"""S14-11: synthetic calibration imports, with no card or distributed tables."""
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from helpers import kernel, profile
from knc_model import NATIVE_MEASUREMENT_SCHEMA, functional, native, reciprocal_tables
from knc_model.errors import InvalidInput, Unsupported


class TestWrfImports(unittest.TestCase):
    def measurement(self, root, kind, rows, **extra):
        data = dict(schema=NATIVE_MEASUREMENT_SCHEMA, kind=kind, job_id="synthetic-test",
                    measured_utc="2026-11-15T00:00:00Z", card_profile="synthetic-demo", results=rows)
        data.update(extra)
        path = root / "measurement.json"
        path.write_text(json.dumps(data))
        return str(path)

    def test_scatter_import_sets_only_the_measured_occupancy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self.measurement(root, "scatter", [{"cycles_per_line": 3.25}])
            result = native.import_native(path, None, tmp)
            self.assertTrue(result["overlay_written"])
            overlay = root / "overlay-profile.json"
            raw = json.loads(overlay.read_text())
            self.assertEqual(set(raw["parameters"]), {"occupancy.scatter_cycles_per_line"})
            p = profile(overlays=[str(overlay)])
            self.assertEqual(p.get("occupancy.scatter_cycles_per_line"), 3.25)
            self.assertEqual(p.param("occupancy.scatter_cycles_per_line").status, "measured")
            for value in (0, -1, float("nan"), True):
                path = self.measurement(root, "scatter", [{"cycles_per_line": value}])
                with self.assertRaises(InvalidInput):
                    native.import_native(path, None, tmp)

    def test_capture_import_and_active_lanes_use_synthetic_words(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "capture.bin"
            words = [0x3f700000 + i for i in range(1024)]  # deliberately unlike rounded reciprocals
            source.write_bytes(struct.pack("<1024I", *words))
            rows = [{"op": op, "file": "capture.bin", "entries": 1024, "exponent_scaling_verified": True}
                    for op in ("vrcp23ps", "vrsqrt23ps")]
            path = self.measurement(root, "rcp23-table", rows, synthetic=True)
            with patch.object(reciprocal_tables, "resource_path", side_effect=lambda *parts: str(root.joinpath(*parts))):
                result = native.import_native(path, None, str(root / "out"))
                policy = result["numerical_policy"]
                self.assertFalse(result["overlay_written"])
                self.assertEqual(json.loads((root / "out/numerical-policy.json").read_text()), policy)
                for op in ("vrcp23ps", "vrsqrt23ps"):
                    # Inactive lanes are out of the synthetic range, and must not access it.
                    values = [0x3f800000 + i for i in range(8)] + [0x3fffffff] * 8
                    expected = words[:8] + [0] * 8
                    k = kernel(None, numerical_policy=policy,
                               init={"registers": {"zmm1": {"u32": values}, "k1": 255}},
                               streams=[{"context": 0, "asm": op + " %zmm1,%zmm0{%k1}"}],
                               expected={"registers": {"0": {"zmm0": {"u32": expected}}}})
                    interp, _, check = functional.run_functional(k)
                    self.assertEqual(check["status"], "ok", check)
                    self.assertFalse(interp.approximate_instructions)
                    self.assertTrue(any("synthetic table" in s for s in interp.assumptions))
                tables = reciprocal_tables.Tables(policy["reciprocal_tables"])
                self.assertEqual(tables.lookup("vrcp23ps", 0xc0000000), (words[0] - (1 << 23)) | 0x80000000)
                self.assertEqual(tables.lookup("vrsqrt23ps", 0x40800000), words[0] - (1 << 23))
                with self.assertRaises(Unsupported):
                    tables.lookup("vrsqrt23ps", 0x40000000)  # odd parity absent from the synthetic table
                for desc in policy["reciprocal_tables"].values():
                    reciprocal_tables_path = Path(reciprocal_tables.table_path(desc["file"]))
                    reciprocal_tables_path.unlink()
                # Descriptors and kernels load lazily, even if no capture is present yet.
                reciprocal_tables.Tables(policy["reciprocal_tables"])
                with self.assertRaises(InvalidInput):
                    tables.lookup("vrcp23ps", 0x3f800000)

    def test_capture_size_and_verification_are_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "capture.bin").write_bytes(bytes(4096))
            row = {"op": "vrcp23ps", "file": "capture.bin", "entries": 1024, "exponent_scaling_verified": True}
            path = self.measurement(root, "rcp23-table", [row])
            with self.assertRaisesRegex(InvalidInput, "entries"):
                native.import_native(path, None, tmp)
            row["entries"] = 1 << 23
            path = self.measurement(root, "rcp23-table", [row])
            with self.assertRaisesRegex(InvalidInput, "byte length"):
                native.import_native(path, None, tmp)
            row["exponent_scaling_verified"] = False
            path = self.measurement(root, "rcp23-table", [row])
            with self.assertRaisesRegex(InvalidInput, "scaling"):
                native.import_native(path, None, tmp)


if __name__ == "__main__":
    unittest.main()
