"""S6-07 directive parsing against three unmodified GCC vect sources."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import vect_suite

CORPUS = ROOT.parent / '_shared/gcc/gcc/testsuite/gcc.dg/vect'


class RealVectHeaders(unittest.TestCase):
    def test_compile_header(self):
        spec = vect_suite.parse_directives((CORPUS / 'vect-1.c').read_text())
        self.assertEqual(spec.action, 'compile')
        self.assertEqual(spec.options, ['-fdump-tree-optimized-details-blocks'])
        self.assertEqual(spec.skip, [])
        self.assertGreater(spec.scans, 0)

    def test_incompatible_avx512_header(self):
        spec = vect_suite.parse_directives((CORPUS / 'pr88497-6.c').read_text())
        self.assertEqual(spec.action, 'compile')
        self.assertIn('-mavx512f', spec.options)
        self.assertTrue(any('avx512f' in reason for reason in spec.skip))

    def test_default_run_and_braced_options(self):
        spec = vect_suite.parse_directives((CORPUS / 'vect-bitfield-read-1-not.c').read_text())
        self.assertEqual(spec.action, 'run')
        self.assertEqual(spec.options, ['-fdump-tree-ifcvt-all'])
        self.assertTrue(any('vect_long_long' in reason for reason in spec.skip))


if __name__ == '__main__':
    unittest.main()
