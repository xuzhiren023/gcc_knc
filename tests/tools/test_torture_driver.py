"""S2-18 host acceptance; run with the bootstrap Cygwin Python and GCC."""
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import storage

OUT = Path(storage.shared_area(storage.main_root(ROOT))) / 'S2-18-driver'


class TortureDriverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(parents=True, exist_ok=True)
        cls.driver = OUT / 'driver.exe'
        fixture = OUT / 'fixture.exe'
        for source, target in [('tools/claude-torture.c', cls.driver),
                               ('tests/tools/torture_driver_fixture.c', fixture)]:
            subprocess.run(['gcc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                            str(ROOT / source), '-o', str(target)], check=True)
        cls.names = ['sleep-%d' % i for i in range(8)] + ['crash', 'fail', 'timeout', 'ok']
        for name in cls.names:
            path = OUT / ('claude-t-%s.exe' % name)
            path.unlink(missing_ok=True)
            os.link(fixture, path)

    @classmethod
    def tearDownClass(cls):
        for path in OUT.iterdir():
            path.unlink()
        OUT.rmdir()

    def run_batch(self, names, args=(), budget_mb=512):
        listing = OUT / 'list'
        listing.write_text(''.join('claude-t-%s.exe %s\n' % (n, n) for n in names))

        def limit():
            resource.setrlimit(resource.RLIMIT_AS, (budget_mb * 1024 * 1024,) * 2)

        start = time.monotonic()
        result = subprocess.run([str(self.driver), *args, 'list'], cwd=OUT,
                                preexec_fn=limit, capture_output=True, text=True,
                                timeout=15)
        return result, time.monotonic() - start

    def test_eight_sleepers_finish_in_one_sleep_and_list_order(self):
        names = ['sleep-%d' % i for i in range(8)]
        result, elapsed = self.run_batch(names, ['-j', '8'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['PASS ' + n for n in names])
        self.assertLess(elapsed, 3.5, 'eight sleeps were serialized')
        self.assertGreater(elapsed, .6)

    def test_crash_failure_timeout_and_ordered_diagnostics(self):
        result, _ = self.run_batch(['timeout', 'crash', 'fail', 'ok'],
                                   ['-j', '4', '--limit-mb', '64'])
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout.splitlines(),
                         ['TIMEOUT timeout', 'FAIL crash', 'FAIL fail', 'PASS ok'])
        self.assertIn('failure diagnostic', result.stderr)
        details = (OUT / 'claude-torture.details').read_text()
        positions = [details.index('TEST ' + n) for n in ['timeout', 'crash', 'fail', 'ok']]
        self.assertEqual(positions, sorted(positions))

    def test_over_budget_refuses_before_starting(self):
        result, _ = self.run_batch(['fail'], ['-j', '8', '--limit-mb', '65'])
        self.assertEqual(result.returncode, 125)
        self.assertIn('memory', result.stderr.lower())
        self.assertEqual(result.stdout, '')
        self.assertNotIn('failure diagnostic', result.stderr)

    def test_explicit_limit_allows_parallel_jobs_with_unlimited_budget(self):
        listing = OUT / 'list'
        names = ['sleep-0', 'sleep-1', 'sleep-2', 'sleep-3']
        listing.write_text(''.join('claude-t-%s.exe %s\n' % (n, n) for n in names))

        def unlimited():
            resource.setrlimit(resource.RLIMIT_AS,
                               (resource.RLIM_INFINITY, resource.RLIM_INFINITY))

        result = subprocess.run([str(self.driver), '-j', '4', '--limit-mb', '64', 'list'],
                                cwd=OUT, preexec_fn=unlimited, capture_output=True,
                                text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['PASS ' + n for n in names])

    def test_parallel_jobs_without_limit_refuse_unlimited_budget(self):
        listing = OUT / 'list'
        listing.write_text('claude-t-ok.exe ok\n')

        def unlimited():
            resource.setrlimit(resource.RLIMIT_AS,
                               (resource.RLIM_INFINITY, resource.RLIM_INFINITY))

        result = subprocess.run([str(self.driver), '-j', '4', 'list'], cwd=OUT,
                                preexec_fn=unlimited, capture_output=True, text=True,
                                timeout=15)
        self.assertEqual(result.returncode, 125)
        self.assertIn('memory budget', result.stderr)
        self.assertEqual(result.stdout, '')

    def test_default_serial_inherits_existing_limit(self):
        result, _ = self.run_batch(['sleep-0', 'sleep-1'], budget_mb=64)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['PASS sleep-0', 'PASS sleep-1'])


if __name__ == '__main__':
    unittest.main()
