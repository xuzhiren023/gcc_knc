"""S14-14 acceptance contracts; model predictions, never native measurements."""
import copy
import importlib
import importlib.util
import os
import contextlib
import io
import json
import tempfile
import unittest

import helpers
from helpers import kernel, profile, simulate
from knc_model import asm, bounds
from knc_model.kernel import Kernel, load_kernel
from knc_model.trace import loop_body


class TestSchedulingExplorer(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(
            importlib.util.find_spec("knc_model.scheduling"),
            "S14-14: scheduling explorer is not implemented")
        self.explore = importlib.import_module("knc_model.scheduling").explore
        self.prof = profile()

    def explore_ok(self, k, method, budget=512):
        original = copy.deepcopy(k.raw)
        result = self.explore(k, self.prof, method=method, seed=17,
                              max_states=budget)
        self.assertEqual(k.raw, original, "search must not mutate its input")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["unsupported"], [])
        self.assertIsInstance(result["assumptions"], list)
        return result

    def check_candidate(self, k, result):
        candidate = result["candidate"]
        rebuilt = Kernel(candidate["kernel"], None)
        measured_model, _, check = simulate(rebuilt, self.prof)
        self.assertEqual(check["status"], "ok")
        self.assertEqual(rebuilt.raw["expected"], k.raw["expected"])
        self.assertEqual(candidate["cycles"], measured_model["completion_cycles"])
        self.assertEqual(candidate["pair_fraction"], measured_model["pair_fraction"])
        self.assertEqual(candidate["gas"], asm.emit_gas(rebuilt.streams[0]))
        self.assertTrue(candidate["limiting_constraints"])
        self.assertLessEqual(result["lower_bound_cycles"], candidate["cycles"])
        self.assertLessEqual(candidate["cycles"], result["baseline_cycles"])
        return candidate

    def test_small_search_recovers_known_optimum(self):
        k = kernel([
            {"id": "a", "op": "vaddps", "ops": ["zmm0", "zmm1", "zmm2"]},
            {"id": "b", "op": "vaddps", "ops": ["zmm3", "zmm0", "zmm2"]},
            {"id": "c", "op": "vaddps", "ops": ["zmm4", "zmm5", "zmm6"]},
        ], init={"registers": {"zmm1": {"f32_broadcast": 1.0},
                               "zmm2": {"f32_broadcast": 2.0},
                               "zmm5": {"f32_broadcast": 4.0},
                               "zmm6": {"f32_broadcast": 5.0}}},
            expected={"registers": {"0": {"zmm0": {"f32_broadcast": 3.0},
                                           "zmm3": {"f32_broadcast": 5.0},
                                           "zmm4": {"f32_broadcast": 9.0}}}})
        result = self.explore_ok(k, "beam")
        candidate = self.check_candidate(k, result)
        self.assertEqual(candidate["order_ids"], ["a", "c", "b"])
        self.assertEqual(candidate["cycles"], 8)
        self.assertEqual(result["baseline_cycles"], 10)
        self.assertTrue(result["search"]["space_exhausted"])
        self.assertEqual(candidate["result_class"], "unvalidated_scenario_estimate")

    def test_sixty_instruction_search_and_list_preserve_chains(self):
        # Three independent chains: many legal interleavings, beyond old n <= 12.
        instructions = [
            {"id": "c%d_%d" % (chain, step), "op": "vaddps",
             "ops": ["zmm%d" % chain, "zmm%d" % chain, "zmm20"]}
            for chain in range(3) for step in range(20)
        ]
        k = kernel(instructions,
                   init={"registers": {"zmm20": {"f32_broadcast": 1.0}}},
                   expected={"registers": {"0": {
                       "zmm%d" % c: {"f32_broadcast": 20.0} for c in range(3)}}})
        found = {}
        for method in ("beam", "list"):
            with self.subTest(method=method):
                result = self.explore_ok(k, method, budget=256)
                candidate = self.check_candidate(k, result)
                ids = candidate["order_ids"]
                self.assertCountEqual(ids, [i["id"] for i in instructions])
                for chain in range(3):
                    self.assertEqual([i for i in ids if i.startswith("c%d_" % chain)],
                                     ["c%d_%d" % (chain, s) for s in range(20)])
                self.assertLess(candidate["cycles"], result["baseline_cycles"])
                found[method] = result
        self.assertLessEqual(found["beam"]["search"]["states_visited"], 256)
        self.assertFalse(found["beam"]["search"]["space_exhausted"])
        again = self.explore_ok(k, "beam", budget=256)
        self.assertEqual(again["candidate"]["order_ids"],
                         found["beam"]["candidate"]["order_ids"])
        self.assertEqual(again["search"], found["beam"]["search"])

    def test_dependencies_include_flags_memory_and_anti_dependencies(self):
        k = kernel([
            {"id": "read", "op": "mov", "ops": ["rbx", "rax"]},
            {"id": "write", "op": "mov", "ops": ["rax", 7]},
            {"id": "store", "op": "mov", "width": 64,
             "ops": [{"base": "rdx"}, "rax"]},
            {"id": "load", "op": "mov", "width": 64,
             "ops": ["rcx", {"base": "rdx"}]},
            {"id": "compare", "op": "cmp", "ops": ["rcx", 7]},
            {"id": "useflags", "op": "sete", "ops": ["al"]},
        ], init={"registers": {"rax": 3, "rdx": 4096}},
            expected={"registers": {"0": {"rbx": 3, "rcx": 7, "rax": 1}}})
        for method in ("beam", "list"):
            with self.subTest(method=method):
                candidate = self.check_candidate(k, self.explore_ok(k, method))
                pos = {iid: n for n, iid in enumerate(candidate["order_ids"])}
                for before, after in (("read", "write"), ("write", "store"),
                                      ("store", "load"), ("compare", "useflags")):
                    self.assertLess(pos[before], pos[after])

    def test_characterization_loop_orders_execute_and_keep_results(self):
        for name in ("reduce_1acc.json", "reduce_2acc.json", "saxpy_loop.json"):
            for method in ("beam", "list"):
                with self.subTest(fixture=name, method=method):
                    k = load_kernel(helpers.fixture(name))
                    candidate = self.check_candidate(k, self.explore_ok(k, method))
                    head, back = loop_body(k, k.streams[0])
                    self.assertCountEqual(candidate["order_ids"],
                                          [i.id for i in k.streams[0].insns[head:back + 1]])
                    self.assertEqual(candidate["order_ids"][-1], k.streams[0].insns[back].id)

    def test_modulo_reports_feasible_ii_and_actual_simulation_difference(self):
        for name in ("reduce_1acc.json", "reduce_2acc.json", "saxpy_loop.json"):
            with self.subTest(fixture=name):
                k = load_kernel(helpers.fixture(name))
                result = self.explore_ok(k, "modulo", budget=4096)
                candidate = self.check_candidate(k, result)
                lower = bounds.loop_bounds(k, self.prof, lambda note: None)
                modulo = result["modulo"]
                self.assertEqual(modulo["res_mii"], lower["res_mii"])
                self.assertEqual(modulo["rec_mii"], lower["rec_mii"])
                ii = modulo["ii"]
                self.assertGreaterEqual(ii, lower["mii_cycles_per_iteration"])
                entries = modulo["schedule"]
                self.assertCountEqual([e["id"] for e in entries], candidate["order_ids"])
                self.assertEqual(modulo["stage_count"], 1 + max(e["cycle"] for e in entries) // ii)
                self.assertIsInstance(modulo["registers_live_across_stages"], int)
                self.assertGreaterEqual(modulo["registers_live_across_stages"], 0)
                # Cyclic resource check, including the last/first issue event.
                slots = [(e["cycle"] % ii, e["pipe"]) for e in entries]
                self.assertEqual(len(slots), len(set(slots)))
                self.assertTrue(all(pipe in ("U", "V") for _, pipe in slots))
                issues = sorted(set(c for c, _ in slots))
                gap = self.prof.get("core.min_issue_gap_same_context")
                for a, b in zip(issues, issues[1:] + [issues[0] + ii]):
                    self.assertGreaterEqual(b - a, gap)
                self.assertAlmostEqual(modulo["simulation_minus_estimate_cycles_per_iteration"],
                                       candidate["cycles_per_iteration"] - ii)
                cycles = {e["id"]: e["cycle"] for e in entries}
                for edge in modulo["dependencies"]:
                    self.assertGreaterEqual(cycles[edge["to"]] + edge["distance"] * ii,
                                            cycles[edge["from"]] + edge["latency"])

    def test_cli_exports_candidate_ranked_by_frozen_batch(self):
        from knc_model.cli import main
        k = kernel([
            {"id": "a", "op": "vaddps", "ops": ["zmm0", "zmm1", "zmm2"]},
            {"id": "b", "op": "vaddps", "ops": ["zmm3", "zmm0", "zmm2"]},
            {"id": "c", "op": "vaddps", "ops": ["zmm4", "zmm5", "zmm6"]},
        ], expected={"registers": {"0": {"zmm3": {"f32_broadcast": 0.0}}}})
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            path = os.path.join(tmp, "input.json")
            with open(path, "w") as f:
                json.dump(k.raw, f)
            out = os.path.join(tmp, "schedule")
            self.assertEqual(main(["schedule", path, "--out", out]), 0)
            manifest = os.path.join(out, "batch.json")
            with open(manifest) as f:
                man = json.load(f)
            self.assertEqual(man["frozen_profile_hash"], self.prof.hash)
            ranked = os.path.join(tmp, "ranked")
            self.assertEqual(main(["batch", manifest, "--out", ranked]), 0)
            with open(os.path.join(ranked, "result.json")) as f:
                result = json.load(f)
            self.assertEqual(result["prediction"]["ranking"], ["beam", "baseline"])
            rows = result["prediction"]["candidates"]
            self.assertTrue(all(r["functional_check"] == "ok" for r in rows))
            self.assertEqual([r["predicted_cycles"] for r in rows], [10, 8])
            man["frozen_profile_hash"] = "wrong-profile"
            with open(manifest, "w") as f:
                json.dump(man, f)
            self.assertEqual(main(["batch", manifest, "--out", ranked, "--force"]), 2)

    def test_s12_31_finds_compare_next_to_jump_without_changing_inputs(self):
        path = os.path.join(helpers.ROOT, "tests", "heldout_native",
                            "s12-31-microbench", "kernels", "gas_0.json")
        raw = copy.deepcopy(load_kernel(path).raw)
        # Select inner products; retain the outer row loop and function epilogue.
        raw["loop"] = {"label": ".A_4108c0", "back_branch": "a4108d3", "trip_count": 27}
        k = Kernel(raw, path)
        for method in ("beam", "list", "modulo"):
            with self.subTest(method=method):
                result = self.explore_ok(k, method, budget=4096)
                candidate = self.check_candidate(k, result)
                ids = candidate["order_ids"]
                self.assertEqual(ids[ids.index("a4108d3") - 1], "a4108cf")
                self.assertEqual(candidate["kernel"]["init"], raw["init"])
                self.assertLess(candidate["cycles"], result["baseline_cycles"])
                # x87 order is a semantic stack constraint, not a tuning target.
                self.assertLess(ids.index("a4108c4"), ids.index("a4108c8"))
                self.assertLess(ids.index("a4108c8"), ids.index("a4108d1"))
                if method == "modulo":
                    from knc_model import isa
                    modulo = result["modulo"]
                    ii = modulo["ii"]
                    entries = modulo["schedule"]
                    rebuilt = Kernel(candidate["kernel"], None)
                    phases = sorted(set(e["cycle"] % ii for e in entries))
                    for e in entries:
                        insn = rebuilt.streams[0].by_id[e["id"]]
                        if insn.kind.startswith("x87"):
                            phase = e["cycle"] % ii
                            self.assertEqual(sum(x["cycle"] % ii == phase for x in entries), 1)
                            if insn.is_load:
                                latency = (self.prof.get("latency.x87_load") if insn.cls == "x87_load" else
                                           self.prof.get("latency.x87_mem_operand_load") +
                                           self.prof.get(isa.CLASSES[insn.cls]["latency"]))
                                next_phase = next((t for t in phases if t > phase), phases[0] + ii)
                                self.assertGreaterEqual(next_phase - phase, latency)


if __name__ == "__main__":
    unittest.main()
