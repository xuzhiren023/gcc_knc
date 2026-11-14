"""Host acceptance for S11-16's actual C probe driver (run under Cygwin)."""
from pathlib import Path
import subprocess
import unittest


class ProbeDriver(unittest.TestCase):
    def test_enumeration_isolation_and_format(self):
        root = Path(__file__).resolve().parents[2]
        out = root.parent / '_shared/S11-16'
        out.mkdir(exist_ok=True)
        binary = out / 'long-double-host.exe'
        subprocess.run(['gcc', '-O2', '-std=gnu11', '-Wall', '-Wextra',
                        '-Werror', '-DPROBE_HOST_TEST',
                        str(root / 'tools/s11_16_long_double.c'), '-pthread',
                        '-ldl', '-o', str(binary)], check=True)
        enumeration = subprocess.check_output([str(binary), '--enumerate'], text=True)
        rows = [line.split() for line in enumeration.splitlines()]
        self.assertEqual(len(rows), 32829 * 8)
        expected = {(e, s, m) for e in range(-16445, 16384)
                    for s in range(2) for m in range(4)}
        actual = set()
        for tag, exponent, sign, mantissa, value in rows:
            self.assertEqual(tag, 'INPUT')
            key = (int(exponent), int(sign), int(mantissa))
            actual.add(key)
            # The emitted representation is the exact 80-bit input, not a
            # double conversion that would lose most of the exponent range.
            self.assertRegex(value, r'^[0-9a-f]{4}:[0-9a-f]{16}$')
            se, significand = (int(part, 16) for part in value.split(':'))
            self.assertEqual(se >> 15, key[1])
            self.assertNotEqual(significand, 0)
            e, _, m = key
            bits = (0x8000000000000000, 0xa000000000000000,
                    0xc000000000000000, 0xffffffffffffffff)[m]
            self.assertEqual(se & 0x7fff, max(0, e + 16383))
            self.assertEqual(significand, bits >> max(0, -16382 - e))
        self.assertEqual(actual, expected)
        run = subprocess.run([str(binary), '--selftest'], text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(run.returncode, 1, run.stderr)
        results = [line.split() for line in run.stdout.splitlines()
                   if line.startswith('RESULT ')]
        self.assertEqual([(r[1], r[2]) for r in results],
                         [('healthy_before', 'OK'), ('injected_segv', 'FAULT'),
                          ('healthy_after', 'OK')])
        self.assertRegex(run.stdout, r'FAULT injected_segv signal=11 input=[0-9a-f]{4}:[0-9a-f]{16}')
        for row in (results[0], results[2]):
            self.assertEqual(row[3], 'calls=262632')
        self.assertIn('SUMMARY functions=3 faults=1 errors=0', run.stdout)


if __name__ == '__main__':
    unittest.main()
