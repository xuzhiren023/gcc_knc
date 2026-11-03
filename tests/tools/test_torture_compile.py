"""S1-05: exercise corpus options through compile, assembly and lint."""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT.parent / '_shared'


class TortureOptionsTest(unittest.TestCase):
    def test_both_option_directives(self):
        summary = SHARED / 'torture-options.txt'
        subprocess.run([sys.executable, str(ROOT / 'tools/torture_compile.py'),
                        '--source', str(ROOT / 'tests/t1/knc-torture-options.c'),
                        '--level', 'O0', '--output', str(SHARED / 'torture-options'),
                        '--summary', str(summary)], check=True)
        self.assertIn('O0\t1\t0\t0\t0\t0\t0\t0\t0\t0',
                      summary.read_text(encoding='utf8'))


if __name__ == '__main__':
    unittest.main()
