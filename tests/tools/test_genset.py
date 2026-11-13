"""S12-02: real host drivers, frozen checks, and corrupted-output controls."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import genset


class GeneralityChecks(unittest.TestCase):
    def test_drivers_and_controls(self):
        checked = genset.host_check()
        self.assertEqual(set(checked), set(genset.PROGRAMS))
        for program, (reference, actual) in checked.items():
            with self.subTest(program=program):
                self.assertTrue(genset.matches(program, reference, actual))
                self.assertFalse(genset.matches(program, reference, actual + '\nCORRUPTED\n'))
                self.assertFalse(genset.matches(program, reference, ''))
                tokens = actual.split()
                tokens[-1] = '999999999'
                self.assertFalse(genset.matches(program, reference, ' '.join(tokens)))
        plan = genset.make_plan()
        self.assertEqual(len(plan), 108)
        for a, b in zip(plan[::2], plan[1::2]):
            self.assertEqual(a['pair_id'], b['pair_id'])
            self.assertEqual(a['threads'], 1)
            self.assertNotEqual(a['compiler'], b['compiler'])
        self.assertEqual({r['profile'] for r in plan}, {'full', '3100', '5100'})


if __name__ == '__main__':
    unittest.main()
