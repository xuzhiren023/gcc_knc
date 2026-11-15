"""Core timing model: latency, issue spacing, context interleaving, pairing, misses vs
prefetches, AGI, determinism, budgets, concurrency. All against the card-7120-measured
profile; these are synthetic model tests, not hardware validation."""
import concurrent.futures
import json
import unittest

import helpers
from helpers import issue_cycles, kernel, profile, simulate
from knc_model import timing
from knc_model.errors import BudgetExhausted, MissingParameter


def vadd(dst, a, b, **kw):
    d = {"op": "vaddps", "ops": [dst, a, b]}
    d.update(kw)
    return d


class TestLatencyAndSpacing(unittest.TestCase):
    def test_producer_consumer_latency(self):
        k = kernel([vadd("zmm0", "zmm1", "zmm2", id="p"), vadd("zmm3", "zmm0", "zmm2", id="c")])
        res, sim, _ = simulate(k)
        ic = issue_cycles(sim)
        self.assertEqual(ic[(0, "p", 0)], 0)
        self.assertEqual(ic[(0, "c", 0)], 4, "dependent vector op issues latency.vector_arith (4) cycles later")
        self.assertEqual(res["completion_cycles"], 8)

    def test_independent_ops_one_context_every_other_cycle(self):
        k = kernel([vadd("zmm%d" % i, "zmm20", "zmm21", id="i%d" % i) for i in range(6)])
        res, sim, _ = simulate(k)
        ic = issue_cycles(sim)
        self.assertEqual([ic[(0, "i%d" % i, 0)] for i in range(6)], [0, 2, 4, 6, 8, 10], "same-context issue gap of 2 cycles")
        self.assertEqual(res["issue_span_cycles"], 11)

    def test_two_contexts_fill_every_cycle(self):
        streams = [{"context": c, "instructions": [vadd("zmm%d" % i, "zmm20", "zmm21", id="i%d" % i) for i in range(6)]} for c in (0, 1)]
        k = kernel(None, streams=streams)
        res, sim, _ = simulate(k)
        ic = issue_cycles(sim)
        self.assertEqual([ic[(0, "i%d" % i, 0)] for i in range(3)], [0, 2, 4])
        self.assertEqual([ic[(1, "i%d" % i, 0)] for i in range(3)], [1, 3, 5], "the other context takes the odd cycles")
        self.assertEqual(res["issue_span_cycles"], 12)
        self.assertEqual(res["core_issue_utilization"], 1.0)

    def test_stalled_context_lets_others_progress(self):
        # context 0 has a dependent chain, context 1 independent ops: context 1 issues while 0 waits
        streams = [{"context": 0, "instructions": [vadd("zmm0", "zmm1", "zmm2", id="a"), vadd("zmm3", "zmm0", "zmm2", id="b"), vadd("zmm4", "zmm3", "zmm2", id="c")]},
                   {"context": 1, "instructions": [vadd("zmm%d" % i, "zmm20", "zmm21", id="i%d" % i) for i in range(4)]}]
        k = kernel(None, streams=streams)
        res, sim, _ = simulate(k)
        ic = issue_cycles(sim)
        self.assertEqual(ic[(0, "b", 0)], 4)
        self.assertEqual(ic[(0, "c", 0)], 8)
        self.assertEqual([ic[(1, "i%d" % i, 0)] for i in range(4)], [1, 3, 5, 7], "context 1 is not blocked by context 0's dependency stall")
        self.assertGreater(res["per_context"]["0"]["stall_cycles"].get("dependency", 0), 0)

    def test_four_contexts_round_robin(self):
        streams = [{"context": c, "instructions": [vadd("zmm%d" % i, "zmm20", "zmm21", id="i%d" % i) for i in range(2)]} for c in range(4)]
        k = kernel(None, streams=streams)
        res, sim, _ = simulate(k)
        ic = issue_cycles(sim)
        self.assertEqual([ic[(c, "i0", 0)] for c in range(4)], [0, 1, 2, 3])
        self.assertEqual([ic[(c, "i1", 0)] for c in range(4)], [4, 5, 6, 7])


class TestPairing(unittest.TestCase):
    def test_vector_plus_scalar_pairs(self):
        k = kernel([vadd("zmm0", "zmm1", "zmm2", id="v"), {"op": "add", "ops": ["rax", 1], "id": "s"}])
        res, sim, _ = simulate(k)
        ic = issue_cycles(sim)
        self.assertEqual(ic[(0, "v", 0)], ic[(0, "s", 0)], "scalar ALU op issues on V in the same cycle")
        self.assertEqual(res["per_context"]["0"]["pairs"], 1)

    def test_two_vector_ops_do_not_pair(self):
        k = kernel([vadd("zmm0", "zmm1", "zmm2", id="v1"), vadd("zmm3", "zmm1", "zmm2", id="v2")])
        res, sim, _ = simulate(k)
        ic = issue_cycles(sim)
        self.assertEqual(ic[(0, "v2", 0)] - ic[(0, "v1", 0)], 2)
        self.assertEqual(res["per_context"]["0"]["pairs"], 0)

    def test_dependent_scalar_does_not_pair_but_cmp_jcc_does(self):
        k = kernel([{"op": "add", "ops": ["rax", 1], "id": "a"}, {"op": "add", "ops": ["rbx", "rax"], "id": "b"}])
        res, sim, _ = simulate(k)
        ic = issue_cycles(sim)
        self.assertEqual(ic[(0, "b", 0)], 2, "RAW inside the pair is illegal")
        k = kernel([{"op": "cmp", "ops": ["rax", "rbx"], "id": "c"}, {"op": "jne", "ops": ["T"], "id": "j"}, {"op": "mov", "ops": ["rcx", 1], "id": "m", "label": "T"}])
        res, sim, _ = simulate(k)
        ic = issue_cycles(sim)
        self.assertEqual(ic[(0, "c", 0)], ic[(0, "j", 0)], "cmp/jcc is a documented pairable dependency")

    def test_encoding_hint_blocks_pairing(self):
        k = kernel([vadd("zmm0", "zmm1", "zmm2", id="v"), {"op": "vmovaps", "ops": [{"base": "rax", "disp": 4096}, "zmm3"], "id": "s", "encoding": {"disp32": True}}],
                   init={"memory": [{"addr": "0x2000", "u32": [0] * 16}], "registers": {"rax": "0x1000"}})
        res, sim, _ = simulate(k)
        ic = issue_cycles(sim)
        self.assertEqual(ic[(0, "s", 0)] - ic[(0, "v", 0)], 2, "MVEX store with disp32 does not pair (R02 p.56)")

    def test_gather_occupies_both_pipes(self):
        from knc_model.kernel import load_kernel
        k = load_kernel(helpers.fixture("gather_scattered.json"))
        res, sim, _ = simulate(k)
        self.assertEqual(res["completion_cycles"], 15 + 7 * 15 + 4)
        k1 = load_kernel(helpers.fixture("gather_one_line.json"))
        res1, _, _ = simulate(k1)
        self.assertEqual(res1["completion_cycles"], 15 + 4)


class TestMemory(unittest.TestCase):
    def cold_kernel(self, prefetch):
        ins = []
        if prefetch:
            ins.append({"op": "vprefetch0", "ops": [{"base": "rax", "disp": 64}], "id": "pf"})
            ins += [{"op": "add", "ops": ["rbx", 1], "id": "f%d" % i} for i in range(4)]  # filler work
        ins.append({"op": "vmovaps", "ops": ["zmm0", {"base": "rax", "disp": 64}], "id": "ld"})
        ins.append(vadd("zmm1", "zmm0", "zmm0", id="use"))
        return kernel(ins, init={"memory": [{"addr": "0x1000", "u32": [1] * 32}], "registers": {"rax": "0x1000"}},
                      scenario={"memory": {"type": "line_tracking", "cold_level": "memory"}, "branch": {"type": "all_predicted"}})

    def test_demand_miss_stalls_context(self):
        res, sim, _ = simulate(self.cold_kernel(False))
        ic = issue_cycles(sim)
        p = profile()
        self.assertEqual(ic[(0, "use", 0)], 357 + (12 - 3), "load to use = memory latency + (vector_load_l1 - scalar_load_l1)")
        self.assertGreater(res["per_context"]["0"]["stall_cycles"]["miss_stall"], 300)

    def test_prefetch_is_nonblocking_and_hides_latency(self):
        res_pf, sim, _ = simulate(self.cold_kernel(True))
        ic = issue_cycles(sim)
        self.assertEqual(ic[(0, "f0", 0)], 0, "the filler pairs with the prefetch: no stall after a prefetch")
        self.assertLess(ic[(0, "ld", 0)], 20, "the demand load issues before the prefetch returns")
        res_nopf, _, _ = simulate(self.cold_kernel(False))
        self.assertLess(res_pf["completion_cycles"], res_nopf["completion_cycles"] + 12)
        self.assertEqual(res_pf["memory"]["stats"]["prefetches"], 1)
        self.assertEqual(res_pf["memory"]["stats"]["inflight_waits"], 1, "the demand load waits for the in-flight prefetch instead of missing again")

    def test_fixed_level_l2(self):
        k = kernel([{"op": "vmovaps", "ops": ["zmm0", {"base": "rax"}], "id": "ld"}, vadd("zmm1", "zmm0", "zmm0", id="use")],
                   init={"memory": [{"addr": "0x1000", "u32": [1] * 16}], "registers": {"rax": "0x1000"}},
                   scenario={"memory": {"type": "fixed_level", "level": "l2"}, "branch": {"type": "all_predicted"}})
        res, sim, _ = simulate(k)
        ic = issue_cycles(sim)
        self.assertEqual(ic[(0, "use", 0)], 24 + (12 - 3))

    def test_outstanding_miss_limit(self):
        ins = [{"op": "vprefetch0", "ops": [{"base": "rax", "disp": 64 * i}], "id": "pf%d" % i} for i in range(10)]
        k = kernel(ins, init={"memory": [{"addr": "0x1000", "u32": [1] * 16 * 10}], "registers": {"rax": "0x1000"}},
                   scenario={"memory": {"type": "line_tracking", "cold_level": "memory"}, "branch": {"type": "all_predicted"}})
        res, sim, _ = simulate(k)
        ic = issue_cycles(sim)
        self.assertLess(ic[(0, "pf7", 0)], 20)
        self.assertGreaterEqual(ic[(0, "pf8", 0)], 357, "the ninth prefetch waits for a free outstanding-miss slot (limit 8)")
        self.assertGreater(res["per_context"]["0"]["stall_cycles"]["outstanding_limit"], 0)

    def test_agi(self):
        k = kernel([{"op": "add", "ops": ["rax", 64], "id": "p"}, {"op": "mov", "ops": ["rcx", {"base": "rax"}], "id": "ld", "width": 64}],
                   init={"registers": {"rax": "0x1000"}}, memory_default=0)
        res, sim, _ = simulate(k)
        ic = issue_cycles(sim)
        self.assertEqual(ic[(0, "ld", 0)], 3, "address usable 3 cycles after the write issued (AGI), not at the next slot (2)")
        self.assertGreater(res["per_context"]["0"]["stall_cycles"]["agi"], 0)


class TestBudgetsAndDeterminism(unittest.TestCase):
    def test_cycle_budget_reports_partial(self):
        from knc_model.kernel import load_kernel
        k = load_kernel(helpers.fixture("saxpy_loop.json"))
        with self.assertRaises(BudgetExhausted) as cm:
            simulate(k, max_cycles=10)
        self.assertIn("partial", str(cm.exception))
        self.assertIn("cycles", cm.exception.partial)

    def test_deterministic(self):
        from knc_model.kernel import load_kernel
        k = load_kernel(helpers.fixture("saxpy_4ctx.json"))
        a, sa, _ = simulate(k)
        b, sb, _ = simulate(k)
        a.pop("python_seconds")
        b.pop("python_seconds")
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(sa.issue_log, sb.issue_log)

    def test_concurrent_runs_share_no_state(self):
        from knc_model.kernel import load_kernel
        names = ["saxpy_4ctx.json", "stream_cold_pf.json", "reduce_1acc.json", "saxpy_loop.json"] * 3

        def one(name):
            k = load_kernel(helpers.fixture(name))
            res, sim, _ = simulate(k, record_issue=False)
            return name, res["completion_cycles"]
        serial = {}
        for n in set(names):
            serial[n] = one(n)[1]
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            for name, cyc in ex.map(one, names):
                self.assertEqual(cyc, serial[name], name)

    def test_missing_parameter_is_explicit(self):
        k = kernel([{"op": "vpermd", "ops": ["zmm2", "zmm1", "zmm0"]}])
        with self.assertRaises(MissingParameter) as cm:
            simulate(k, prof=profile("knc-common"))
        self.assertIn("latency.vector_long", str(cm.exception))
        res, _, _ = simulate(k)  # measured profile knows it
        self.assertEqual(res["completion_cycles"], 6)

    def test_branch_scenarios(self):
        import json as _json
        from knc_model.kernel import Kernel
        with open(helpers.fixture("saxpy_loop.json"), encoding="utf-8") as f:
            raw = _json.load(f)
        raw["streams"][0]["instructions"].append({"id": "after", "op": "mov", "ops": ["rax", 0]})  # code after the loop sees the penalty
        k = Kernel(raw, helpers.fixture("saxpy_loop.json"))
        base, _, _ = simulate(k)
        k.scenario["branch"] = {"type": "all_mispredicted"}
        mis, _, _ = simulate(k)
        self.assertEqual(mis["completion_cycles"] - base["completion_cycles"], 4 * 5, "4 branches x 5 extra cycles each")
        k.scenario["branch"] = {"type": "exit_mispredicted"}
        ex, _, _ = simulate(k)
        self.assertEqual(ex["completion_cycles"] - base["completion_cycles"], 5, "only the direction change at loop exit is charged")
        k.scenario["branch"] = {"type": "ids_mispredicted", "ids": ["br"]}
        ids, _, _ = simulate(k)
        self.assertEqual(ids["completion_cycles"], mis["completion_cycles"])


if __name__ == "__main__":
    unittest.main()
