import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "knc-twin"
SCRIPT = TWIN / "scripts" / "knc_twin.py"
PHIWEATHER = ROOT.parent.parent / "twin-study-20261116" / "sixth" / "held-out"


class NativeEmit(unittest.TestCase):
    def test_rollup_classification_requires_candidate_held_out_band(self):
        from knc_twin.scripts.knc_model.cli import rollup_result_class

        self.assertEqual(rollup_result_class([{"ratio": 1.0}], [])["class"],
                         "unvalidated_scenario_estimate")
        self.assertEqual(rollup_result_class([], [])["class"],
                         "unvalidated_scenario_estimate")
        self.assertEqual(rollup_result_class([{"candidate": {}, "band_basis": "held-out S12-31"}], [])["class"],
                         "calibrated_forecast")

    def test_prepare_native_relocates_absolute_memory_operands(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            kernel = tmp / "kernel.json"
            kernel.write_text(json.dumps({
                "schema": "knc-twin.kernel/1",
                "name": "absolute-memory-relocation",
                "init": {"memory": [{"addr": "0x1000", "u64": [7]}]},
                "streams": [{"asm": "movq 0x1000, %rax\nret"}],
            }), encoding="utf-8")
            output = tmp / "output"
            result = subprocess.run([
                sys.executable, str(SCRIPT), "prepare-native", str(kernel),
                "--out", str(output), "--no-check",
            ], cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.assertEqual(result.returncode, 0, result.stdout[-3000:])
            asm = (output / "kernel.S").read_text(encoding="utf-8")
            self.assertIn("knc_twin_mem+0(%rip)", asm)
            self.assertNotRegex(asm, r"\(\s*\)")

            rip = tmp / "rip.json"
            rip.write_text(json.dumps({
                "schema": "knc-twin.kernel/1",
                "name": "absolute-rip-displacement",
                "streams": [{"asm": "movq data(%rip), %rax\nret"}],
                "init": {
                    "memory": [{"addr": "0x1000", "u64": [7, 8]}, {"addr": "0x1008", "u64": [9]}],
                    "symbols": {"data": "0x1008"},
                },
            }), encoding="utf-8")
            rip_output = tmp / "rip-output"
            rip_result = subprocess.run([
                sys.executable, str(SCRIPT), "prepare-native", str(rip),
                "--out", str(rip_output), "--no-check",
            ], cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.assertEqual(rip_result.returncode, 0, rip_result.stdout[-3000:])
            rip_asm = (rip_output / "kernel.S").read_text(encoding="utf-8")
            self.assertIn("knc_twin_mem+8(%rip)", rip_asm)

            symbol = tmp / "symbol.json"
            symbol.write_text(json.dumps({
                "schema": "knc-twin.kernel/1",
                "name": "resolved-rip-symbol-relocation",
                "init": {
                    "memory": [{"addr": "0x1000", "u64": [7]}],
                    "symbols": {"data": "0x1000"},
                },
                "streams": [{"asm": "movq data(%rip), %rax\nret"}],
            }), encoding="utf-8")
            symbol_output = tmp / "symbol-output"
            symbol_result = subprocess.run([
                sys.executable, str(SCRIPT), "prepare-native", str(symbol),
                "--out", str(symbol_output), "--no-check",
            ], cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.assertEqual(symbol_result.returncode, 0, symbol_result.stdout[-3000:])
            symbol_asm = (symbol_output / "kernel.S").read_text(encoding="utf-8")
            self.assertIn("knc_twin_mem+0(%rip)", symbol_asm)
            self.assertNotRegex(symbol_asm, r"\(\s*\)")

            outside = tmp / "outside.json"
            outside.write_text(json.dumps({
                "schema": "knc-twin.kernel/1",
                "name": "absolute-memory-outside-image",
                "init": {"memory": [{"addr": "0x1000", "u64": [7]}]},
                "streams": [{"asm": "movq 0x2000, %rax\nret"}],
            }), encoding="utf-8")
            rejected = subprocess.run([
                sys.executable, str(SCRIPT), "prepare-native", str(outside),
                "--out", str(tmp / "outside-output"), "--no-check",
            ], cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("absolute memory address 0x2000 lies outside", rejected.stdout)

    def test_rollup_needs_a_validated_candidate_shape(self):
        base = {
            "schema": "knc-twin.kernel/1", "unit_of_work": {"description": "x", "count": 1},
            "init": {}, "expected": {}, "streams": [{"context": 0, "instructions": []}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for name, extra in (("baseline", {}), ("candidate", {}),
                                ("validated", {"provenance": {"shape": "register_vector_chain_l1"}})):
                (tmp / (name + ".json")).write_text(json.dumps(dict(base, name=name, **extra)), encoding="utf-8")
            def classify(candidate):
                manifest = tmp / "manifest.json"
                region = {"name": "r", "share": 0.5, "baseline": "baseline.json"}
                if candidate:
                    region["candidate"] = candidate
                manifest.write_text(json.dumps({"schema": "knc-twin.rollup/1", "regions": [region]}), encoding="utf-8")
                output = tmp / ("out-" + str(candidate))
                result = subprocess.run([sys.executable, str(SCRIPT), "rollup", str(manifest), "--profile", "card-7120-measured", "--out", str(output)],
                                        cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                self.assertEqual(result.returncode, 0, result.stdout[-3000:])
                return json.loads((output / "result.json").read_text(encoding="utf-8"))["prediction"]["result_class"]["class"]
            self.assertEqual(classify(None), "unvalidated_scenario_estimate")
            self.assertEqual(classify("candidate.json"), "unvalidated_scenario_estimate")

    @unittest.skipUnless(PHIWEATHER.exists(), "PhiWeather held-out kernel is not available")
    def test_phiweather_kernel_has_no_empty_memory_operands(self):
        kernels = list(PHIWEATHER.rglob("*.json"))
        kernels = [p for p in kernels if "kernel" in p.name.lower()]
        self.assertTrue(kernels, "no PhiWeather kernel JSON found")
        for kernel in kernels:
            with tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "native"
                result = subprocess.run([
                    sys.executable, str(SCRIPT), "prepare-native", str(kernel),
                    "--out", str(output), "--no-check",
                ], cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                self.assertEqual(result.returncode, 0, result.stdout[-3000:])
                asm = (output / "kernel.S").read_text(encoding="utf-8")
                self.assertNotRegex(asm, r"\(\s*\)", str(kernel))


if __name__ == "__main__":
    unittest.main()
