"""S5-03 E1/E2/E4, including the omitted-step-15 negative control."""
from pathlib import Path
import subprocess
import tempfile
import unittest


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


if __name__ == '__main__':
    unittest.main()
