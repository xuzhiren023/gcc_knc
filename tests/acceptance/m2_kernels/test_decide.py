"""Host-only recorded-output cases for ADR-0010 amendment 2."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


class Decisions(unittest.TestCase):
    def run_block(self, gains, ratios=None, invalid=False, regression=False, one_state=False):
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for i, gain in enumerate(gains, 1):
                text = (HERE / ('sample-invalid.txt' if invalid and i == 1
                                else 'sample-pass.txt')).read_text()
                text = text.replace('launch=1 ', 'launch=%d ' % i)
                text = text.replace('gain_fraction=0.8', 'gain_fraction=%s' % gain)
                if one_state:
                    text = text.replace('regime_step=1', 'regime_step=0')
                if ratios:
                    text = text.replace('gcc_over_gcc_before=0.95',
                                        'gcc_over_gcc_before=%s' % ratios[i-1])
                if regression and i == 1:
                    text = text.replace('gcc_over_x87_max=0.2', 'gcc_over_x87_max=1.06')
                path = Path(tmp) / ('launch%d.out' % i)
                path.write_text(text)
                paths.append(str(path))
            proc = subprocess.run([sys.executable, str(HERE / 'decide.py'),
                                   '--min-effect', '0.02', *paths],
                                  text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            return json.loads(proc.stdout)

    def test_pass(self):
        # Reduced receipt from tmp/claude-s6-m2-test/l2-1.out: card_run's sleep.
        report = self.run_block([0.8]*5)
        self.assertEqual(report['m2']['decision'], 'pass')
        self.assertEqual(report['m2']['regime_steps'], 5)
        self.assertEqual(report['m2']['median_gain_ci95'], [0.8, 0.8])
        self.assertEqual(report['tuning'][0]['decision'], 'accept')

    def test_clause_a(self):
        report = self.run_block([0.49]*5)['m2']
        self.assertFalse(report['a'])
        self.assertEqual(report['decision'], 'fail')

    def test_one_state_is_note(self):
        report = self.run_block([0.8]*3, one_state=True)['tuning'][0]
        self.assertEqual(report['decision'], 'accept')
        self.assertEqual(report['reasons'], [])
        self.assertIn('two performance states not established', report['notes'][0])

    def test_clause_b_sequential(self):
        report = self.run_block([0.50, 0.50, 0.50, 0.50, 0.70])['m2']
        self.assertTrue(report['a'])
        self.assertFalse(report['b'])
        self.assertEqual(report['decision'], 'run-five-more')
        report = self.run_block([0.50, 0.50, 0.50, 0.50, 0.70]*2)['m2']
        self.assertEqual(report['decision'], 'fail')
        self.assertEqual(report['sequential_step'], 2)

    def test_sign_flip(self):
        report = self.run_block([0.8]*5, [0.95, 0.95, 1.05, 0.95, 0.95])
        self.assertEqual(report['tuning'][0]['decision'], 'placement-dependent')

    def test_invalid(self):
        report = self.run_block([0.8]*5, invalid=True)
        self.assertEqual(report['m2']['decision'], 'invalid-block')
        self.assertIn('density 3', report['invalid'][0]['reasons'])
        self.assertIn('launch1.out', report['invalid'][0]['file'])

    def test_clause_c(self):
        report = self.run_block([0.8]*5, regression=True)['m2']
        self.assertFalse(report['c'])
        self.assertEqual(report['decision'], 'fail')


if __name__ == '__main__':
    unittest.main()
