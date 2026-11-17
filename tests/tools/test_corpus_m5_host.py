"""S14-56 host-only build and corruption contract for the new scored units.

Proposed interface for red review: corpus.host_check_m5(stage, programs=...)
builds selected frozen units on x86-64 and returns
{unit: (reference_text, actual_text)}. The default test excludes WRF; explicitly
set KNC_M5_SLOW_WRF=1 to exercise the full WRF host build. The real WRF
comparison remains against GCC 5.1.1 on the card, run by the lead.
corpus.check_m5_output(unit, reference_text, actual_text) checks complete
outputs, including WRF field differences with the frozen THM-ULP bounds.
The host helper stores Q3/Q5 builds, references and diagnostics sealed.
Missing build dependencies must fail, never skip or fabricate a reference.

The Q fixtures below exercise the existing real host build path immediately
and expose corpus.output_result accepting corrupted output with a pass marker.
The new collector must consume job['reference'] and validate the payload.
"""
import copy
import json
import math
import os
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


class M5FPContracts(unittest.TestCase):
    """Synthetic normalized outputs; no application build or native execution.

    Proposed checker text format: JSON with a likelihood for MilkyWay; WRF
    has completion and fields keyed by domain/field, containing values.
    Only the frozen reference carries rms_bound, derived from the donor
    THM-1-ULP run. These toy bounds are exact powers of two, not case data.
    """

    def checker(self):
        checker = getattr(corpus, 'check_m5_output', None)
        self.assertTrue(callable(checker), 'missing M5 complete-output checker')
        return checker

    def test_milkyway_rejects_one_ulp_likelihood_change(self):
        checker = self.checker()
        likelihood = -123.25
        reference = json.dumps({'likelihood': likelihood})
        self.assertTrue(checker('MilkyWay-Nbody', reference, reference))
        for direction in (-math.inf, math.inf):
            with self.subTest(direction=direction):
                changed = math.nextafter(likelihood, direction)
                self.assertNotEqual(changed, likelihood)
                self.assertFalse(checker('MilkyWay-Nbody', reference,
                                        json.dumps({'likelihood': changed})))

    def wrf_fixture(self):
        fields = ('T', 'QVAPOR', 'U', 'V', 'W', 'PH', 'MU', 'PSFC',
                  'T2', 'Q2', 'U10', 'V10', 'RAINNC')
        reference = dict(completion='SUCCESS COMPLETE WRF', fields={
            domain + '/' + field: dict(values=[0.0, 0.0], rms_bound=2.0 ** -20)
            for domain in ('d01', 'd02') for field in fields})
        actual = copy.deepcopy(reference)
        for field in actual['fields'].values():
            del field['rms_bound']
        return reference, actual

    def test_wrf_accepts_below_and_rejects_above_each_frozen_rms_bound(self):
        checker = self.checker()
        reference, actual = self.wrf_fixture()
        encoded = json.dumps(reference)
        self.assertTrue(checker('WRF', encoded, json.dumps(actual)))
        for name, field in reference['fields'].items():
            for direction, accepted in ((0.0, True), (math.inf, False)):
                with self.subTest(field=name, direction=direction):
                    changed = copy.deepcopy(actual)
                    delta = math.nextafter(field['rms_bound'], direction)
                    # Equal magnitudes make RMS exactly abs(delta), so these
                    # straddle the threshold without cancellation or dilution.
                    changed['fields'][name]['values'] = [delta, -delta]
                    self.assertEqual(checker('WRF', encoded, json.dumps(changed)), accepted)

    def test_wrf_rejects_nan_in_every_field(self):
        checker = self.checker()
        reference, actual = self.wrf_fixture()
        for name in actual['fields']:
            with self.subTest(field=name):
                changed = copy.deepcopy(actual)
                changed['fields'][name]['values'][0] = math.nan
                self.assertFalse(checker('WRF', json.dumps(reference), json.dumps(changed)))

    def test_wrf_rejects_missing_success_marker(self):
        checker = self.checker()
        reference, actual = self.wrf_fixture()
        del actual['completion']
        self.assertFalse(checker('WRF', json.dumps(reference), json.dumps(actual)))


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

    def check_host_units(self, programs):
        host_check = getattr(corpus, 'host_check_m5', None)
        checker = getattr(corpus, 'check_m5_output', None)
        self.assertTrue(callable(host_check), 'missing M5 host build/reference integration')
        self.assertTrue(callable(checker), 'missing M5 complete-output checker')
        checked = host_check(corpus.SHARED / 'S14-56', programs=sorted(programs))
        self.assertEqual(set(checked), programs)
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

    def test_new_units_except_wrf_build_and_reject_corrupted_host_output(self):
        self.check_host_units(UNITS - {'WRF'})

    @unittest.skipUnless(os.environ.get('KNC_M5_SLOW_WRF') == '1',
                         'slow WRF host build: explicitly set KNC_M5_SLOW_WRF=1')
    def test_slow_wrf_build_and_reject_corrupted_host_output(self):
        self.check_host_units({'WRF'})


if __name__ == '__main__':
    unittest.main()
