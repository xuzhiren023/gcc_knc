#!/usr/bin/env python3
"""Exercise the benchmark's real calibration/measurement with a simulated clock.

Run with host Cygwin Python and gcc through tools/run.py. The production driver
is included unchanged; only its clock and numerical kernels are substituted.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


class BatchCalibration(unittest.TestCase):
    def test_double_batches_after_transient(self):
        source = Path(__file__).with_name('s12_18_batch_probe.c')
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'batch-probe.exe'
            build = subprocess.run(
                [os.environ.get('CC', 'gcc'), '-O2', '-std=gnu11', '-pthread',
                 str(source), '-lm', '-o', str(binary)],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertEqual(build.returncode, 0, build.stdout)
            for k, name in enumerate(('exp', 'log', 'pow'), start=3):
                for cold_calls in (0, 7):
                    with self.subTest(kernel=name, cold_calls=cold_calls):
                        run = subprocess.run(
                            [str(binary), str(k), str(cold_calls)],
                            text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=10)
                        self.assertEqual(run.returncode, 0, run.stdout)
                        samples = re.findall(
                            r'^batches .*seconds=([0-9.,]+)$', run.stdout, re.M)
                        self.assertEqual(len(samples), 6, run.stdout)
                        for group in samples:
                            values = [float(v) for v in group.split(',')]
                            self.assertEqual(len(values), 3, run.stdout)
                            for value in values:
                                self.assertGreaterEqual(value, .05, run.stdout)
                                self.assertLessEqual(value, .2, run.stdout)
                        self.assertIn('batches=valid', run.stdout)
                        ratios = re.findall(
                            r'^round .*ratio_vec_over_scl=([0-9.]+)$',
                            run.stdout, re.M)
                        self.assertEqual(len(ratios), 3, run.stdout)
                        for ratio in ratios:
                            # Changing reps must preserve time-per-element ratios.
                            self.assertAlmostEqual(float(ratio), 1.25, delta=.001)


if __name__ == '__main__':
    unittest.main()
