"""S5-03 FP32 division and square-root exact integer models."""
from pathlib import Path
import subprocess
import tempfile
import unittest

class SqrtModel(unittest.TestCase):
    def test_exhaustive(self):
        source = Path(__file__).with_name('knc-sqrt-model.c')
        with tempfile.TemporaryDirectory(prefix='knc-sqrt-') as directory:
            exe = str(Path(directory) / 'model')
            subprocess.run(['gcc', '-O3', '-std=gnu11', str(source), '-o', exe], check=True)
            subprocess.run([exe], check=True)

class DivModel(unittest.TestCase):
    def test_models(self):
        source = Path(__file__).with_name('knc-div-model.c')
        with tempfile.TemporaryDirectory(prefix='knc-div-') as directory:
            exe = str(Path(directory) / 'model')
            subprocess.run(['gcc', '-O3', '-std=gnu11', str(source), '-o', exe], check=True)
            subprocess.run([exe], check=True)
            result = subprocess.run([exe, '--omit-step-15'], text=True,
                                    stdout=subprocess.PIPE)
            print(result.stdout, flush=True)
            self.assertEqual(result.returncode, 1)
            lines = result.stdout.splitlines()
            self.assertEqual(sum('condC_fail=1 ' in x for x in lines), 2)
            self.assertEqual(sum('fail RN=1 RD=0 RU=0 RZ=0' in x for x in lines), 12)
            self.assertTrue(any(x.startswith('E4 ') and 'fail RN=2 RD=0 RU=0 RZ=0' in x
                                for x in lines))


class V8dfModel(unittest.TestCase):
    """S10-09 FP64 division and square root: 53-bit MPFR emulation of both sequences."""
    def test_models(self):
        source = Path(__file__).with_name('knc-v8df-model.c')
        clean = 'fail RN=0 RD=0 RU=0 RZ=0'
        with tempfile.TemporaryDirectory(prefix='knc-v8df-') as directory:
            exe = str(Path(directory) / 'model')
            subprocess.run(['gcc', '-O2', '-std=gnu11', str(source), '-o', exe,
                            '-lmpfr', '-lgmp'], check=True)
            subprocess.run([exe], check=True)
            # Each all-ones blend is needed, and only under round to nearest.
            for option, broken, intact in (('--omit-div-blend', 'div', 'sqrt'),
                                           ('--omit-sqrt-blend', 'sqrt', 'div')):
                result = subprocess.run([exe, option], text=True, stdout=subprocess.PIPE)
                print(result.stdout, flush=True)
                self.assertEqual(result.returncode, 1)
                lines = [x for x in result.stdout.splitlines() if ' fail RN=' in x]
                kind = lambda x: 'div' if x.startswith(('D2', 'div')) else 'sqrt'
                self.assertTrue(all(clean in x for x in lines if kind(x) == intact))
                failing = [x for x in lines if clean not in x]
                self.assertTrue(failing)
                self.assertTrue(all(kind(x) == broken and ' RD=0 RU=0 RZ=0' in x
                                    for x in failing))
                # Lemma B's condition fails for the all-ones divisor alone.
                self.assertIn('condC_fail=2' if broken == 'div' else 'condC_fail=0',
                              next(x for x in result.stdout.splitlines()
                                   if x.startswith('D1 ')))


if __name__ == '__main__':
    unittest.main()
