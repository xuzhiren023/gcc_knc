"""E3: exact integer emulation, all reduced FP32 inputs and rounding modes."""
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

if __name__ == '__main__':
    unittest.main()
