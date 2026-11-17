"""S14-56 host-only build and corruption contract for the new scored units.

Proposed interface for red review: corpus.host_check_m5(stage) builds the
frozen units on x86-64 and returns {unit: (reference_text, actual_text)}.
corpus.check_m5_output(unit, reference_text, actual_text) checks complete
outputs, including WRF field differences with the frozen THM-ULP bounds.
The host helper stores Q3/Q5 builds, references and diagnostics sealed.
Missing build dependencies must fail, never skip or fabricate a reference.

The Q fixtures below exercise the existing real host build path immediately
and expose corpus.output_result accepting corrupted output with a pass marker.
The new collector must consume job['reference'] and validate the payload.
"""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import corpus
import genset

UNITS = {'Q1/Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'MilkyWay-Nbody', 'WRF'}
CLOCK = ('CORPUS_META {"threads":1}\nCORPUS_TIME 1\n'
         'CORPUS_CLOCK {"clock":"CLOCK_MONOTONIC_RAW","boundary":"launch-to-exit",'
         '"start_ns":1,"end_ns":1000000001,"utc_start_ns":2}\n')


class M5HostChecks(unittest.TestCase):
    def test_real_q_outputs_reach_corpus_checker(self):
        # Keep all artifacts private, including the two newly held-out units.
        stage = corpus.sealed_dir(corpus.SHARED / 'S14-56') / 'q-host'
        with patch.object(genset, 'STAGE', stage):
            checked = genset.host_check()
        grouped = {'Q1/Q2': ('\n'.join(checked[q][0] for q in ('Q1', 'Q2')),
                             '\n'.join(checked[q][1] for q in ('Q1', 'Q2')))}
        grouped.update({q: checked[q] for q in ('Q3', 'Q4', 'Q5', 'Q6')})
        for unit, (reference, actual) in grouped.items():
            with self.subTest(unit=unit):
                job = dict(program=unit, threads=1, reference=reference)
                clean = CLOCK + actual + '\nCORPUS_CHECK pass\n'
                self.assertEqual(corpus.output_result(job, clean, '', 0)['check'], 'pass')
                tokens = actual.split()
                tokens[-1] = '999999999'
                corrupt = CLOCK + ' '.join(tokens) + '\nCORPUS_CHECK pass\n'
                self.assertEqual(corpus.output_result(job, corrupt, '', 0)['check'], 'fail',
                                 'a pass marker must not override corrupted workload output')

    def test_all_new_units_build_and_reject_corrupted_host_output(self):
        host_check = getattr(corpus, 'host_check_m5', None)
        checker = getattr(corpus, 'check_m5_output', None)
        self.assertTrue(callable(host_check), 'missing M5 host build/reference integration')
        self.assertTrue(callable(checker), 'missing M5 complete-output checker')
        checked = host_check(corpus.SHARED / 'S14-56')
        self.assertEqual(set(checked), UNITS)
        for unit, (reference, actual) in checked.items():
            with self.subTest(unit=unit):
                self.assertTrue(reference.strip())
                self.assertTrue(actual.strip())
                self.assertTrue(checker(unit, reference, actual))
                self.assertFalse(checker(unit, reference, ''))
                self.assertFalse(checker(unit, reference, actual + '\nCORRUPTED\n'))
                tokens = actual.split()
                tokens[-1] = '999999999'
                self.assertFalse(checker(unit, reference, ' '.join(tokens)))


if __name__ == '__main__':
    unittest.main()
