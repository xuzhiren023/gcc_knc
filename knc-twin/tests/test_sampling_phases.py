"""S14-12 red contract: phases preserve flat rollup arithmetic and uncertainty.

Each phase has name, share (of program time), and regions whose shares are
within that phase. prediction.phases reports modeled_share_of_phase_time;
the existing program-level prediction fields retain their meaning.
Region sampling options are per side: sampling.baseline / sampling.candidate
each name a loop and its warmup, window and max_iterations. Region output
reports sampled=true whenever either side uses sampling.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import helpers


ROOT = Path(helpers.ROOT)


class TestPhaseSampling(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="knc-phases-")
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        source = ROOT / "fixtures" / "rollup" / "manifest.json"
        self.flat = json.loads(source.read_text())
        for region in self.flat["regions"]:
            for side in ("baseline", "candidate"):
                if side in region:
                    region[side] = str((source.parent / region[side]).resolve())

    def invoke(self, manifest, name):
        path = self.work / (name + ".json")
        path.write_text(json.dumps(manifest))
        out = self.work / name
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "knc_twin.py"),
                               "rollup", str(path), "--out", str(out)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads((out / "result.json").read_text())
        self.assertEqual(result["status"], "ok")
        return result["prediction"], (out / "summary.md").read_text()

    def test_hpcg_phases_match_flat_pilot_and_cover_measured_change(self):
        manifest = copy.deepcopy(self.flat)
        regions = manifest.pop("regions")
        # Splitting time this way is an algebraic test of the existing measured
        # pilot shares, not a claim of a newly measured phase profile.
        manifest["phases"] = []
        for name, share, region in zip(("SpMV phase", "MG phase"), (0.4, 0.6), regions):
            region["share"] /= share
            manifest["phases"].append({"name": name, "share": share, "regions": [region]})
        phases, summary = self.invoke(manifest, "phases")
        flat, _ = self.invoke(self.flat, "flat")
        for key in ("predicted_time_ratio", "predicted_time_ratio_band",
                    "predicted_candidate_per_unit", "predicted_candidate_per_unit_band",
                    "modeled_share_of_run_time", "unmodeled_share_assumed_unchanged"):
            self.assertEqual(phases[key], flat[key], key)
        self.assertAlmostEqual(phases["modeled_share_of_run_time"], 0.86)
        rows = {p["name"]: p for p in phases["phases"]}
        self.assertAlmostEqual(rows["SpMV phase"]["modeled_share_of_phase_time"], 0.65)
        self.assertAlmostEqual(rows["MG phase"]["modeled_share_of_phase_time"], 1.0)
        # Rating improvement is inverse wall time for the pilot's fixed work.
        lo, hi = phases["predicted_time_ratio_band"]
        self.assertLessEqual(lo, 1.0 / 1.088)
        self.assertGreaterEqual(hi, 1.0 / 1.088)
        for text in ("SpMV phase", "MG phase", "65", "seconds per HPCG pilot run"):
            self.assertIn(text, summary)

    def test_sampled_region_downgrades_forecast_and_propagates_band(self):
        manifest = copy.deepcopy(self.flat)
        regions = manifest.pop("regions")
        # Sample the existing calibrated SpMV baseline's outer row loop. The
        # candidate stays fully simulated; both retain the original inputs.
        regions[0]["sampling"] = {
            "baseline": {"loop": ".A_4108be", "warmup": 1, "window": 1,
                         "max_iterations": 8, "tolerance": 0.01}}
        manifest["phases"] = [{"name": "pilot", "share": 1.0, "regions": regions}]
        sampled, _ = self.invoke(manifest, "sampled-phase")
        flat, _ = self.invoke(self.flat, "unsampled-flat")
        self.assertEqual(flat["result_class"]["class"], "calibrated_forecast")
        self.assertEqual(sampled["result_class"]["class"],
                         "unvalidated_scenario_estimate")
        row = next(r for r in sampled["regions"] if r["name"] == regions[0]["name"])
        self.assertTrue(row["sampled"])
        self.assertEqual(row["baseline"]["result_class"]["class"],
                         "unvalidated_scenario_estimate")
        lo, hi = sampled["predicted_time_ratio_band"]
        flat_lo, flat_hi = flat["predicted_time_ratio_band"]
        self.assertGreaterEqual(hi - lo + 1e-5, flat_hi - flat_lo)
        self.assertLessEqual(lo, sampled["predicted_time_ratio"])
        self.assertGreaterEqual(hi, sampled["predicted_time_ratio"])
        scale = self.flat["program"]["measured_per_unit"]
        wall_lo, wall_hi = sampled["predicted_candidate_per_unit_band"]
        # Ratio output is rounded to five decimals; wall time retains six.
        self.assertAlmostEqual(wall_lo, scale * lo, delta=scale * 1e-5)
        self.assertAlmostEqual(wall_hi, scale * hi, delta=scale * 1e-5)

    def test_unvalidated_regions_prevent_calibrated_phase_forecast(self):
        # An unchanged ratio is still an unvalidated region; equality alone
        # must not turn a scenario estimate into a calibrated forecast.
        kernel = helpers.fixture("saxpy_loop.json")
        manifest = {"schema": "knc-twin.rollup/1",
                    "program": {"unit": "seconds per step", "measured_per_unit": 10},
                    "phases": [{"name": "synthetic phase", "share": 0.5,
                                "regions": [{"name": "unvalidated region", "share": 0.5,
                                             "baseline": kernel, "candidate": kernel}]}]}
        pred, _ = self.invoke(manifest, "unvalidated")
        self.assertEqual(pred["result_class"]["class"], "unvalidated_scenario_estimate")
        self.assertAlmostEqual(pred["modeled_share_of_run_time"], 0.25)
        self.assertAlmostEqual(pred["unmodeled_share_assumed_unchanged"], 0.75)
        self.assertAlmostEqual(pred["predicted_candidate_per_unit"], 10)


if __name__ == "__main__":
    unittest.main()
