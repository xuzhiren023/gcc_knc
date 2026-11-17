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
