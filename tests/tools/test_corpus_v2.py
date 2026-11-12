"""S11-18 red contract: host fixtures only; no compiler or card execution.

V2 launch identities include profile ('full', '3100', '5100'). Full uses
the probed core count; smaller profiles follow tools/card_run's compute cores.
Full PolyBench outputs use arrays=[{array: name, values: [...]}], with the
existing RTOL/ATOL contract. Build records distinguish variant='serial'
and variant='optimization-fallback' from the failed baseline attempts.
The latter records carry actual flags and a nonempty fallback_reason.
These fields describe proposed v2 interfaces for red review.
"""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import corpus


def observations(program, candidate=(1., 3., 2.)):
    plan, rows = [], []
    for run in range(3):
        for compiler in (corpus.DONOR, corpus.KNC):
            job = dict(program=program, compiler=compiler, flags=['-O2'],
                       profile='full', threads=1, run=run, input='synthetic',
                       held_out=False)  # Never trust this label for sealing.
            plan.append(job)
            row = dict(job, check='pass', time_seconds=7.125)
            if program.startswith('PB-'):
                values = [1., 3., 2.] if compiler == corpus.DONOR else list(candidate)
                row['arrays'] = [dict(array='A', values=values)]
                row['checksum'] = [dict(array='A', count=len(values),
                                        sum=sum(values), abs=sum(map(abs, values)),
                                        squares=sum(x*x for x in values),
                                        weighted=sum((i+1)*x for i, x in enumerate(values)))]
            rows.append(row)
    return plan, rows


def collect_at(stage, plan, rows):
    stage.mkdir(parents=True, exist_ok=True)
    corpus.write_json(stage / 'plan.json', plan)
    (stage / 'raw-results.jsonl').write_text(
        ''.join(json.dumps(row) + '\n' for row in rows))
    corpus.collect(SimpleNamespace(stage=stage))


class CorpusV2(unittest.TestCase):
    def test_profiles_expand_all_programs_and_three_openmp_densities(self):
        plan = corpus.make_plan(core_count=60)
        self.assertEqual({row.get('profile') for row in plan},
                         {'full', '3100', '5100'})
        groups = {}
        for row in plan:
            groups.setdefault((row['profile'], row['program'], row['threads']), []).append(row)
        for profile, cores in (('full', 60), ('3100', 56), ('5100', 59)):
            for program in corpus.PROGRAMS:
                expected = {cores, 2*cores, 4*cores} if program in corpus.OPENMP else {1}
                self.assertEqual({threads for p, name, threads in groups
                                  if p == profile and name == program}, expected)
                for threads in expected:
                    launches = groups[profile, program, threads]
                    self.assertEqual({(r['compiler'], r['run']) for r in launches},
                                     {(c, n) for c in (corpus.DONOR, corpus.KNC)
                                      for n in range(3)})
                    self.assertEqual(len(launches), 6)

    def test_profiles_are_distinct_launch_identities_even_for_serial(self):
        plan, _ = observations('zlib')
        self.assertEqual(len({corpus.identity(dict(plan[0], profile=p))
                              for p in ('full', '3100', '5100')}), 3)

    def test_held_out_outputs_and_diagnostics_are_sealed_by_program(self):
        with tempfile.TemporaryDirectory() as temporary:
            shared = Path(temporary)
            stage = shared / 'S11-18'
            plan, rows = observations('zlib')
            for program in ('PB-adi', 'PB-durbin', 'bzip2'):
                jobs, results = observations(program)
                for row in results:
                    row.update(time_seconds=918273.625, profile='3100',
                               check='fail', cause='SEALED_DIAGNOSTIC_CANARY')
                for job in jobs:
                    job['profile'] = '3100'
                plan.extend(jobs)
                rows.extend(results)
            output = io.StringIO()
            with patch.object(corpus, 'SHARED', shared), redirect_stdout(output), redirect_stderr(output):
                collect_at(stage, plan, rows)
            # Includes raw output, processed output, plans, reports and logs.
            public = output.getvalue() + '\n'.join(
                path.read_text() for path in stage.rglob('*') if path.is_file())
            for secret in ('918273.625', 'SEALED_DIAGNOSTIC_CANARY', '3100'):
                self.assertNotIn(secret, public)
            for program in ('PB-adi', 'PB-durbin', 'bzip2'):
                self.assertIn(program, public)  # Public readiness/pass-fail remains visible.
            sealed = shared / 'm4-sealed'
            private = '\n'.join(path.read_text() for path in sealed.rglob('*') if path.is_file())
            for secret in ('918273.625', 'SEALED_DIAGNOSTIC_CANARY', '3100'):
                self.assertIn(secret, private)

    def test_complete_output_rejects_corruption_that_preserves_old_reductions(self):
        # These distinct arrays have equal count, sum, abs, squares and weighted sum.
        # A control against sum-only comparisons must still fail correctness.
        with tempfile.TemporaryDirectory() as temporary:
            for candidate, passes in (((1., 3., 2.), True),
                                      ((1. + 1e-9, 3., 2.), True),
                                      ((2., 1., 3.), False)):
                with self.subTest(candidate=candidate):
                    plan, rows = observations('PB-gemm', candidate)
                    stage = Path(temporary) / 'S11-18'
                    with redirect_stdout(io.StringIO()):
                        collect_at(stage, plan, rows)
                    result = corpus.parse_results((stage / 'results.jsonl').read_text())
                    candidates = [r for r in result if r['compiler'] == corpus.KNC]
                    self.assertEqual(len(candidates), 3)
                    self.assertTrue(all((r['check'] == 'pass') == passes for r in candidates))

    def test_donor_failures_stay_visible_beside_labelled_serial_and_sqlite_fallbacks(self):
        # Exercise real staging and recipes; only external builds/runtime lookup
        # and extraction are faked. Missing OpenMP and kmov failures are deliberate.
        with tempfile.TemporaryDirectory() as temporary:
            shared = Path(temporary)
            stage = shared / 'S11-18'
            stage.mkdir()
            corpus.write_json(stage / 'settings.json', dict(extra_flags={}, repetitions=3))
            corpus.write_json(stage / 'builds.json', [])
            attempts = []

            def fake_execute(command, cwd, log):
                command = list(map(str, command))
                if '-o' not in command:
                    return
                binary = Path(command[command.index('-o') + 1])
                if binary.name != 'workload':
                    binary.write_bytes(b'fixture')
                    return
                donor = 'cross' in Path(command[0]).parts
                program = Path(cwd).name
                attempts.append((program, donor, command))
                reason = None
                if '-fopenmp' in command and (donor or program == 'HPCG'):
                    reason = 'error: missing OpenMP runtime' if donor else 'error: default(none)'
                if donor and program == 'SQLite' and any(f in command for f in ('-O2', '-O3')):
                    reason = 'error: kmov operand size mismatch'
                if reason:
                    log.write(reason + '\n')
                    raise RuntimeError(reason)
                binary.write_bytes(b'fixture; never executed')

            args = SimpleNamespace(stage=stage, only=list(corpus.OPENMP) + ['SQLite'],
                                   extra_flags={}, repetitions=3)
            with patch.object(corpus, 'SHARED', shared), \
                 patch.object(corpus, 'os', SimpleNamespace(name='posix')), \
                 patch.object(corpus, 'extract_packages'), \
                 patch.object(corpus, 'execute', side_effect=fake_execute), \
                 patch.object(corpus, 'stage_runtimes', return_value=[]), \
                 patch.object(corpus, 'write_lead_script'), redirect_stdout(io.StringIO()):
                corpus.stage(args)
            records = json.loads((stage / 'builds.json').read_text())
            for program in corpus.OPENMP:
                with self.subTest(program=program):
                    relevant = [r for r in records if r['program'] == program]
                    self.assertTrue(any(r['compiler'] == corpus.DONOR and r['check'] == 'error'
                                        and r.get('cause') for r in relevant))
                    serial = [r for r in relevant if r.get('variant') == 'serial']
                    self.assertEqual({r['compiler'] for r in serial}, {corpus.DONOR, corpus.KNC})
                    self.assertTrue(all(r['check'] == 'pass' and r.get('fallback_reason') for r in serial))
                    for donor in (True, False):
                        self.assertTrue(any(p == program and d == donor and '-fopenmp' not in cmd
                                            for p, d, cmd in attempts))
            sqlite = [r for r in records if r['program'] == 'SQLite' and r['compiler'] == corpus.DONOR]
            self.assertTrue(any(r['check'] == 'error' and '-O2' in r['flags'] for r in sqlite))
            fallback = [r for r in sqlite if r.get('variant') == 'optimization-fallback']
            self.assertEqual(len(fallback), 1)
            self.assertEqual(fallback[0]['check'], 'pass')
            self.assertIn('-O1', fallback[0]['flags'])
            self.assertNotIn('-O2', fallback[0]['flags'])
            self.assertTrue(fallback[0].get('fallback_reason'))


if __name__ == '__main__':
    unittest.main()
