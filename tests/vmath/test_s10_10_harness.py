#!/usr/bin/env python3
"""Regression coverage for S10-10 harness changes."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class HarnessRegression(unittest.TestCase):
    def test_card_binary_staging_and_missing_binary(self):
        project = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
        shared = project / '.work/_shared'
        original = ROOT / 'tests/vmath/card_qualify.py'
        source = original.read_text(encoding='utf8')
        old = source.replace("binary = OUT / 'knc' / (program + '.mic')", "binary = OUT / target / (program + '.mic')")
        self.assertNotEqual(old, source)
        with tempfile.TemporaryDirectory() as baseline_tmp:
            baseline = Path(baseline_tmp) / 'card_qualify.py'
            baseline.write_text(old, encoding='utf8')
            probe = subprocess.run([sys.executable, str(baseline), '--dry-run', '--out', 'S10-08',
                                    '--set', 'negative'], cwd=ROOT, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertNotEqual(probe.returncode, 0, probe.stdout)
        with tempfile.TemporaryDirectory(dir=shared) as tmp:
            out = Path(tmp)
            (out / 'card').mkdir()
            knc = out / 'knc'
            knc.mkdir()
            for program in ('qualify_f', 'qualify_d', 'qualify_v1'):
                (knc / (program + '.mic')).write_bytes(b'test binary')
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
            cmd = [sys.executable, str(ROOT / 'tests/vmath/card_qualify.py'),
                   '--dry-run', '--out', out.name, '--set', 'negative']
            result = subprocess.run(cmd, cwd=ROOT, env=env, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn(str(knc / 'qualify_f.mic'), result.stdout)
            self.assertIn(str(knc / 'qualify_d.mic'), result.stdout)
            self.assertIn(str(knc / 'qualify_v1.mic'), result.stdout)
            (knc / 'qualify_f.mic').unlink()
            missing = subprocess.run(cmd, cwd=ROOT, env=env, text=True,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertNotEqual(missing.returncode, 0, missing.stdout)
            self.assertRegex(missing.stdout.lower(), r'missing.*qualify_f|qualify_f.*missing')

    def test_independent_batch_calibration_and_timing_ratio(self):
        compiler = os.environ.get('CC')
        self.assertTrue(compiler, 'set CC to the host C compiler')
        self.assertTrue(shutil.which(compiler), 'host C compiler not found: ' + compiler)
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / 'bench'
            src = ROOT / 'tests/bench/vmath'
            objects = []
            for name, extra in (('vec', []), ('scl', ['-fno-tree-vectorize'])):
                obj = Path(tmp) / ('kernels-%s.o' % name)
                build = subprocess.run([compiler, '-O2', '-fno-math-errno', *extra, '-DBUILD=' + name,
                                        '-c', str(src / 'kernels.c'), '-o', str(obj)], text=True,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                self.assertEqual(build.returncode, 0, build.stdout)
                objects.append(str(obj))
            build = subprocess.run([compiler, '-O2', '-pthread', '-DS10_10_HOST_TEST', str(src / 'driver.c'), *objects,
                                    '-lm', '-o', str(exe)], text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertEqual(build.returncode, 0, build.stdout)
            run = subprocess.run([str(exe), '--cores', '1', '--density', '1',
                                  '--rounds', '1', '--batches', '1',
                                  '--set', 'l2', '--kernel', 'expf'], text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
            self.assertEqual(run.returncode, 0, run.stdout)
            sizing = re.search(r'reps_vec=(\d+) reps_scl=(\d+)', run.stdout)
            self.assertIsNotNone(sizing, run.stdout)
            reps_vec, reps_scl = map(int, sizing.groups())
            self.assertNotEqual(reps_vec, reps_scl, run.stdout)
            batches = re.findall(r'batches .*seconds=([0-9.,]+)', run.stdout)
            self.assertEqual(len(batches), 2, run.stdout)
            for group in batches:
                for value in group.split(','):
                    self.assertGreaterEqual(float(value), .05, run.stdout)
                    self.assertLessEqual(float(value), .2, run.stdout)
            ratio = float(re.search(r'ratio_vec_over_scl=([0-9.]+)', run.stdout).group(1))
            vec = float(re.search(r'batch_ms_vec=([0-9.]+)', run.stdout).group(1))
            scl = float(re.search(r'batch_ms_scl=([0-9.]+)', run.stdout).group(1))
            expected = (vec / reps_vec) / (scl / reps_scl)
            self.assertAlmostEqual(ratio, expected, delta=.03)


if __name__ == '__main__':
    unittest.main()
