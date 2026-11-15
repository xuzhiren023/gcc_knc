"""Phase-one staging contract: diagnostic flags, development inputs, paired runs.

No compiler or card invocation. S12-21 must first build the complete development
panel, then use measured code differences to choose the four native A/B cases.
These tests deliberately do not assert a performance gain or an IMUL latency.
"""
import importlib.util
from collections import Counter
from pathlib import Path
import tempfile
import unittest


DEVELOPMENT = {
    'PB-gemm', 'PB-atax', 'PB-cholesky', 'PB-ludcmp', 'PB-jacobi-2d',
    'PB-heat-3d', 'STREAM', 'NPB-CG', 'NPB-EP', 'NPB-MG', 'NPB-IS',
    'HPCG', 'zlib', 'SQLite',
}
FLAGS = {
    'default': ['-O2', '-march=knc'],
    'density1': ['-O2', '-march=knc', '--param=knc-threads-per-core=1'],
}


class PhaseOne(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[2] / 'tools/s12_21_stage.py'
        if not path.is_file():
            raise AssertionError('S12-21 phase-one staging tool is missing: ' + str(path))
        spec = importlib.util.spec_from_file_location('s12_21_stage', path)
        cls.stage = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.stage)

    def test_build_both_densities_for_exactly_fourteen_development_programs(self):
        rows = self.stage.build_plan()
        self.assertEqual(len(rows), 28)
        self.assertEqual(Counter((r['program'], r['label']) for r in rows),
                         Counter((p, label) for p in DEVELOPMENT for label in FLAGS))
        for row in rows:
            with self.subTest(program=row['program'], label=row['label']):
                self.assertEqual(row['compiler'], 'gcc-knc')
                self.assertEqual(row['variant'], 'serial')
                self.assertEqual(row['flags'], FLAGS[row['label']])

    def differences(self):
        # Values stand for changed normalized instruction records, not timings.
        # Nonzero lower-ranked programs must not displace the measured top four.
        differences = {program: 1 for program in DEVELOPMENT}
        differences.update({'PB-gemm': 40, 'NPB-CG': 30, 'zlib': 20, 'SQLite': 10})
        return differences

    def test_four_largest_code_differences_get_three_adjacent_alternating_pairs(self):
        plan = self.stage.card_plan(self.differences())
        rows = plan['pairs']
        selected = {'PB-gemm', 'NPB-CG', 'zlib', 'SQLite'}
        self.assertEqual(len(rows), 24)
        self.assertEqual(Counter((r['program'], r['run'], r['label']) for r in rows),
                         Counter((p, run, label) for p in selected
                                 for run in range(3) for label in FLAGS))
        for first, second in zip(rows[::2], rows[1::2]):
            self.assertEqual(first['program'], second['program'])
            self.assertEqual(first['run'], second['run'])
            order = ['default', 'density1'] if first['run'] % 2 == 0 else ['density1', 'default']
            self.assertEqual([first['label'], second['label']], order)
        for row in rows:
            self.assertEqual(row['profile'], 'full')
            self.assertIs(row['benchmark'], True)
            self.assertEqual(row['variant'], 'serial')
            self.assertEqual(row['flags'], FLAGS[row['label']])
            self.assertGreater(row['timeout'], 0)

        diagnostic = plan['imul']
        self.assertEqual(diagnostic['threads'], 1)
        self.assertEqual(diagnostic['profile'], 'full')
        self.assertIs(diagnostic['benchmark'], True)
        self.assertEqual(set(map(tuple, diagnostic['cases'])),
                         {(bits, form, dependency) for bits in (32, 64)
                          for form in ('register', 'memory')
                          for dependency in ('dependent', 'independent')})
        self.assertEqual(len(diagnostic['cases']), 8)
        self.assertGreater(diagnostic['timeout'], 0)
        self.assertLess(diagnostic['timeout'] + sum(r['timeout'] for r in rows), 1800)

    def test_selection_rejects_incomplete_or_contaminated_development_census(self):
        incomplete = self.differences()
        del incomplete['HPCG']
        foreign = self.differences()
        foreign['unauthorized-program'] = 1000
        for differences in (incomplete, foreign):
            with self.subTest(programs=sorted(differences)), self.assertRaises(ValueError):
                self.stage.card_plan(differences)

    def test_fresh_stage_rejects_existing_outputs_before_building(self):
        self.assertEqual(self.stage.STAGE_SUBDIR, Path('S12-21/r2'))
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / self.stage.STAGE_SUBDIR
            self.stage.prepare_stage(out)
            stale = out / 'default' / 'NPB-MG' / 'stale.s'
            stale.parent.mkdir(parents=True)
            stale.write_text('stale assembly')
            with self.assertRaisesRegex(ValueError, 'stage must be empty'):
                self.stage.prepare_stage(out)
            self.assertEqual(stale.read_text(), 'stale assembly')


if __name__ == '__main__':
    unittest.main()
