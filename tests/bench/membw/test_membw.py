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

    def test_gemv_formats_shapes_and_accounting(self):
        # Each run checks every row against the benchmark's scalar reference.
        # Uneven partitions and partial row groups exercise the cleanup paths.
        for fmt, width in [('fp32', 4), ('int8', 1), ('fp16', 2)]:
            for columns, streams, block, unroll in [(4096, 1, 0, 1),
                                                    (11008, 8, 256, 8)]:
                with self.subTest(format=fmt, columns=columns):
                    result = subprocess.run(
                        [str(self.binary), '--workload', 'gemv', '--format', fmt,
                         '--columns', str(columns), '--row-streams', str(streams),
                         '--column-block', str(block), '--unroll', str(unroll),
                         '--mib', '1', '--passes', '2', '--repeats', '5',
                         '--threads', '1', '--pf0', '8', '--pf1', '64'],
                        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        timeout=45)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    records = [json.loads(s) for s in result.stdout.splitlines()]
                    row, = [r for r in records if r['kind'] == 'result']
                    self.assertEqual(row['workload'], 'gemv')
                    self.assertEqual(row['format'], fmt)
                    self.assertTrue(row['valid'])
                    self.assertEqual(row['columns'], columns)
                    self.assertEqual(row['samples'], 5)
                    matrix_bytes = row['rows'] * columns * width
                    self.assertGreaterEqual(matrix_bytes, 1024 * 1024)
                    self.assertLess(matrix_bytes, 1024 * 1024 + columns * width)
                    self.assertEqual(row['logical_bytes'], matrix_bytes * 2)
                    self.assertEqual(row['scale_bytes'], row['rows'] * 4
                                     if fmt == 'int8' else 0)
                    rates = sorted(row['logical_bytes'] / t['seconds'] / 1e9
                                   for t in row['timings'])
                    self.assertAlmostEqual(row['median_GBs'], rates[2], places=5)
                    self.assertAlmostEqual(row['median_GFLOPs'], rates[2] * 2 / width,
                                           places=5)

    def test_gemv_sweep_contract(self):
        result = subprocess.run(['sh', str(HERE / 'sweep.sh'), 'gemv-plan'],
                                text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr)
        configs = []
        for i, line in enumerate(result.stdout.splitlines(), 1):
            words = shlex.split(line)
            self.assertEqual(words[:2], ['CASE', str(i)])
            c = dict(zip(words[2::2], words[3::2]))
            self.assertEqual((c['--mib'], c['--passes'], c['--repeats']),
                             ('2048', '32', '5'))
            self.assertEqual(c['--placement'], 'spread')
            configs.append(c)
        self.assertGreater(len(configs), 0)
        self.assertLess(len(configs) * 90 + 120, 90 * 60)
        self.assertEqual(configs[0]['--workload'], 'read')
        for fmt in ['fp32', 'int8', 'fp16']:
            group = [c for c in configs if c['--workload'] == 'gemv'
                     and c['--format'] == fmt]
            self.assertEqual({c['--threads'] for c in group}, {'60', '120', '180', '240'})
            self.assertEqual({c['--columns'] for c in group}, {'4096', '11008'})
            for key in ['--row-streams', '--column-block', '--pages', '--unroll']:
                self.assertGreater(len({c[key] for c in group}), 1, (fmt, key))
            self.assertTrue(any(c['--pf0'] == '0' for c in group))
            self.assertTrue(any(c['--pf1'] == '0' for c in group))
            # Every memory/prefetch setting has an earlier plain-read control.
            keys = ['--threads', '--pf0', '--pf1', '--pages', '--unroll']
            for c in group:
                earlier = configs[:configs.index(c)]
                self.assertTrue(any(r['--workload'] == 'read' and
                                    all(r[k] == c[k] for k in keys) for r in earlier))

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

    def test_third_sweep_budget_and_controls(self):
        result = subprocess.run(['sh', str(HERE / 'sweep.sh'), 'third-plan'],
                                check=True, text=True, stdout=subprocess.PIPE)
        cases = result.stdout.splitlines()
        self.assertEqual(len(cases), 58)
        self.assertLess(len(cases) * 90 + 120, 90 * 60)
        configs = []
        for i, case in enumerate(cases, 1):
            words = shlex.split(case)
            self.assertEqual(words[:2], ['CASE', str(i)])
            c = dict(zip(words[2::2], words[3::2]))
            configs.append(c)
            self.assertEqual((c['--mib'], c['--passes'], c['--repeats']),
                             ('2048', '32', '5'))
            self.assertEqual(c['--placement'], 'spread')
            self.assertNotEqual(c['--workload'], 'all')
        self.assertEqual([c['--workload'] for c in configs[:6]],
                         ['triad', 'read', 'write', 'copy', 'rmw', 'stencil'])
        self.assertEqual(configs[:6], configs[-6:])
        self.assertEqual((configs[0]['--threads'], configs[0]['--pf0'],
                          configs[0]['--pf1']), ('60', '8', '64'))
        for start, workload in zip(range(6, 26, 4),
                                   ['read', 'copy', 'triad', 'rmw', 'stencil']):
            group = configs[start:start+4]
            self.assertEqual([c['--workload'] for c in group], [workload] * 4)
            self.assertEqual([(c['--threads'], c['--pf0'], c['--pf1']) for c in group],
                             [('60', '16', '128'), ('60', '32', '256'),
                              ('120', '16', '128'), ('120', '32', '256')])
        reference = configs[26]
        self.assertEqual(reference, configs[51])
        self.assertEqual(reference['--threads'], '120')
        for c, keys in zip(configs[27:38],
                           [{'--prefetch'}, {'--pf0', '--pf1'}, {'--pf0', '--pf1'},
                            {'--pages'}, {'--schedule'}, {'--chunk-lines'},
                            {'--evict'}, {'--prefetch'}, {'--store'}, {'--store'},
                            {'--offset-lines'}]):
            changed = {k for k in reference.keys() | c.keys()
                       if reference.get(k) != c.get(k)}
            self.assertEqual(changed, keys)
        self.assertEqual([c['--evict'] for c in configs[46:51]],
                         ['none', 'l2', 'none', 'l2', 'both'])


if __name__ == '__main__':
    if os.name == 'nt':
        tc = PROJECT / '.work/_shared/toolchain'
        env = os.environ.copy()
        env['PATH'] = str(tc / 'cygwin/bin') + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output([str(tc / 'cygwin/bin/cygpath.exe'),
                                          '-u', str(Path(__file__))], text=True).strip()
        sys.exit(subprocess.call([str(tc / 'cygwin/bin/python3.12.exe'), script], env=env))
    unittest.main()
