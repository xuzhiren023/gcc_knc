"""S14-56 red contract: seven new votes, fixed inputs and sealed held-outs.

Q1/Q2 is one program identity. WRF's dm+sm exception is the ticket's owner
decision; all other additions use serial -O2. No card jobs are started here.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import corpus


UNITS = {'Q1/Q2': 'C', 'Q3': 'N', 'Q4': 'H', 'Q5': 'N', 'Q6': 'G',
         'MilkyWay-Nbody': 'S', 'WRF': 'S'}
M4 = {'PB-gemm', 'PB-atax', 'PB-cholesky', 'PB-ludcmp', 'PB-jacobi-2d',
      'PB-heat-3d', 'PB-adi', 'PB-durbin', 'STREAM', 'NPB-CG', 'NPB-EP',
      'NPB-MG', 'NPB-IS', 'HPCG', 'zlib', 'SQLite', 'bzip2'}


class M5Pins(unittest.TestCase):
    """Proposed manifest API: M5_SOURCES[unit], also embedded in plan rows.

    Each source has source_url and a release/edition or commit pin. WRF inputs
    retain the original source paths and the authorized conversion command.
    S14-56 lead correction 2026-11-17: no content digests.
    """

    def sources(self):
        sources = getattr(corpus, 'M5_SOURCES', None)
        self.assertIsInstance(sources, dict, 'missing pinned M5 source manifest')
        return sources

    def test_every_new_unit_records_source_and_release_or_commit(self):
        sources = self.sources()
        for unit in UNITS:
            with self.subTest(unit=unit):
                self.assertIn(unit, sources)
                pin = sources[unit]
                self.assertRegex(pin['source_url'], r'\Ahttps?://\S+\Z')
                self.assertIsInstance(pin['version'], str)
                self.assertTrue(pin['version'].strip())
                self.assertTrue(pin.get('tag') or pin.get('commit') or pin.get('edition'))
                self.assertNotIn('hash', pin)
        for row in corpus.make_plan(core_count=60):
            if row['program'] in UNITS:
                self.assertEqual(row['source'], sources[row['program']])

    def test_milkyway_exact_release_and_correctness_only_patches(self):
        pin = self.sources()['MilkyWay-Nbody']
        self.assertEqual(pin['source_url'],
                         'https://github.com/Milkyway-at-home/milkywayathome_client')
        self.assertEqual(pin['version'], 'nbody_1.96')
        self.assertEqual(pin['commit'], '1e640779f1cabf88aaa49e4db569cfe7e09016c4')
        patches = pin['patches']
        expected = {'crlibm-config-path.patch', 'nbody-king-const.patch',
                    'nbody-result-contract.patch'}
        self.assertEqual(set(patches), expected)
        self.assertEqual(len(patches), len(expected))
        self.assertEqual(pin['host_patches'], ['popt-cygwin.patch'])

    def test_wrf_input_sources_and_conversion_are_frozen(self):
        pin = self.sources()['WRF']
        base = 'C:/Users/xuzhi/Documents/PhiWeather/artifacts/test-state/'
        case = base + 'accuracy-downloads-20261112/cases/miami-20240106/hn12rlh/inputs/'
        expected = {name: case + name for name in
                    ('wrfinput_d01', 'wrfinput_d02', 'wrfbdy_d01')}
        expected['namelist.input'] = (base + 'claude-mentor-performance-20261105/'
                                     'bt-20240106-MIA-HN12RLH-S1126-04/namelist.input')
        for name, source in expected.items():
            with self.subTest(input=name):
                record = pin['inputs'][name]
                self.assertEqual(record['source'].replace('\\', '/'), source)
                self.assertNotIn('hash', record)
                if name != 'namelist.input':
                    self.assertEqual(record['conversion'],
                                     'nccopy -k 64-bit-offset <in> <out>')


class M5Manifest(unittest.TestCase):
    def test_seven_additions_preserve_m4_and_q1_q2_have_one_vote(self):
        self.assertEqual(set(corpus.PROGRAMS), M4 | set(UNITS))
        self.assertEqual(len(corpus.PROGRAMS), 24)

    def test_primary_rows_freeze_style_input_flags_and_build_mode(self):
        plan = corpus.make_plan(core_count=60)
        for unit, style in UNITS.items():
            with self.subTest(unit=unit):
                rows = [r for r in plan if r['program'] == unit
                        and r['panel'] == 'primary' and r['profile'] == 'full']
                self.assertEqual(len(rows), 6, 'three donor/KNC pairs per vote')
                self.assertEqual({r['style'] for r in rows}, {style})
                self.assertEqual({r['held_out'] for r in rows}, {unit in ('Q3', 'Q5')})
                self.assertEqual({r['input'] for r in rows}, {corpus.INPUTS[unit]})
                self.assertTrue(corpus.INPUTS[unit])
                self.assertEqual(len({r['pair_id'] for r in rows}), 3)
                for row in rows:
                    self.assertEqual(row['flags'], ['-O2'] + (
                        ['-march=knc'] if row['compiler'] == corpus.KNC else []))
                    self.assertEqual(row['variant'], 'dm+sm' if unit == 'WRF' else 'serial')
                    if unit != 'WRF':
                        self.assertEqual(row['threads'], 1)

    def test_q3_q5_details_are_written_only_to_sealed_partition(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary) / 'public'
            sealed = Path(temporary) / 'sealed'
            stage.mkdir()
            sealed.mkdir()
            rows = [dict(program=p, check='pass', diagnostic='private detail') for p in UNITS]
            with patch.object(corpus, 'sealed_dir', return_value=sealed):
                corpus.write_partition(stage, 'builds.json', rows)
            public = json.loads((stage / 'builds.json').read_text())
            private = json.loads((sealed / 'builds.json').read_text())
            self.assertEqual({r['program'] for r in public}, set(UNITS) - {'Q3', 'Q5'})
            self.assertEqual({r['program'] for r in private}, {'Q3', 'Q5'})


if __name__ == '__main__':
    unittest.main()
