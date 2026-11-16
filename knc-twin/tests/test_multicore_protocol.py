"""S14-13 behavioral red contract; synthetic tests, never native validation.

The lead's 2026-11-15 review requires shared contention, TD remote hits,
transaction conservation and a background effect before green. These small
tests deliberately use no held-out rows or bandwidth targets.

New interface contract for the implementation:
* scenario.multicore carries placement, channel_interleave and background.
* prediction.cores lists core IDs and completion-envelope predicted_cycles.
* prediction.memory.controllers lists detailed/background issued and served
  transaction counts separately (measured region only, after draining).
* Fabric(profile, placement, background=False) is the same backing service
  used by the CLI, not a separate latency calculator. request(core, address,
  operation) returns a live handle; drain() completes queued events; a handle's
  result() reports source, directory, issued_cycle and completed_cycle.
  Fabric.parameters_used() uses the normal profile summary representation.

The serial write/read protocol probe avoids unsupported inter-core programs:
the host test issues B's request only after A's ownership operation completes.
Parameter names below make the planned residual and route terms inspectable.
See references/multicore-design.md for their evidence and assumed alternatives.
"""
import copy
import importlib
import importlib.util
import json
import os
import tempfile
import unittest

import helpers
import test_multicore_cli as entry
from knc_model import analytic
from knc_model import PROFILE_SCHEMA
from knc_model.profile import Param


def read_kernel(cores, background, single_channel=True):
    """Same 32 cold lines per tile, disjoint even at the largest tile count.

    Stride 16 lines maps every access to channel zero under line-modulo-16;
    stride one visits every channel. No stores, prefetches or warm cache hits
    obscure the exact count of demand memory transactions.
    """
    raw = entry.register_kernel(cores)
    raw["name"] = "multicore-protocol-cold-read"
    raw["unit_of_work"] = {"description": "one cold line read", "count": cores * 32}
    raw["init"] = {"memory": []}
    raw["scenario"] = {
        "memory": {"type": "line_tracking", "cold_level": "memory",
                   "hardware_prefetcher": "off"},
        "multicore": {
            # Keep existing detailed stops fixed while increasing the tile count.
            "placement": {str(c): c for c in range(cores)},
            "channel_interleave": "line_modulo",
            "background": {"enabled": background, "active_cores": 60,
                           "epoch_cycles": 64, "seed": 0},
        },
    }
    stride = 16 * 64 if single_channel else 64
    for core, stream in enumerate(raw["streams"]):
        base = 0x100000 + core * 0x10000
        stream["init"] = {"registers": {"rax": base}}
        stream["expected"] = {"registers": {"zmm0": {"f32": [float(core + 32)] * 16}}}
        stream["instructions"] = []
        for line in range(32):
            address = base + line * stride
            raw["init"]["memory"].append({"addr": address, "f32": [float(core + line + 1)] * 16})
            stream["instructions"].append({
                "id": "read%d" % line, "op": "vmovaps",
                "ops": ["zmm0", {"base": "rax", "disp": line * stride}],
            })
    return raw


class TestMulticoreProtocol(unittest.TestCase):
    # Reuse only the CLI invocation/assertion helpers, not its test cases.
    invoke = entry.TestMulticoreCLI.invoke
    prediction = entry.TestMulticoreCLI.prediction

    def bottleneck_prediction(self, raw):
        # Artificially slow the one selected channel: this is a queue invariant,
        # not a claim about measured channel saturation or a profile calibration.
        overlay = {"schema": PROFILE_SCHEMA, "id": "single-channel-test",
                   "version": "1", "parameters": {
                       "memory.channel_service_cycles_per_line": {
                           "value": 256, "status": "synthetic", "unit": "cycles",
                           "source": "S14-13 queue contention test"}}}
        with tempfile.TemporaryDirectory(prefix="knc-twin-channel-") as work:
            path = os.path.join(work, "overlay.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(overlay, f)
            code, result, diagnostic = self.invoke(
                "simulate", raw, "--scale", "ring", "--overlay", path)
        self.assertEqual(code, 0, diagnostic)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["functional_check"]["status"], "ok")
        self.assertEqual(result["parameters_used"]["memory.channel_service_cycles_per_line"]["value"], 256)
        self.channel_service_cycles = result["parameters_used"]["memory.channel_service_cycles_per_line"]["value"]
        pred = result["prediction"]
        self.assertEqual(pred["result_class"]["class"], "unvalidated_scenario_estimate")
        return pred

    def test_one_channel_contention_grows_with_detailed_tiles(self):
        means = []
        for count in (1, 2, 4, 8):
            # Lead-approved test correction, S14-13 answer 2026-11-15:
            # hold background at 52 so adding detailed cores adds offered load.
            raw = read_kernel(count, True)
            raw["scenario"]["multicore"]["background"]["active_cores"] = count + 52
            pred = self.bottleneck_prediction(raw)
            cores = pred["cores"]
            self.assertEqual(sorted(c["core"] for c in cores), list(range(count)))
            means.append(sum(c["predicted_cycles"] for c in cores) / float(count))
            controllers = pred["memory"]["controllers"]
            self.assertEqual(sum(c["detailed_issued"] for c in controllers), count * 32)
            self.assertEqual(controllers[0]["detailed_issued"], count * 32)
            self.assertGreater(sum(c["background_served"] for c in controllers), 0)
            self.assertGreater(controllers[0]["queue_wait_cycles"], 0)
        self.assertEqual(means, sorted(means), "per-core cycles must not fall as tiles grow")
        self.assertGreater(means[-1], means[0], "independent copies of CoreSim cannot pass")
        print("fixed-background 1/2/4/8 means:", means)
        symmetry = []
        for count in (1, 2, 4, 8):
            pred = self.bottleneck_prediction(read_kernel(count, True))
            symmetry.append(sum(c["predicted_cycles"] for c in pred["cores"]) / float(count))
            self.assertLessEqual(abs(symmetry[-1] - symmetry[0]),
                                 count * self.channel_service_cycles)
        print("fixed-total 1/2/4/8 means:", symmetry)

    def test_remote_owner_read_uses_td_and_shortest_route(self):
        name = "knc_model.multicore"
        self.assertIsNotNone(importlib.util.find_spec(name), "shared multicore fabric is absent")
        module = importlib.import_module(name)
        latencies = []
        route_cycles = []
        for distance in (1, 15, 30, 31):
            prof = helpers.profile()
            # Synthetic single-slot packets retain occupied-link service;
            # default line zero maps to TD zero, at the owner's position zero.
            for key, value in (("ring.data_slot_bytes", 64),
                               ("ring.hop_cycles", 1),
                               ("ring.control_service_cycles", 1)):
                prof.params[key] = Param(key, {"value": value, "status": "synthetic",
                                               "source": "S14-13 protocol test"})
            fabric = module.Fabric(prof, placement={0: 0, 1: distance}, background=False)
            owner = fabric.request(core=0, address=0, operation="write")
            self.assertFalse(owner.done)
            fabric.drain()
            self.assertTrue(owner.done)
            self.assertEqual(owner.result()["owner"], 0)
            remote = fabric.request(core=1, address=0, operation="read")
            self.assertFalse(remote.done)
            fabric.drain()
            self.assertTrue(remote.done)
            result = remote.result()
            self.assertEqual(result["source"], "remote_l2")
            self.assertEqual(result["source_core"], 0)
            self.assertEqual(result["directory"], 0)
            self.assertEqual(result["memory_transactions"], 0)
            p = {key: item["value"] for key, item in fabric.parameters_used().items()}
            hops = 2 * min(distance, 61 - distance)
            self.assertEqual(result["response_path_hops"], hops)
            # The measured remote anchor is decomposed once. Do not add the
            # complete anchor again to the new route (design parameter table).
            anchor = p["latency.remote_l2_line_ns"] * p["card.clock_hz"] / 1e9
            residual = p["multicore.remote_endpoint_residual_cycles"]
            self.assertGreaterEqual(residual, 0)
            self.assertAlmostEqual(
                residual + p["multicore.remote_reference_path_cycles"], anchor,
                delta=1.0 / 1024)
            route = hops * p["ring.hop_cycles"]
            elapsed = result["completed_cycle"] - result["issued_cycle"]
            if distance == 1:
                self.assertGreaterEqual(
                    elapsed, residual + p["latency.l2_hit"] + p["td.lookup_cycles"] + route)
            else:
                # Fixed endpoint and packet service terms cancel; only the
                # shortest-route hop delay changes between these probes.
                self.assertAlmostEqual(
                    elapsed - latencies[0], route - route_cycles[0], delta=1.0 / 1024)
            latencies.append(elapsed)
            route_cycles.append(route)
        self.assertLess(latencies[0], latencies[1])
        self.assertLess(latencies[1], latencies[2])
        self.assertEqual(latencies[2], latencies[3], "31 stops takes the reverse 30-hop path")

    def test_memory_transactions_are_conserved_per_controller(self):
        for count in (2, 4, 8):
            with self.subTest(cores=count):
                pred = self.prediction(read_kernel(count, True, single_channel=False), "ring")
                controllers = pred["memory"]["controllers"]
                self.assertEqual([c["controller"] for c in controllers], list(range(8)))
                for controller in controllers:
                    self.assertEqual(controller["detailed_issued"], controller["detailed_served"])
                    self.assertEqual(controller["detailed_served"], count * 4)
                    self.assertEqual(controller["background_issued"], controller["background_served"])
                self.assertEqual(sum(c["detailed_served"] for c in controllers), count * 32)
                self.assertGreater(sum(c["background_served"] for c in controllers), 0)

    def test_pending_reads_merge_and_conflicting_store_waits(self):
        from knc_model.multicore import Fabric
        fabric = Fabric(helpers.profile(), {0: 0, 1: 1, 2: 2})
        first = fabric.request(0, 0, "read")
        second = fabric.request(1, 0, "read")
        store = fabric.request(2, 0, "write")
        fabric.advance(20)
        self.assertFalse(first.done)
        self.assertFalse(second.done)
        self.assertEqual(fabric.lines[0][0]["sharers"], set())
        fabric.drain()
        self.assertEqual(second.result()["source"], "merged_read")
        self.assertEqual(sum(c["read_transactions"] for c in fabric.controllers), 1)
        self.assertGreater(store.result()["completed_cycle"], second.result()["completed_cycle"])
        self.assertEqual(fabric.lines[0][0]["owner"], 2)
        self.assertEqual(fabric.lines[0][0]["sharers"], {2})

    def test_rfo_no_read_and_dirty_eviction_accounting(self):
        from knc_model.multicore import Fabric, TileMemory
        fabric = Fabric(helpers.profile(), {0: 0, 1: 15})
        kernel = helpers.kernel([{"op": "nop"}], scenario={"memory": {"type": "line_tracking", "cold_level": "memory"}})
        caches = [TileMemory(kernel.scenario, fabric.p, lambda _: None, fabric, c) for c in (0, 1)]
        first = caches[0]._fetch(0, "read")
        self.assertIsNone(caches[0].l2.lookup(0))
        fabric.drain()
        self.assertIsNotNone(caches[0].l2.lookup(0))
        caches[1]._fetch(0, "write")
        fabric.drain()
        self.assertIsNone(caches[0].l1.lookup(0))
        self.assertIsNone(caches[0].l2.lookup(0))
        fabric.evict(1, 0)
        fabric.drain()
        self.assertEqual(sum(c["read_transactions"] for c in fabric.controllers), 1)
        self.assertEqual(sum(c["write_transactions"] for c in fabric.controllers), 1)
        self.assertNotIn(0, fabric.lines[0])
        nr = fabric.request(0, 64, "no_read")
        fabric.drain()
        self.assertEqual(nr.result()["memory_transactions"], 1)
        self.assertEqual(sum(c["read_transactions"] for c in fabric.controllers), 1)
        self.assertEqual(sum(c["write_transactions"] for c in fabric.controllers), 2)
        self.assertTrue(first.done)

    def test_links_contend_and_channels_overlap(self):
        from knc_model.multicore import Fabric
        fabric = Fabric(helpers.profile(), {0: 0, 1: 30})
        arrivals = []
        fabric.route(0, 15, "data", lambda: arrivals.append(fabric.now))
        fabric.route(0, 15, "data", lambda: arrivals.append(fabric.now))
        fabric.drain()
        self.assertEqual(arrivals[1] - arrivals[0], fabric.data)
        self.assertTrue(any(s["wait_cycles"] > 0 for s in fabric.link_stats.values()))
        # Remove route asymmetry, retaining real channel queues and service.
        fabric = Fabric(helpers.profile(), {0: 0}, scenario={"td_positions": [0] * 64,
                        "controller_positions": [0] * 8})
        fabric.interval = 256
        a = fabric.request(0, 0, "read")
        b = fabric.request(0, 64, "read")
        c = fabric.request(0, 1024, "read")
        fabric.drain()
        self.assertEqual(c.result()["completed_cycle"] - a.result()["completed_cycle"], 256)
        self.assertLess(b.result()["completed_cycle"], c.result()["completed_cycle"])
        self.assertEqual({fabric.directory(i * 64) for i in range(64)}, set(range(64)))

    def test_background_changes_ring_but_not_analytical_scales(self):
        raw = read_kernel(2, False)
        unit = self.prediction(raw, "unit")
        ring_off = self.prediction(raw, "ring")
        raw_on = copy.deepcopy(raw)
        raw_on["scenario"]["multicore"]["background"]["enabled"] = True
        ring_on = self.prediction(raw_on, "ring")
        self.assertEqual(unit["predicted_cycles"], ring_off["predicted_cycles"])
        self.assertGreater(ring_on["predicted_cycles"], ring_off["predicted_cycles"])

        # Identical work/analytic inputs for both background settings; pin the
        # existing formulas independently, so changing both outputs cannot pass.
        prof = helpers.profile()
        clock = prof.get("card.clock_hz")
        remote_cycles = prof.get("latency.remote_l2_line_ns") * clock / 1e9
        bw = prof.get_sub("card.sustained_bandwidth_gbs", "read_only")
        pairs, cards = [], []
        for kernel in (raw, raw_on):
            params = {"core_a_cycles": 100, "core_b_cycles": 200,
                      "lines_exchanged": 64, "concurrency": 4,
                      "units": kernel["unit_of_work"]["count"], "bytes_per_unit": 64,
                      "per_core_cycles_per_unit": 100, "cores": 2,
                      "scenario": kernel["scenario"]}
            pairs.append(analytic.pair_estimate(prof, params))
            cards.append(analytic.card_estimate(prof, params))
        self.assertEqual(pairs[0], pairs[1])
        self.assertEqual(cards[0], cards[1])
        self.assertEqual(pairs[0]["scenarios"][0]["total_cycles"], round(200 + 16 * remote_cycles, 1))
        self.assertEqual(cards[0]["scenarios"][0]["total_seconds"],
                         max(100 * 64 / 2 / clock, 64 * 64 / (bw * 1e9)))


if __name__ == "__main__":
    unittest.main()
