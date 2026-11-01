"""S0-01: required tools fail usefully; optional test tools may be absent."""
import contextlib
import io
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
doctor = runpy.run_path(str(ROOT / "tools" / "doctor"))


class Doctor(unittest.TestCase):
    def check(self, required):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sysroot/usr/include").mkdir(parents=True)
            (root / "sysroot/lib64").mkdir()
            manifest = {"sysroot": "sysroot", "tools": [
                {"name": "gcc", "path": "gcc", "version": "14.4.0",
                 "role": "host compiler", "required": True},
                {"name": "expect", "path": "expect", "version": None,
                 "role": "optional test driver", "required": required}]}
            (root / "gcc").touch()
            output = io.StringIO()
            with contextlib.redirect_stdout(output), patch("subprocess.run") as run:
                run.return_value = subprocess.CompletedProcess([], 0, "gcc 14.4.0\n")
                result = doctor["check"](manifest, root)
                run.assert_called_once()
            return result, output.getvalue()

    def test_optional_absence_reports_version_and_succeeds(self):
        result, output = self.check(False)
        self.assertEqual(result, 0)
        self.assertIn("14.4.0", output)
        self.assertIn("ABSENT expect", output)

    def test_required_absence_fails_with_tool_and_path(self):
        result, output = self.check(True)
        self.assertNotEqual(result, 0)
        self.assertIn("MISSING expect", output)
        self.assertIn("expect", output)


if __name__ == "__main__":
    unittest.main()
