"""Host checks for the diagnostic output reader; no card execution."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[2] / 'tools/s12_12_stage.py'
spec = importlib.util.spec_from_file_location('stage', PATH)
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class Results(unittest.TestCase):
    def test_pass(self):
        self.assertEqual(stage.read_result('noise\nRESULT G04 PASS\n', 'G04'), 'PASS')

    def test_unavailable_is_not_pass(self):
        self.assertEqual(stage.read_result('RESULT G06 UNAVAILABLE\n', 'G06'), 'UNAVAILABLE')

    def test_missing_truncated_duplicate_wrong_and_failed(self):
        for text in ('', 'RESULT G04 PAS', 'RESULT G04 PASS\nRESULT G04 PASS\n',
                     'RESULT G05 PASS\n', 'RESULT G04 FAIL\n',
                     'RESULT G04 PASS extra\n', 'RESULT G04 PASS\nRESULT G05 FAIL\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                stage.read_result(text, 'G04')

    def test_pmu_ring_records(self):
        import struct
        sample = struct.pack('<IHHQ', 9, 0, 16, 0x1234)
        lost = struct.pack('<IHHQQ', 2, 0, 24, 7, 19)
        self.assertEqual(stage.decode_samples(sample + lost), (1, 19))
        for data in (sample[:-1], struct.pack('<IHH', 9, 0, 0),
                     struct.pack('<IHH', 2, 0, 8)):
            with self.subTest(data=data), self.assertRaises(ValueError):
                stage.decode_samples(data)


if __name__ == '__main__':
    unittest.main()
