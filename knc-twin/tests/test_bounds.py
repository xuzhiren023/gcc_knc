"""Bounds on cases with independently known answers."""
import unittest

import helpers
from helpers import kernel, profile, simulate
from knc_model import bounds, functional, timing
from knc_model.kernel import load_kernel


def assume_list():
    out = []
    return out, (lambda t: out.append(t) if t not in out else None)


class TestLoopBounds(unittest.TestCase):
    def test_recurrence_one_accumulator(self):
        k = load_kernel(helpers.fixture("reduce_1acc.json"))
        notes, assume = assume_list()
        res = bounds.loop_bounds(k, profile(), assume)
        # one vaddps per iteration feeding itself: RecMII = 4/1; body 4 instrs -> 2 issue events -> ResMII 4
        self.assertEqual(res["rec_mii"], "4")
        self.assertEqual(res["res_mii"], 4)
        self.assertEqual(res["mii_cycles_per_iteration"], 4)
        self.assertEqual(res["iteration_critical_path_cycles"], 4)
        recs = res["per_context"]["0"]["recurrences"]
        self.assertTrue(any(r["from"] == "ld" and r["to"] == "ld" and r["latency"] == 4 and r["distance"] == 1 for r in recs))

    def test_two_accumulators_are_resource_bound(self):
        k = load_kernel(helpers.fixture("reduce_2acc.json"))
        notes, assume = assume_list()
        res = bounds.loop_bounds(k, profile(), assume)
        self.assertEqual(res["rec_mii"], "4", "each chain still has a 4-cycle recurrence per iteration")
        self.assertEqual(res["res_mii"], 6, "5 instructions, 3 V-eligible -> 3 issue events x 2-cycle spacing")
        self.assertEqual(res["binding"], "resources")
        # per vector: 3 cycles vs 4 for one accumulator
        self.assertLess(res["mii_cycles_per_iteration"] / 2.0, 4)

    def test_simulation_never_beats_bound(self):
        for name in ("reduce_1acc.json", "reduce_2acc.json", "saxpy_loop.json"):
            k = load_kernel(helpers.fixture(name))
            notes, assume = assume_list()
            lb = bounds.loop_bounds(k, profile(), assume)
            res, _, _ = simulate(k)
            trips = k.loop["trip_count"]
            self.assertGreaterEqual(res["completion_cycles"], lb["mii_cycles_per_iteration"] * trips, name)

    def test_critical_path_vs_ii(self):
        k = load_kernel(helpers.fixture("saxpy_loop.json"))
        notes, assume = assume_list()
        res = bounds.loop_bounds(k, profile(), assume)
        self.assertEqual(res["iteration_critical_path_cycles"], 12 + 4 + 1, "load 12 -> fma 4 -> store")
        self.assertEqual(res["rec_mii_ceiling"], 1, "only the induction variables are loop-carried")
        self.assertEqual(res["mii_cycles_per_iteration"], 8)


class TestTraceBounds(unittest.TestCase):
    def test_issue_and_spacing_terms(self):
        k = kernel([{"op": "vaddps", "ops": ["zmm%d" % i, "zmm20", "zmm21"]} for i in range(6)])
        interp, _, _ = functional.run_functional(k)
        notes, assume = assume_list()
        res = bounds.trace_bounds(k, profile(), interp.traces, assume)
        self.assertEqual(res["terms"]["core_issue_events"], 6)
        self.assertEqual(res["terms"]["per_context_issue_spacing"], 11)
        self.assertEqual(res["lower_bound_cycles"], 11)
        sim, _, _ = simulate(k)
        self.assertEqual(sim["issue_span_cycles"], 11, "independent ops meet the spacing bound exactly")

    def test_critical_path_term(self):
        k = kernel([{"op": "vaddps", "ops": ["zmm0", "zmm1", "zmm2"]}, {"op": "vaddps", "ops": ["zmm3", "zmm0", "zmm2"]}, {"op": "vaddps", "ops": ["zmm4", "zmm3", "zmm2"]}])
        interp, _, _ = functional.run_functional(k)
        notes, assume = assume_list()
        res = bounds.trace_bounds(k, profile(), interp.traces, assume)
        self.assertEqual(res["terms"]["dependency_critical_path"], 12)
        self.assertEqual(res["binding_term"], "dependency_critical_path")

    def test_bound_never_above_simulation(self):
        for name in ("saxpy_4ctx.json", "stream_cold_pf.json", "gather_scattered.json", "int_mask_edge.json"):
            k = load_kernel(helpers.fixture(name))
            interp, _, _ = functional.run_functional(k)
            notes, assume = assume_list()
            lb = bounds.trace_bounds(k, profile(), interp.traces, assume)
            res, _, _ = simulate(k)
            self.assertLessEqual(lb["lower_bound_cycles"], res["completion_cycles"], name)


class TestSearch(unittest.TestCase):
    def test_exhaustive_search_finds_known_optimum(self):
        # a: chain of two dependent ops then an independent op placed last; best order hides latency: a, c, b
        k = kernel([{"op": "vaddps", "ops": ["zmm0", "zmm1", "zmm2"], "id": "a"},
                    {"op": "vaddps", "ops": ["zmm3", "zmm0", "zmm2"], "id": "b"},
                    {"op": "vaddps", "ops": ["zmm4", "zmm5", "zmm6"], "id": "c"}])
        interp, _, _ = functional.run_functional(k)
        prof = profile()

        def factory(tr):
            return timing.CoreSim(k, prof, tr, record_issue=False)
        res = bounds.search_optimal_order(k, prof, interp.traces, 0, 1000, None, factory)
        self.assertTrue(res["space_exhausted"])
        self.assertEqual(res["orders_evaluated"], 3, "a<b, c anywhere: 3 legal orders")
        self.assertEqual(res["best_cycles"], 8)
        self.assertEqual(res["original_order_cycles"], 10)
        self.assertEqual(res["best_order_ids"][0], "a")
        self.assertEqual(res["best_order_ids"][2], "b")

    def test_budget_not_exhausted_reported(self):
        k = kernel([{"op": "vaddps", "ops": ["zmm%d" % i, "zmm20", "zmm21"], "id": "i%d" % i} for i in range(6)])
        interp, _, _ = functional.run_functional(k)
        prof = profile()
        res = bounds.search_optimal_order(k, prof, interp.traces, 0, 5, None, lambda tr: timing.CoreSim(k, prof, tr, record_issue=False))
        self.assertFalse(res["space_exhausted"])
        self.assertEqual(res["orders_evaluated"], 6)


if __name__ == "__main__":
    unittest.main()
