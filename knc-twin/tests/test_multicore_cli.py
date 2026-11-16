"""S14-13 multicore entry-point contract (synthetic, not native validation).

These tests establish the first red handoff from references/multicore-design.md.
They exercise the real CLI in-process to keep host validation single-threaded.
Protocol/conservation tests and measured comparisons belong to the implementation
phase; these small inputs do not establish a hardware bandwidth scaling curve.
"""
import contextlib
import io
import json
import os
import tempfile
import unittest

import helpers
from knc_model import cli


def register_kernel(cores, contexts=1):
    """Independent identical cores; context numbers deliberately repeat."""
    return {
        "schema": helpers.SCHEMA,
        "name": "multicore-register-chain",
        "unit_of_work": {"description": "one context chain", "count": cores * contexts},
        "streams": [
            {"core": core, "context": ctx,
             "init": {"registers": {"zmm0": {"f32": [0.0] * 16},
                                    "zmm1": {"f32": [1.0] * 16}}},
             "expected": {"registers": {"zmm0": {"f32": [12.0] * 16}}},
             "instructions": [
                {"op": "vaddps", "ops": ["zmm0", "zmm0", "zmm1"],
                 "id": "add%d" % i} for i in range(12)]}
            for core in range(cores) for ctx in range(contexts)
        ],
    }


def copy_kernel(cores):
    """Disjoint cold lines with externally specified output values per core."""
    raw = register_kernel(cores)
    raw["name"] = "multicore-cold-copy"
    raw["unit_of_work"] = {"description": "one copied cache line", "count": cores * 8}
    raw["init"] = {"memory": []}
    raw["expected"] = {"memory": []}
    raw["scenario"] = {"memory": {
        "type": "line_tracking", "cold_level": "memory", "hardware_prefetcher": "off"
    }}
    for core, stream in enumerate(raw["streams"]):
        del stream["expected"]
        src = 0x100000 + core * 0x10000
        dst = src + 0x8000
        stream["init"]["registers"].update({"rax": src, "rbx": dst})
        values = [float(core * 128 + i + 1) for i in range(128)]
        raw["init"]["memory"].extend([
            {"addr": src, "f32": values}, {"addr": dst, "f32": [0.0] * 128}
        ])
        raw["expected"]["memory"].append({"addr": dst, "f32": values})
        stream["instructions"] = []
        for line in range(8):
            stream["instructions"].extend([
                {"id": "load%d" % line, "op": "vmovaps",
                 "ops": ["zmm0", {"base": "rax", "disp": 64 * line}]},
                {"id": "store%d" % line, "op": "vmovaps",
                 "ops": [{"base": "rbx", "disp": 64 * line}, "zmm0"]},
            ])
    return raw


class TestMulticoreCLI(unittest.TestCase):
    def invoke(self, command, raw=None, *options):
        # All generated inputs/results are temporary and removed even on failure.
        with tempfile.TemporaryDirectory(prefix="knc-twin-multicore-") as work:
            args = [command]
            if raw is not None:
                path = os.path.join(work, "kernel.json")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(raw, f)
                args.append(path)
            out = os.path.join(work, "out")
            args.extend(list(options) + ["--out", out])
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                try:
                    code = cli.main(args)
                except SystemExit as exc:
                    code = exc.code
            result = None
            path = os.path.join(out, "result.json")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    result = json.load(f)
            return code, result, stderr.getvalue() + stdout.getvalue()

    def prediction(self, raw, scale):
        code, result, diagnostic = self.invoke("simulate", raw, "--scale", scale)
        self.assertEqual(code, 0, diagnostic)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["scale"], scale)
        self.assertEqual(result["result_type"], "timing_prediction")
        self.assertEqual(result["functional_check"]["status"], "ok")
        pred = result["prediction"]
        if scale in ("unit", "ring"):
            self.assertEqual(pred["result_class"]["class"], "unvalidated_scenario_estimate")
            self.assertTrue(result["assumptions"])
            self.assertTrue(result["parameters_used"])
            self.assertTrue(result["calibration_status"])
            self.assertIn("unsupported", result)
            self.assertIn("limiting_constraints", result)
        return pred

    def test_capabilities_distinguish_simulation_and_formulas(self):
        code, result, diagnostic = self.invoke("capabilities")
        self.assertEqual(code, 0, diagnostic)
        scales = result["capabilities"]["scales"]
        for scale in ("unit", "ring"):
            with self.subTest(scale=scale):
                self.assertIn(scale, scales)
                self.assertIn("simulat", scales[scale].lower())
        for scale in ("pair", "card"):
            self.assertIn("analytical", scales[scale].lower())

    def test_register_only_tiles_preserve_core_schedule(self):
        for contexts in (1, 4):
            baseline = register_kernel(1, contexts)
            for stream in baseline["streams"]:
                del stream["core"]
            core = self.prediction(baseline, "core")
            for count in (1, 2, 4, 8):
                with self.subTest(cores=count, contexts=contexts):
                    unit = self.prediction(register_kernel(count, contexts), "unit")
                    # Independent cores run concurrently, not as a single 32-context core.
                    self.assertEqual(unit["predicted_cycles"], core["predicted_cycles"])
                    self.assertEqual(unit["dynamic_instructions"], count * core["dynamic_instructions"])
                    self.assertEqual(unit["unit_count"], count * contexts)

    def test_cold_streams_complete_on_two_four_eight_tiles(self):
        baseline = copy_kernel(1)
        del baseline["streams"][0]["core"]
        core = self.prediction(baseline, "core")
        self.assertEqual(core["dynamic_instructions"], 16)
        for count in (2, 4, 8):
            with self.subTest(cores=count):
                pred = self.prediction(copy_kernel(count), "unit")
                self.assertEqual(pred["dynamic_instructions"], count * 16)
                self.assertEqual(pred["unit_count"], count * 8)
                self.assertGreater(pred["predicted_cycles"], pred["issue_span_cycles"])

    def test_ring_never_promotes_a_validated_core_shape(self):
        raw = register_kernel(8)
        raw["provenance"] = {"shape": "register_vector_chain_l1"}
        pred = self.prediction(raw, "ring")
        self.assertEqual(pred["dynamic_instructions"], 8 * 12)

    def test_invalid_placement_is_a_structured_error(self):
        duplicate = register_kernel(2)
        duplicate["streams"][1]["core"] = 0
        bad_context = register_kernel(1)
        bad_context["streams"][0]["context"] = 4
        for raw in (duplicate, bad_context, register_kernel(9)):
            with self.subTest(streams=len(raw["streams"])):
                code, result, diagnostic = self.invoke("simulate", raw, "--scale", "unit")
                self.assertEqual(code, 2, diagnostic)
                # argparse rejecting --scale is not a successful placement validation.
                self.assertIsNotNone(result, diagnostic)
                self.assertEqual(result["status"], "invalid_input")
                self.assertIsNone(result.get("prediction"))

    def test_budget_exhaustion_is_not_a_partial_prediction(self):
        for scale in ("unit", "ring"):
            with self.subTest(scale=scale):
                code, result, diagnostic = self.invoke(
                    "simulate", copy_kernel(2), "--scale", scale, "--max-cycles", "1")
                self.assertEqual(code, 5, diagnostic)
                self.assertEqual(result["status"], "budget_exhausted")
                self.assertIsNone(result.get("prediction"))
                self.assertIn("partial", result)


if __name__ == "__main__":
    unittest.main()
