"""Small host correctness contract; run through tools/run.py, never on the card."""
import json
import os
from pathlib import Path
import subprocess
import shlex
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
OUT = PROJECT / '.work/_shared/S11-05'


class MemoryBandwidth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(exist_ok=True)
        cls.binary = OUT / 'membw-host'
        subprocess.run(['gcc', '-O2', '-std=gnu11', '-Wall', '-Wextra',
                        '-Werror', '-pthread', str(HERE / 'membw.c'),
                        '-o', str(cls.binary)], check=True)

    def run_case(self, *options):
        result = subprocess.run([str(self.binary), '--mib', '1', '--passes', '2',
                                 '--repeats', '5', *options], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        rows = [row for row in rows if row.get('kind') == 'result']
        self.assertEqual({r['workload'] for r in rows},
                         {'read', 'write', 'copy', 'triad', 'rmw', 'stencil'})
        for row in rows:
            self.assertTrue(row['valid'])
            self.assertEqual(row['samples'], 5)
            self.assertGreater(row['min_GBs'], 0)
            self.assertLessEqual(row['min_GBs'], row['median_GBs'])
            self.assertLessEqual(row['median_GBs'], row['max_GBs'])
            self.assertEqual(row['threads'], row['allowed_cpus'])
            self.assertEqual(len(set(row['cpus'])), row['threads'])
            self.assertEqual(len(row['timings']), 5)
            rates = []
            for sample in row['timings']:
                self.assertGreater(sample['seconds'], 0)
                self.assertGreaterEqual(sample['wall_seconds'], sample['seconds'])
                self.assertGreaterEqual(sample['start_skew_seconds'], 0)
                rates.append(row['logical_bytes'] / sample['seconds'] / 1e9)
            self.assertAlmostEqual(sorted(rates)[2], row['median_GBs'], places=5)
        return rows

    def test_all_kernels_and_controls(self):
        self.run_case('--store', 'normal', '--pages', 'small')
        self.run_case('--store', 'ngo', '--pages', 'huge', '--placement', 'spread',
                      '--pf0', '8', '--pf1', '32', '--prefetch', 'exclusive',
                      '--fence', 'chunk', '--evict', 'both', '--offset-lines', '3',
                      '--padding-lines', '5', '--chunk-lines', '17',
                      '--schedule', 'cyclic', '--unroll', '4', '--split', '1',
                      '--read-chains', '4')
        self.run_case('--store', 'nr', '--placement', 'reverse', '--prefetch', 'l2',
                      '--fence', 'line', '--unroll', '8', '--chunk-lines', '31',
                      '--pass-fence', 'final', '--read-chains', '1')

    def test_invalid_configuration(self):
        for options in [('--repeats', '4'), ('--unroll', '0'), ('--mib', '0'),
                        ('--store', 'bogus'), ('--threads', '99999'),
                        ('--fence', 'none'), ('--offset-lines', '-1'),
                        ('--pass-fence', 'none'), ('--read-chains', '2')]:
            result = subprocess.run([str(self.binary), *options],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=10)
            self.assertNotEqual(result.returncode, 0, options)

    def test_second_sweep_budget_and_calibration(self):
        result = subprocess.run(['sh', str(HERE / 'sweep.sh'), 'second-plan'],
                                check=True, text=True, stdout=subprocess.PIPE)
        cases = result.stdout.splitlines()
        self.assertEqual(len(cases), 58)
        self.assertLess(len(cases) * 90 + 120, 90 * 60)
        configs = []
        for i, case in enumerate(cases, 1):
            words = shlex.split(case)
            self.assertEqual(words[:2], ['CASE', str(i)])
            configs.append(dict(zip(words[2::2], words[3::2])))
        self.assertEqual([c['--workload'] for c in configs[:3]], ['triad'] * 3)
        for i in range(0, 18, 3):
            self.assertEqual([(c['--mib'], c['--passes']) for c in configs[i:i+3]],
                             [('256', '8'), ('2048', '8'), ('2048', '32')])
        for c in configs[18:]:
            self.assertEqual((c['--mib'], c['--passes']), ('2048', '32'))
            self.assertNotEqual(c['--workload'], 'all')


if __name__ == '__main__':
    if os.name == 'nt':
        tc = PROJECT / '.work/_shared/toolchain'
        env = os.environ.copy()
        env['PATH'] = str(tc / 'cygwin/bin') + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output([str(tc / 'cygwin/bin/cygpath.exe'),
                                          '-u', str(Path(__file__))], text=True).strip()
        sys.exit(subprocess.call([str(tc / 'cygwin/bin/python3.12.exe'), script], env=env))
    unittest.main()
