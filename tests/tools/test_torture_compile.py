"""S1-05: exercise corpus options through compile, assembly and lint."""
from pathlib import Path
import subprocess
import sys
import runpy
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import storage

SHARED = Path(storage.shared_area(storage.main_root(ROOT)))


class TortureOptionsTest(unittest.TestCase):
    def test_both_option_directives(self):
        summary = SHARED / 'torture-options.txt'
        subprocess.run([sys.executable, str(ROOT / 'tools/torture_compile.py'),
                        '--source', str(ROOT / 'tests/t1/knc-torture-options.c'),
                        '--level', 'O0', '--output', str(SHARED / 'torture-options'),
                        '--summary', str(summary)], check=True)
        self.assertIn('O0\t1\t0\t0\t0\t0\t0\t0\t0\t0\t0',
                      summary.read_text(encoding='utf8'))

    def test_user_inline_asm(self):
        summary = SHARED / 'torture-inline-asm.txt'
        subprocess.run([sys.executable, str(ROOT / 'tools/torture_compile.py'),
                        '--source', str(ROOT / 'tests/tools/knc-torture-inline-asm.c'),
                        '--level', 'O0', '--output', str(SHARED / 'torture-inline-asm'),
                        '--summary', str(summary)], check=True)
        self.assertIn('O0 / user inline asm rejected (1)',
                      summary.read_text(encoding='utf8'))

    def test_every_assembler_error_must_be_inside_app(self):
        classify = runpy.run_path(str(ROOT / 'tools/torture_compile.py'))['user_asm_rejection']
        with tempfile.TemporaryDirectory(dir=SHARED) as temporary:
            asm = Path(temporary) / 'case.s'
            asm.write_text('.text\n#APP\n# 9 "case.c" 1\nbad_user\n#NO_APP\nbad_generated\n')
            inside = 'case.c:9: Error: no such instruction: bad_user\n'
            outside = 'case.c:11: Error: no such instruction: bad_generated\n'
            self.assertTrue(classify(asm, inside))
            self.assertFalse(classify(asm, inside + outside))
            self.assertFalse(classify(asm, 'Error: unlocated error\n'))


if __name__ == '__main__':
    unittest.main()
