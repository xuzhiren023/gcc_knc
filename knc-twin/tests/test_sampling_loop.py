"""S14-12 red contract for brief 04: loop sampling, not native validation.

Proposed JSON contract: prediction.sampling contains windows (iterations and
cycles_per_iteration), iterations_sampled, stop_reason, and the last-window
cycles_per_iteration_band. prediction.predicted_cycles_per_unit_band also
includes model uncertainty. Recorded held-out values are comparison targets
only; they must never be inputs to the sampler or used to tune its parameters.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import helpers


ROOT = Path(helpers.ROOT)
HELDOUT = ROOT / "tests" / "heldout_native"
KT = ROOT / "scripts" / "knc_twin.py"


class TestLoopSampling(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="knc-sampling-")
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)

    def invoke(self, command, kernel, label, *options):
        args = [sys.executable, str(KT), command, str(kernel)]
        if command == "simulate":
            args.append("--sample-loop")
        args += ["--loop", label, *options, "--out", str(self.work / "out")]
        proc = subprocess.run(args, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads((self.work / "out" / "result.json").read_text())
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["sampled"])
        pred = result["prediction"]
        self.assertEqual(pred["result_class"]["class"],
                         "unvalidated_scenario_estimate")
        return pred

    def test_stable_loop_series_spread_and_extrapolation(self):
        pred = self.invoke("sample-loop", helpers.fixture("budget_long_loop.json"),
                           "L", "--warmup", "8", "--window", "8",
                           "--tolerance", "0.01", "--max-iterations", "128")
        sampling = pred["sampling"]
        self.assertEqual(sampling["stop_reason"], "converged")
        self.assertLess(sampling["iterations_sampled"], 128)
        windows = sampling["windows"]
        self.assertGreaterEqual(len(windows), 3)
        for window in windows:
            self.assertGreaterEqual(window["iterations"], 8)
            self.assertGreater(window["cycles_per_iteration"], 0)
        last = [w["cycles_per_iteration"] for w in windows[-3:]]
        self.assertEqual(sampling["cycles_per_iteration_band"], [min(last), max(last)])
        cpi = pred["predicted_cycles_per_unit"]
        self.assertGreaterEqual(cpi, min(last))
        self.assertLessEqual(cpi, max(last))
        self.assertAlmostEqual(pred["predicted_cycles"], cpi * 20000)

    def test_simulate_option_has_same_sampling_result(self):
        options = ("--warmup", "8", "--window", "8", "--max-iterations", "128")
        kernel = helpers.fixture("budget_long_loop.json")
        direct = self.invoke("sample-loop", kernel, "L", *options)
        option = self.invoke("simulate", kernel, "L", *options)
        for key in ("sampling", "predicted_cycles", "predicted_cycles_per_unit_band"):
            self.assertEqual(direct[key], option[key])

    def test_iteration_budget_is_reported_without_false_convergence(self):
        pred = self.invoke("sample-loop", helpers.fixture("budget_long_loop.json"),
                           "L", "--warmup", "0", "--window", "8",
                           "--max-iterations", "16")
        self.assertEqual(pred["sampling"]["stop_reason"], "max_iterations")
        self.assertLessEqual(pred["sampling"]["iterations_sampled"], 16)

    def test_s12_30_random_rows_cover_the_input_period(self):
        # Three identical calls, each with 32 random-column rows. Sampling a
        # row (not the inner nonzero loop) must see all 32 before convergence.
        raw = json.loads((HELDOUT / "s12-30-small" / "kernels" /
                          "csr27-donor-off.json").read_text())
        raw["unit_of_work"] = {"description": "one row (27 nonzeros)", "count": 96}
        path = self.work / "random-rows.json"
        path.write_text(json.dumps(raw))
        pred = self.invoke("sample-loop", path, ".A_10", "--warmup", "0",
                           "--window", "4", "--max-iterations", "96")
        sample = pred["sampling"]
        self.assertGreaterEqual(sample["iterations_sampled"], 32)
        self.assertTrue(any(w["iterations"] > 4 for w in sample["windows"]),
                        "windows must widen to cover the longer input period")

    def test_hpcg104_band_covers_recorded_slope_and_measurement(self):
        # Reuse the existing faithful input generator in a disposable directory;
        # neither the recorded kernels nor held-out evidence are rewritten.
        spec = importlib.util.spec_from_file_location(
            "sampling_hpcg_inputs", HELDOUT / "make_s12_31_hpcg104.py")
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        generator.OUT_DIR = str(self.work)
        generator.write_inputs()
        case_dir = HELDOUT / "s12-31-hpcg-104"
        raw = json.loads((case_dir / "kernels" / "donor_spmv.json").read_text())
        for block in raw["init"]["memory"]:
            if "file" in block:
                block["file"] = str(self.work / "input" / Path(block["file"]).name)
        raw["expected"] = {"memory": [{"addr": "0x70000000",
                            "file": str(self.work / "input" / "y_8000.bin")}]}
        path = self.work / "hpcg.json"
        path.write_text(json.dumps(raw))
        pred = self.invoke("sample-loop", path, ".A_40f2f0", "--warmup", "104",
                           "--window", "104", "--max-iterations", "2080")
        self.assertLess(pred["sampling"]["iterations_sampled"], 8000)
        lo, hi = pred["predicted_cycles_per_unit_band"]
        self.assertGreater(lo, 0)
        self.assertGreaterEqual(hi, lo)
        recorded = json.loads((case_dir / "prediction.json").read_text())
        donor = next(v for v in recorded["variants"] if v["variant"] == "donor")
        units = json.loads((case_dir / "case.json").read_text())["slope"]["units"]
        cycles = donor["completion_cycles"]
        slope = (cycles[1] - cycles[0]) / (units[1] - units[0])
        native = json.loads((case_dir / "measurement.json").read_text())
        for reference in (slope, native["per_variant"]["donor"]):
            self.assertLessEqual(lo, reference)
            self.assertGreaterEqual(hi, reference)


if __name__ == "__main__":
    unittest.main()
