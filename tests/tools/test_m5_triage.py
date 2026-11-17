"""S14-04 host contract: extend captured development triage, never card timing."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import m5_triage as m5


class M5TriageTest(unittest.TestCase):
    def test_existing_development_capture_keeps_unknowns_and_mapping(self):
        root = Path(__file__).resolve().parents[2]
        shared = root.parent / '_shared'
        capture = json.loads((shared / 'S12-19/debug/serial-zlib/triage.json').read_text())
        original = copy.deepcopy(capture)
        result = m5.extend(capture, {'style': 'B'})
        self.assertEqual(capture, original)
        self.assertEqual(result['total_samples'], capture['total_samples'])
        self.assertEqual(len(result['rows']), len(capture['rows']))
        hot = [r for r in result['rows'] if r['samples']]
        self.assertTrue(hot)
        for row in hot:
            self.assertEqual(set(row['m5']['properties']), set(m5.PROPERTIES))
            self.assertTrue(all(v['status'] == 'unknown'
                                for v in row['m5']['properties'].values()))
            self.assertEqual(set(row['m5']['levels']), set(m5.LEVELS))
            self.assertEqual(set(row['m5']['outcomes']), set(m5.OUTCOMES))
            for level in row['m5']['levels'].values():
                self.assertIsNone(level['lower_bound_seconds'])
                self.assertIsNone(level['gap_seconds'])
        output = shared / 'S14-04'
        output.mkdir(exist_ok=True)
        (output / 'zlib-m5.json').write_text(json.dumps(result, indent=2) + '\n')

    def test_bound_uses_max_and_explicit_elapsed_measurement(self):
        model = dict(work='one fixed batch', configuration='test fixture',
                     assumptions='arithmetic contract only; not native evidence',
                     terms=dict(dependency_path=self.term(2), memory=self.term(3),
                                resources={'issue': self.term(4)}),
                     measurement=dict(seconds=10, source='fixture wall timer'),
                     prediction=dict(seconds=8, source='fixture overlap model'))
        result = m5.bound(model)
        self.assertEqual(result['lower_bound_seconds'], 4)
        self.assertEqual(result['gap_seconds'], 6)
        self.assertEqual(result['bound_utilization'], .4)
        self.assertEqual(result['prediction_ratio'], .8)
        self.assertEqual(result['term_utilization']['resource:issue'], .4)
        self.assertEqual(result['qualification'], 'conditional')
        del model['terms']['memory']
        partial = m5.bound(model)
        self.assertIn('memory', partial['unknown_terms'])
        self.assertEqual(partial['lower_bound_seconds'], 4)
        model['measurement']['seconds'] = 1
        self.assertEqual(m5.bound(model)['diagnosis'], 'audit: measurement below bound')

    @staticmethod
    def term(seconds):
        return dict(seconds=seconds, formula='count / measured capacity',
                    source='fixture machine.key [R]; counted assembly',
                    qualification='conditional')

    def test_missing_evidence_invalid_labels_and_sealed_inputs_fail(self):
        for term in (self.term(-1), self.term(float('nan')), {'seconds': 2}):
            with self.assertRaises(ValueError):
                m5.bound(dict(work='batch', configuration='fixture', assumptions='fixture',
                              terms={'memory': term}))
        capture = dict(program='zlib', rows=[{'id': 'hot'}])
        for annotations in ({'style': 'X'}, {'regions': {'typo': {}}},
                            {'regions': {'hot': {'outcomes': {'fast': []}}}}):
            with self.assertRaises(ValueError):
                m5.extend(capture, annotations)
        with self.assertRaises(ValueError):
            m5.extend(dict(program='PB-adi', rows=[]), {})

    def test_outcomes_levels_and_donor_priority_are_separate(self):
        capture = dict(program='zlib', rows=[{'id': 'hot'}])
        observation = dict(level='one_context', baseline_seconds=2,
                           candidate_seconds=1, source='fixture pair, not native',
                           configuration='fixture', work='same fixed batch')
        result = m5.extend(capture, {'style': 'B', 'regions': {'hot': {
            'properties': {'numerical_contract': {'status': 'reported',
                'value': 'strict', 'source': 'fixture contract'}},
            'outcomes': {'runtime_assisted_gain': [observation]}}}})
        outcomes = result['rows'][0]['m5']['outcomes']
        self.assertEqual(outcomes['runtime_assisted_gain'][0]['speedup'], 2)
        self.assertEqual(outcomes['unmodified_source_compiler_gain'], [])
        rows = m5.donor_priority([
            dict(program='STREAM', speedup=1.5, source='fixture'),
            dict(program='zlib', speedup=.99, source='fixture'),
            dict(program='HPCG', speedup=None, source='missing')])
        self.assertEqual([r['program'] for r in rows], ['zlib', 'STREAM', 'HPCG'])
        self.assertAlmostEqual(rows[0]['margin'], -.01)


if __name__ == '__main__':
    unittest.main()
