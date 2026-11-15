"""S13-06: knc-twin selftest, the trial kernels' functional check, and held-out predictions.

The held-out predictions in knc-twin/tests/heldout_native/*/prediction.json were recorded before
comparison with the native numbers; for the same engine version and profile hash they must not
change. A changed engine or profile fails here until the predictions are re-recorded on purpose.
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TWIN = ROOT / "knc-twin"
TRIAL = TWIN / "tests" / "trial"
HELDOUT = TWIN / "tests" / "heldout_native"


def trial_lib():
    spec = importlib.util.spec_from_file_location("knc_trial", TRIAL / "knc_trial.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class KncTwin(unittest.TestCase):
    def test_selftest_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = subprocess.run([sys.executable, str(TWIN / "scripts" / "knc_twin.py"), "selftest"], cwd=tmp,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        self.assertEqual(out.returncode, 0, out.stdout[-3000:])
        self.assertRegex(out.stdout, r"Ran \d+ tests")
        self.assertRegex(out.stdout, r"\nOK\b")

    def test_trial_cases_convert_and_run_as_recorded(self):
        lib = trial_lib()
        cases = lib.load_cases(TRIAL)
        self.assertGreaterEqual(len(cases), 10)
        with tempfile.TemporaryDirectory() as tmp:
            for case in cases:
                with self.subTest(case=case["name"]):
                    got = lib.check_case(case, Path(tmp))
                    self.assertEqual(got, case["expect"])

    def test_heldout_predictions_unchanged(self):
        lib = trial_lib()
        dirs = sorted(d for d in HELDOUT.iterdir() if d.is_dir())
        self.assertTrue(dirs, "no held-out cases")
        with tempfile.TemporaryDirectory() as tmp:
            for d in dirs:
                with self.subTest(case=d.name):
                    recorded = json.loads((d / "prediction.json").read_text(encoding="utf-8"))
                    self.assertEqual(lib.predict_heldout(d, Path(tmp)), recorded)
                    measurement = json.loads((d / "measurement.json").read_text(encoding="utf-8"))
                    self.assertTrue(measurement.get("source_log"), "measurement.json must cite its source log")


if __name__ == "__main__":
    unittest.main()
