"""S11-18 contract: host fixtures and harness C builds; no card execution.

V2 launch identities include profile ('full', '3100', '5100') and variant.
Serial OpenMP-program builds vote in panel='primary'; variant='openmp'
is GCC-KNC-only and its panel states the donor runtime limitation. Full uses
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
import os
from pathlib import Path
import re
import signal
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import corpus


class GateReadiness(unittest.TestCase):
    def test_gate_scorer_requires_all_raw_pairs_and_reports_owner_misses(self):
        import m4_gate as gate
        import m4_score as scorer
        from dataclasses import asdict
        spec = scorer.freeze_primary_spec({level: dict(assembled=True,diagnostic='')
                                           for level in scorer.SQLITE_LEVELS})
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary)
            records = {}
            for profile in ('full','3100','5100'):
                rows = gate.schedule(profile)
                for row in rows:
                    speedup = 1.0 if row['program'] in ('PB-gemm','PB-adi') else 1.5
                    row.update(check='pass',time_seconds=3. if row['compiler']==corpus.DONOR else 3./speedup,
                               primary=json.loads(json.dumps(asdict(spec[row['program']]))),
                               flags=list(spec[row['program']].donor_flags if row['compiler']==corpus.DONOR
                                          else spec[row['program']].new_flags),
                               timing=dict(utc_start_ns=row['launch_order']+1),
                               lead_environment_policy=dict(lead_verified=True,exclusive_window='fixture',
                                                            clock_power_policy='fixed fixture'),
                               environment=dict(start={}))
                records['initial-'+profile+'-checked.jsonl']=rows
            output = io.StringIO()
            with patch.object(gate,'load_freeze',return_value=({},spec)), \
                    patch.object(gate,'check_block',return_value=True), \
                    patch.object(corpus,'read_partition',side_effect=lambda stage,name: records[name]), \
                    patch.object(corpus,'sealed_dir',return_value=stage), \
                    patch.object(scorer,'SEALED_ROOT',stage), redirect_stdout(output):
                gate.score(SimpleNamespace(stage=stage,extended=False))
                report=json.loads((stage/'score.json').read_text())
                self.assertTrue(report['ready'] and report['pass'])
                self.assertTrue(len(report['owner_target_misses'])==6)
                self.assertTrue(all(r['status']==('found; held out, never tuned' if r['program']=='PB-adi'
                                                else 'development defect') for r in report['owner_target_misses']))
                records['initial-5100-checked.jsonl'].pop()
                gate.score(SimpleNamespace(stage=stage,extended=False))
                report=json.loads((stage/'score.json').read_text())
                self.assertTrue(not report['ready'] and not report['passed'])
            self.assertNotIn('speedup',output.getvalue())

    def test_initial_and_extension_have_exact_pairs_and_separate_profiles(self):
        import m4_gate as gate
        for profile in ('full', '3100', '5100'):
            for extended in (False, True):
                plan = gate.schedule(profile, extended)
                self.assertEqual(len(plan), 204)
                self.assertEqual({j['profile'] for j in plan}, {profile})
                self.assertEqual({j['panel'] for j in plan}, {'primary'})
                for offset in range(0, len(plan), 34):
                    round_rows = plan[offset:offset+34]
                    self.assertEqual([r['program'] for r in round_rows[::2]], list(corpus.PROGRAMS))
                    for a,b in zip(round_rows[::2], round_rows[1::2]):
                        expected = ((corpus.DONOR, corpus.KNC) if (a['run']%2 == 0) != extended
                                    else (corpus.KNC, corpus.DONOR))
                        self.assertEqual((a['compiler'],b['compiler']), expected)
                        self.assertEqual((a['start_order'],b['start_order']), (0,1))
                        self.assertEqual(a['pair_id'],b['pair_id'])
                        self.assertEqual(a['threads'],1)

    def test_package_checker_corruption_uses_output_result(self):
        clock = ('CORPUS_META {"threads":1}\nCORPUS_TIME 1\n'
                 'CORPUS_CLOCK {"clock":"CLOCK_MONOTONIC_RAW","boundary":"launch-to-exit",'
                 '"start_ns":1,"end_ns":1000000001,"utc_start_ns":2}\n')
        hpcg = 'HPCG result is VALID\n'
        for section in ('Spectral Convergence Tests','Iteration Count Information','Reproducibility Information'):
            hpcg += section + '::Result=PASSED\n'
        hpcg += 'Departure from Symmetry test::Result=PASSED\n'
        for label in ('Reference CG iterations per set','Optimized CG iterations per set',
                      'Total number of reference iterations','Total number of optimized iterations'):
            hpcg += 'Iteration Count Information::' + label + '=50\n'
        for program, good, corrupt in (('NPB-CG','Verification = SUCCESSFUL\n','VERIFICATION FAILED\n'),
                                       ('HPCG',hpcg,'INVALID\n')):
            self.assertEqual(corpus.output_result(dict(program=program,threads=1),clock+good,'',0)['check'],'pass')
            self.assertEqual(corpus.output_result(dict(program=program,threads=1),clock+good+corrupt,'',0)['check'],'fail')

    def test_stream_run_encoding_covers_every_component(self):
        arrays = [dict(array=k,runs=[[3,v]]) for k,v in corpus.stream_expected().items()]
        self.assertTrue(corpus.stream_matches(arrays,count=3))
        arrays[2]['runs'][0][0] = 2
        self.assertFalse(corpus.stream_matches(arrays,count=3))
        arrays[2]['runs'] = [[2,corpus.stream_expected()['c']],[1,float('inf')]]
        self.assertFalse(corpus.stream_matches(arrays,count=3))

    def test_native_sqlite_corruption_reaches_integer_checker(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            binary = folder / 'workload'
            lib = corpus.SHARED / 'corpus-build/sources/sqlite-amalgamation-3460100'
            subprocess.run(['gcc','-O0','-I'+str(lib),str(lib/'sqlite3.c'),str(corpus.SUPPORT/'sqlite.c'),
                            '-lpthread','-ldl','-lm','-o',str(binary)],check=True,capture_output=True)
            (folder / 'input.sql').write_bytes((corpus.SUPPORT / 'input.sql').read_bytes())
            clean = subprocess.run([str(binary)],cwd=folder,capture_output=True,text=True)
            bad = subprocess.run([str(binary)],cwd=folder,capture_output=True,text=True,
                                 env=dict(os.environ,CORPUS_CORRUPT='1'))
            self.assertEqual(clean.returncode,0)
            self.assertIn('CORPUS_CHECK pass',clean.stdout)
            self.assertEqual(bad.returncode,1)
            self.assertIn('CORPUS_INJECTED SQLite',bad.stdout)
            self.assertNotIn('CORPUS_CHECK pass',bad.stdout)

    def test_native_stream_capture_keeps_full_precision(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            binary = folder / 'workload'
            source = corpus.SHARED / 'corpus-build/sources'
            subprocess.run(['gcc','-O0','-I'+str(source),'-DSTREAM_ARRAY_SIZE=256','-DNTIMES=20',
                            str(corpus.SUPPORT/'stream_capture.c'),'-lm','-o',str(binary)],check=True,capture_output=True)
            result = subprocess.run([str(binary)],cwd=folder,capture_output=True)
            self.assertEqual(result.returncode,0)
            arrays=[]
            with (folder/'arrays.bin').open('rb') as data:
                while name := data.read(80):
                    count,=struct.unpack('=Q',data.read(8))
                    values=struct.unpack('='+'d'*count,data.read(8*count))
                    arrays.append(dict(array=name.rstrip(b'\0').decode(),values=list(values)))
            self.assertTrue(corpus.stream_matches(arrays,count=256))
            arrays[-1]['values'][-1]*=1.01
            self.assertFalse(corpus.stream_matches(arrays,count=256))
    def test_host_references_against_small_package_workloads(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            reference = folder / 'reference'
            subprocess.run(['gcc', '-O0', '-ffp-contract=off', str(corpus.SUPPORT / 'reference.c'),
                            '-lm', '-o', str(reference)], check=True, capture_output=True)
            sources = corpus.SHARED / 'corpus-build/sources/polybench-c-4.2.1-beta'
            for name in corpus.PB:
                # Held-out fixtures deliberately expose only the pass/fail assertion.
                with self.subTest(program=name):
                    benchmark = next(sources.rglob(name + '.c'))
                    binary = folder / 'workload'
                    compile_run = subprocess.run(['gcc', '-O0', '-ffp-contract=off',
                        '-I' + str(sources / 'utilities'), '-DPOLYBENCH_DUMP_ARRAYS', '-DDATA_TYPE_IS_DOUBLE',
                        '-DN=8', '-DM=8', '-DNI=8', '-DNJ=8', '-DNK=8', '-DTSTEPS=3',
                        '-include', str(corpus.SUPPORT / 'polybench_capture.h'),
                        str(benchmark), str(sources / 'utilities/polybench.c'),
                        str(corpus.SUPPORT / 'polybench_capture.c'), '-lm', '-o', str(binary)], capture_output=True)
                    self.assertTrue(compile_run.returncode == 0)
                    result = subprocess.run([str(binary)], cwd=folder, capture_output=True)
                    self.assertTrue(result.returncode == 0)
                    arrays = []
                    with (folder / 'arrays.bin').open('rb') as data:
                        while raw_name := data.read(80):
                            count, = struct.unpack('=Q', data.read(8))
                            values = struct.unpack('=' + 'd' * count, data.read(count * 8))
                            arrays.append(dict(array=raw_name.rstrip(b'\0').decode(), values=list(values)))
                    ref = subprocess.run([str(reference), name, '8', '8', '3'], capture_output=True)
                    self.assertTrue(ref.returncode == 0)
                    expected = json.loads(ref.stdout)
                    self.assertTrue(corpus.reference_matches(arrays, expected))
                    arrays[0]['values'][0] += 1.
                    self.assertFalse(corpus.reference_matches(arrays, expected))
    def test_independent_reference_rejects_agreeing_wrong_compilers(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary) / 'S13-01'
            plan, rows = observations('PB-gemm')
            for row in rows:
                row['arrays'][0]['values'][1] = 99.
            with patch.object(corpus, 'load_reference', return_value=[
                    dict(array='A', values=[1., 3., 2.])]), redirect_stdout(io.StringIO()):
                collect_at(stage, plan, rows)
            result = corpus.parse_results((stage / 'results.jsonl').read_text())
            self.assertTrue(all(r['check'] == 'fail' for r in result))

    def test_frozen_element_tolerance_and_finiteness(self):
        ref = [dict(array='x', values=[0., 10.])]
        self.assertTrue(corpus.reference_matches([dict(array='x', values=[1e-8, 10.00001])], ref))
        for values in ([2e-8, 10.], [0., float('nan')], [0., float('inf')]):
            self.assertFalse(corpus.reference_matches([dict(array='x', values=values)], ref))

    def test_stream_checks_each_component_not_package_marker(self):
        expected = corpus.stream_expected()
        arrays = [dict(array=k, values=[v] * 3) for k, v in expected.items()]
        self.assertTrue(corpus.stream_matches(arrays, count=3))
        arrays[1]['values'][1] *= 1.01
        self.assertFalse(corpus.stream_matches(arrays, count=3))
        self.assertFalse(corpus.stream_matches([], count=3))

OPENMP_PANEL = 'the donor toolchain has no OpenMP runtime'


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
    # Explicit independent synthetic fixture, never a copy of the observations.
    for program in {j['program'] for j in plan if j['program'].startswith('PB-')}:
        base = corpus.sealed_dir(stage) if program in corpus.HELD_OUT else stage
        (base / 'references').mkdir(parents=True, exist_ok=True)
        corpus.write_json(base / 'references' / (program + '.json'),
                          [dict(array='A', values=[1., 3., 2.])])
    corpus.write_json(stage / 'plan.json', plan)
    (stage / 'raw-results.jsonl').write_text(
        ''.join(json.dumps(row) + '\n' for row in rows))
    corpus.collect(SimpleNamespace(stage=stage))


class CorpusV2(unittest.TestCase):
    def test_profiles_expand_all_programs_and_three_openmp_densities(self):
        plan = corpus.make_plan(core_count=60)
        with self.subTest(contract='profile coverage'):
            self.assertEqual({row.get('profile') for row in plan},
                             {'full', '3100', '5100'})
        groups = {}
        for row in plan:
            groups.setdefault((row.get('profile'), row['program']), []).append(row)
        for profile, cores in (('full', 60), ('3100', 56), ('5100', 59)):
            for program in corpus.PROGRAMS:
                with self.subTest(profile=profile, program=program):
                    launches = groups.get((profile, program), [])
                    primary = [r for r in launches if r.get('panel') == 'primary']
                    expected = {(c, n, 1) for c in (corpus.DONOR, corpus.KNC)
                                for n in range(3)}
                    self.assertEqual({(r['compiler'], r['run'], r['threads'])
                                      for r in primary}, expected)
                    self.assertEqual(len(primary), 6)
                    if program in corpus.OPENMP:
                        self.assertTrue(all(r.get('variant') == 'serial' for r in primary))
                        panel = [r for r in launches if r.get('panel') == OPENMP_PANEL]
                        self.assertEqual({(r['compiler'], r['run'], r['threads']) for r in panel},
                                         {(corpus.KNC, n, t) for n in range(3)
                                          for t in (cores, 2*cores, 4*cores)})
                        self.assertEqual(len(panel), 9)
                        self.assertTrue(all(r.get('variant') == 'openmp' for r in panel))
                        self.assertEqual(len(launches), 15)
                    else:
                        self.assertEqual(len(launches), 6)

    def test_gate_pairs_and_raw_clock_record(self):
        plan = corpus.make_plan(repetitions=6, core_count=60)
        self.assertEqual(len(plan), 936)
        primary = [r for r in plan if r['panel'] == 'primary']
        self.assertEqual(plan[:len(primary)], primary)
        for run in range(6):
            block = primary[run * 102:(run + 1) * 102]
            self.assertEqual([r['profile'] for r in block[::34]], ['full', '3100', '5100'])
            for a, b in zip(block[::2], block[1::2]):
                self.assertEqual((a['compiler'], b['compiler']),
                                 (corpus.DONOR, corpus.KNC) if run % 2 == 0 else (corpus.KNC, corpus.DONOR))
                self.assertIsNotNone(a.get('pair_id'))
                self.assertEqual(a.get('pair_id'), b.get('pair_id'))
                self.assertEqual((a.get('start_order'), b.get('start_order')), (0, 1))
        stdout = ('CORPUS_META {"threads":1}\nCORPUS_TIME 2.5\n'
                  'CORPUS_CLOCK {"clock":"CLOCK_MONOTONIC_RAW","boundary":"launch-to-exit",'
                  '"start_ns":1000000000,"end_ns":3500000000,"utc_start_ns":123456789}\n'
                  'Time in seconds = 0.75\nVerification = SUCCESSFUL\n')
        row = corpus.output_result(dict(program='NPB-CG', threads=1), stdout, '', 0)
        self.assertEqual(row['check'], 'pass')
        self.assertEqual(row['time_seconds'], 2.5)
        self.assertEqual(row.get('timing', {}).get('boundary'), 'launch-to-exit')
        self.assertIn('Time in seconds = 0.75', row.get('secondary_timing_output', []))
        old = corpus.output_result(dict(program='NPB-CG', threads=1),
                                   '\n'.join(s for s in stdout.splitlines() if not s.startswith('CORPUS_CLOCK ')), '', 0)
        self.assertNotEqual(old['check'], 'pass', 'legacy partial timing must not be scored')

    def test_profiles_are_distinct_launch_identities_even_for_serial(self):
        plan, _ = observations('zlib')
        with self.subTest(contract='profiles'):
            self.assertEqual(len({corpus.identity(dict(plan[0], profile=p))
                                  for p in ('full', '3100', '5100')}), 3)
        with self.subTest(contract='variants'):
            self.assertNotEqual(corpus.identity(dict(plan[0], variant='serial')),
                                corpus.identity(dict(plan[0], variant='openmp')))

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
                with self.subTest(public_secret=secret):
                    self.assertNotIn(secret, public)
            for program in ('PB-adi', 'PB-durbin', 'bzip2'):
                # Associate the state with each program, not an unrelated failure.
                with self.subTest(public_state=program):
                    self.assertRegex(public, re.escape(program) + r'[^\n]*\bfail\b')
            sealed = shared / 'm4-sealed'
            private = '\n'.join(path.read_text() for path in sealed.rglob('*') if path.is_file())
            for secret in ('918273.625', 'SEALED_DIAGNOSTIC_CANARY', '3100'):
                with self.subTest(sealed_secret=secret):
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
            hpcg_inputs = []
            source = shared / 'corpus-build/sources'
            relative = Path('hpcg-3.1/src/ComputeResidual.cpp')
            # Synthetic source fixture; only the directive models the real failure.
            original = ('// host fixture, never compiled\n'
                        '#pragma omp parallel default(none) shared(local_residual, v1v, v2v)\n'
                        '// n is required by the parallel region\n')
            fixture = {relative.as_posix(): original,
                       'hpcg-3.1/src/untouched.cpp': '// unchanged fixture\n'}

            def fake_extract(destination):
                for name, content in fixture.items():
                    path = destination / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content)

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
                fixed = False
                if program == 'HPCG':
                    residuals = [Path(arg) for arg in command
                                 if Path(arg).name == 'ComputeResidual.cpp']
                    if len(residuals) == 1 and residuals[0].is_file():
                        path = residuals[0]
                        content = path.read_text()
                        directive = re.search(r'default\(none\)\s+shared\(([^)]*)\)', content)
                        fixed = bool(directive and 'n' in directive[1].replace(' ', '').split(','))
                        hpcg_inputs.append((donor, path, content, fixed))
                if '-fopenmp' in command:
                    if donor:
                        reason = 'error: missing OpenMP runtime'
                    elif program == 'HPCG' and not fixed:
                        reason = 'error: n not specified in enclosing parallel default(none)'
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
                 patch.object(corpus, 'extract_packages', side_effect=fake_extract), \
                 patch.object(corpus, 'execute', side_effect=fake_execute), \
                 patch.object(corpus, 'stage_runtimes', return_value=[]), \
                 patch.object(corpus, 'write_lead_script'), redirect_stdout(io.StringIO()):
                corpus.stage(args)
            records = json.loads((stage / 'builds.json').read_text())
            with self.subTest(contract='corpus source remains unchanged'):
                self.assertEqual({p.relative_to(source).as_posix(): p.read_text()
                                  for p in source.rglob('*') if p.is_file()}, fixture)
            with self.subTest(contract='identical staged HPCG source fix'):
                self.assertEqual({donor for donor, _, _, _ in hpcg_inputs}, {True, False})
                self.assertTrue(all(fixed for _, _, _, fixed in hpcg_inputs))
                self.assertEqual(len({content for _, _, content, _ in hpcg_inputs}), 1)
                for _, path, content, _ in hpcg_inputs:
                    self.assertFalse(path.resolve().is_relative_to(source.resolve()))
                    before, after = original.splitlines(), content.splitlines()
                    self.assertEqual(len(before), len(after))
                    self.assertEqual(sum(a != b for a, b in zip(before, after)), 1)
                    shared_names = re.search(r'shared\(([^)]*)\)', content)[1]
                    self.assertEqual({s.strip() for s in shared_names.split(',')},
                                     {'local_residual', 'v1v', 'v2v', 'n'})
                    self.assertEqual(re.sub(r'shared\([^)]*\)', 'shared(...)', content),
                                     re.sub(r'shared\([^)]*\)', 'shared(...)', original))
            with self.subTest(contract='only corpus change recorded'):
                changes = []
                for record in records:
                    recorded = record.get('source_changes', [])
                    if record['program'] == 'HPCG':
                        self.assertEqual(len(recorded), 1)
                        self.assertEqual(recorded[0].get('file'), relative.as_posix())
                        self.assertTrue(recorded[0].get('reason'))
                        changes.append(recorded)
                    else:
                        self.assertEqual(recorded, [])
                self.assertTrue(changes)
                self.assertTrue(all(change == changes[0] for change in changes))
            for program in corpus.OPENMP:
                with self.subTest(program=program):
                    relevant = [r for r in records if r['program'] == program]
                    self.assertTrue(any(r['compiler'] == corpus.DONOR and r['check'] == 'error'
                                        and 'missing OpenMP runtime' in r.get('cause', '')
                                        and '-fopenmp' in r['flags'] for r in relevant))
                    serial = [r for r in relevant if r.get('variant') == 'serial']
                    self.assertEqual({r['compiler'] for r in serial}, {corpus.DONOR, corpus.KNC})
                    self.assertTrue(all(r['check'] == 'pass' and r.get('fallback_reason') for r in serial))
                    self.assertTrue(all(r.get('panel') == 'primary' and '-fopenmp' not in r['flags']
                                        for r in serial))
                    openmp = [r for r in relevant if r['compiler'] == corpus.KNC
                              and r.get('variant') == 'openmp']
                    self.assertEqual(len(openmp), 1)
                    self.assertTrue(all(r['check'] == 'pass' and r.get('panel') == OPENMP_PANEL
                                        and '-fopenmp' in r['flags'] for r in openmp))
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


class ReviewRuntime(unittest.TestCase):
    """Host builds of harness code only; no card correctness claim."""

    def paused_run(self, binary, directory):
        with (directory / 'stdout').open('w+') as output:
            child = subprocess.Popen([str(binary)], cwd=directory, stdout=output,
                                     env=dict(os.environ, CORPUS_TIMED='1'))
            _, status = os.waitpid(child.pid, os.WUNTRACED)
            output.seek(0)
            before = output.read()
            packed_before = (directory / 'packed.bin').exists()
            if os.WIFSTOPPED(status):
                os.kill(child.pid, signal.SIGCONT)
                self.assertEqual(child.wait(timeout=30), 0)
            else:
                child.returncode = os.waitstatus_to_exitcode(status)
            output.seek(0)
            after = output.read()
        return os.WIFSTOPPED(status), before, after, packed_before

    def test_polybench_materializes_complete_binary_output_before_exit(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            fixture = directory / 'dump.c'
            fixture.write_text('''#include "polybench_capture.h"
int main(void) {
  fprintf(stderr, "begin dump: %s", "A");
  fprintf(stderr, "%0.2lf ", 1.2345678901234567);
  fprintf(stderr, "\\nend   dump: %s\\n", "A");
  fprintf(stderr, "begin dump: %s", "B");
  fprintf(stderr, "%0.2lf ", -2.0);
  fprintf(stderr, "\\nend   dump: %s\\n", "B");
  return 0;
}
''')
            binary = directory / 'dump'
            subprocess.run(['gcc', '-I' + str(corpus.SUPPORT), str(fixture),
                            str(corpus.SUPPORT / 'polybench_capture.c'), '-o', str(binary)],
                           check=True, capture_output=True)
            stopped, _, after, _ = self.paused_run(binary, directory)
            self.assertFalse(stopped, 'ADR-0015 requires exit, without a stop boundary')
            self.assertEqual(after, '', 'format and transfer only after child exit')
            artifact = directory / 'arrays.bin'
            self.assertTrue(artifact.exists(), 'complete output must be materialized on card')
            if artifact.exists():
                arrays = []
                with artifact.open('rb') as data:
                    while name := data.read(80):
                        count, = struct.unpack('=Q', data.read(8))
                        values = struct.unpack('=' + 'd' * count, data.read(8 * count))
                        arrays.append(dict(array=name.rstrip(b'\0').decode(), values=list(values)))
                self.assertEqual(arrays, [dict(array='A', values=[1.2345678901234567]),
                                          dict(array='B', values=[-2.0])])

    def test_supervisor_waits_for_exit_and_defers_transfer(self):
        header = corpus.SUPPORT / 'timing.h'
        self.assertTrue(header.exists(), 'shared launch-to-exit supervisor is required')
        if not header.exists():
            return
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'workload').write_text('#!/bin/sh\necho child-output\necho child-error >&2\nsleep 0.2\nexit 7\n')
            (directory / 'workload').chmod(0o755)
            fixture = directory / 'timer.c'
            fixture.write_text('#include "timing.h"\nint main(void) { int status; '
                               'if (corpus_timed_workload(&status)) return 2; '
                               'return WIFEXITED(status) ? WEXITSTATUS(status) : 3; }\n')
            binary = directory / 'timer'
            # Cygwin's host clock is a stand-in; the card build uses RAW unconditionally.
            subprocess.run(['gcc', '-DCLOCK_MONOTONIC_RAW=CLOCK_MONOTONIC',
                            '-I' + str(corpus.SUPPORT), str(fixture), '-o', str(binary)],
                           check=True, capture_output=True)
            result = subprocess.run([str(binary)], cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 7)
            self.assertLess(result.stdout.index('CORPUS_TIME '), result.stdout.index('child-output'))
            self.assertIn('child-error', result.stderr)
            timing = json.loads(next(line[len('CORPUS_CLOCK '):] for line in result.stdout.splitlines()
                                     if line.startswith('CORPUS_CLOCK ')))
            self.assertEqual(timing['clock'], 'CLOCK_MONOTONIC_RAW')
            self.assertEqual(timing['boundary'], 'launch-to-exit')
            self.assertGreaterEqual((timing['end_ns'] - timing['start_ns']) / 1e9, 0.2)
            self.assertGreater(timing['utc_start_ns'], 0)

    def test_peer_control_uses_corrupted_stream_and_rejects_clean_control(self):
        sources = corpus.SHARED / 'corpus-build/sources'
        for name, package, units, defines in (
                ('zlib', 'zlib-1.3.1', 'adler32 crc32 deflate infback inffast inflate inftrees trees zutil compress uncompr', ['-DCORPUS_ZLIB']),
                ('bzip2', 'bzip2-1.0.8', 'blocksort huffman crctable randtable compress decompress bzlib', [])):
            with self.subTest(codec=name), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                library = sources / package
                binary = directory / 'workload'
                subprocess.run(['gcc', '-O2', '-I' + str(library), *defines,
                                *(str(library / (unit + '.c')) for unit in units.split()),
                                str(corpus.SUPPORT / 'roundtrip.c'), '-o', str(binary)],
                               check=True, capture_output=True)
                (directory / 'input.bin').write_bytes(b'A' * (8 * 1024 * 1024))
                stopped, _, output, packed_before = self.paused_run(binary, directory)
                with self.subTest(boundary=name):
                    self.assertFalse(stopped, 'materialization belongs inside launch-to-exit')
                    self.assertTrue(packed_before)
                    self.assertEqual((directory / 'restored.bin').read_bytes(),
                                     (directory / 'input.bin').read_bytes())
                    self.assertNotIn('CORPUS_CONTROL', output)
                packed = (directory / 'packed.bin').read_bytes()
                clean = subprocess.run([str(binary), 'decode'], cwd=directory,
                                       capture_output=True, text=True)
                self.assertEqual(clean.returncode, 0)
                self.assertIn('CORPUS_CROSS pass', clean.stdout)
                for corrupt in (False, True):
                    control = bytearray(packed)
                    if corrupt:
                        control[0] ^= 1
                    (directory / 'corrupt.bin').write_bytes(control)
                    result = subprocess.run([str(binary), 'control'], cwd=directory,
                                            capture_output=True, text=True)
                    with self.subTest(codec=name, corrupt=corrupt):
                        self.assertEqual(result.returncode, 0 if corrupt else 1)
                        self.assertEqual('CORPUS_CONTROL rejected' in result.stdout, corrupt)
                (directory / 'corrupt.bin').unlink()
                missing = subprocess.run([str(binary), 'control'], cwd=directory,
                                         capture_output=True, text=True)
                self.assertEqual(missing.returncode, 2)
                self.assertNotIn('CORPUS_CONTROL rejected', missing.stdout)
                self.assertEqual((directory / 'packed.bin').read_bytes(), packed)
                bad = subprocess.run([str(binary)],cwd=directory,capture_output=True,text=True,
                                     env=dict(os.environ,CORPUS_CORRUPT='1'))
                self.assertEqual(bad.returncode,1)
                self.assertIn('CORPUS_INJECTED '+name,bad.stdout)
                self.assertNotIn('CORPUS_CHECK pass',bad.stdout)


class PgoPeerPackaging(unittest.TestCase):
    """S11-17: BusyBox-compatible archive and an executable decoder after unpack."""

    def test_peer_unpack_and_decode_commands(self):
        import tarfile
        import s11_17_pgo as pgo
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            donor = root / 'S11-18' / corpus.DONOR / '0/serial/zlib'
            donor.mkdir(parents=True)
            decoder = donor / 'workload'
            decoder.write_text('#!/bin/sh\necho "PEER $1"\n')
            decoder.chmod(0o644)  # Host file permissions must not leak into tar.
            (donor / 'libfixture.so').write_bytes(b'fixture')
            out = root / 'S11-17'
            out.mkdir()
            with patch.object(corpus, 'SHARED', root), patch.object(pgo, 'OUT', out):
                pgo.stage_peer()
            with tarfile.open(out / 'peer.tar') as archive:
                members = archive.getmembers()
                self.assertFalse(any(m.pax_headers for m in members),
                                 'card BusyBox must not encounter pax headers')
                self.assertEqual(archive.getmember('workload').mode, 0o755)
                self.assertEqual(archive.getmember('libfixture.so').mode, 0o644)
            # The actual launcher shell commands followed by its two execl calls.
            result = subprocess.run(
                ['sh', '-ec', 'mkdir -p peer && tar -xf peer.tar -C peer; '
                 './peer/workload decode; ./peer/workload control'],
                cwd=out, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), ['PEER decode', 'PEER control'])
            self.assertEqual(result.stderr, '')

    def test_lead_native_stderr_and_exit_status(self):
        import s11_17_pgo as pgo
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            (out / 'pgo').mkdir()
            (out / 'pgo/workload').touch()
            with patch.object(pgo, 'OUT', out), redirect_stdout(io.StringIO()):
                pgo.stage_lead()
            # A native command emits stderr but exits successfully; Windows
            # PowerShell 5.1 must continue to all thirty pilot launches.
            lead = corpus.windows_path(out / 'lead.ps1').replace("'", "''")
            wrapper = out / 'mock.ps1'
            for code in (0, 7):
                wrapper.write_text(
                    "$global:launches = 0\n"
                    "function python {\n"
                    "  $global:launches++\n"
                    "  & $env:COMSPEC /d /c 'echo benign-native-stderr 1>&2'\n"
                    "  $global:LASTEXITCODE = " + str(code) + "\n}\n"
                    "& '" + lead + "' -Evaluate -Phase pilot\n"
                    "if ($global:launches -ne 30) { exit 9 }\n")
                result = subprocess.run(
                    ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                     '-File', corpus.windows_path(wrapper)],
                    capture_output=True, text=True)
                with self.subTest(native_exit=code):
                    if code:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn('Evaluation failed: full 0 base', result.stderr)
                    else:
                        self.assertEqual(result.returncode, 0, result.stderr)


class CodecSnapshots(unittest.TestCase):
    """Real initial-full zlib captures (launches 034/035): workload, peer decode, control."""
    DATA = Path(__file__).resolve().parent / 'data/s13_01_codec'
    TRANSPORT = dict(result_class='program', exit_code=0, program_exit_code=0,
                     foreign_processes=[], overlapping_jobs=[])

    def job(self, compiler, program='zlib'):
        return dict(program=program, compiler=compiler, flags=['-O2'], run=0, threads=1,
                    input=corpus.INPUTS['zlib'], profile='full', variant='serial', block='initial')

    def test_one_snapshot_set_per_process_attributes_the_timed_workload(self):
        import m4_gate as gate
        for compiler in (corpus.DONOR, corpus.KNC):
            text = (self.DATA / ('zlib-%s.stdout' % compiler)).read_text()
            row = corpus.output_result(self.job(compiler), text, '', 0)
            workload = text[:text.index('CORPUS_ENV_END end\n')] + 'CORPUS_ENV_END end\n'
            with self.subTest(compiler=compiler):
                self.assertEqual(text.count('CORPUS_ENV_BEGIN start'), 3)
                self.assertEqual(row['check'], 'pass', row.get('cause'))
                self.assertEqual(row['environment'], corpus.parse_environment(workload, 'zlib'))
                self.assertEqual(sorted(row['environment']), ['end', 'materialize', 'start'])
                self.assertTrue(gate.environment_valid(row))
        first = text.index('CORPUS_ENV_END start\n') + len('CORPUS_ENV_END start\n')
        start = text[text.index('CORPUS_ENV_BEGIN start'):first]
        materialize = text[first:text.index('CORPUS_ENV_END materialize\n') + len('CORPUS_ENV_END materialize\n')]
        inside = first - len('CORPUS_ENV_END start\n')
        for case, bad, program in (
                ('repeated start in one process', text[:first] + start + text[first:], 'zlib'),
                ('repeated materialize in one process', text.replace(materialize, materialize * 2, 1), 'zlib'),
                ('interleaved set', text[:inside] + start + text[inside:], 'zlib'),
                ('peer verdict in the wrong process', text.replace('CORPUS_CROSS pass\n', '', 1).replace(
                    'CORPUS_CONTROL rejected\n', 'CORPUS_CONTROL rejected\nCORPUS_CROSS pass\n', 1), 'zlib'),
                ('several sets outside a codec launch', text, 'SQLite')):
            row = corpus.output_result(self.job(corpus.KNC, program), bad, '', 0)
            with self.subTest(case=case):
                self.assertEqual(row['check'], 'error')
                self.assertRegex(row['cause'], 'duplicate|interleaved|attributable')

    def test_recheck_rederives_a_completed_block_from_captures_only(self):
        import m4_gate as gate
        with tempfile.TemporaryDirectory() as temporary:
            stage, sealed = Path(temporary) / 'S13-01', Path(temporary) / 'sealed'
            capture = stage / 'initial-full-capture'
            capture.mkdir(parents=True); sealed.mkdir()
            plan, raw = [], []
            for number, compiler in enumerate((corpus.DONOR, corpus.KNC)):
                (capture / ('%03d.stdout' % number)).write_bytes((self.DATA / ('zlib-%s.stdout' % compiler)).read_bytes())
                (capture / ('%03d.stderr' % number)).write_text('')
                plan.append(self.job(compiler))
                # As written by the original parser at launch time.
                raw.append(dict(self.job(compiler), check='error', time_seconds=None, cause='duplicate environment snapshot',
                                stdout=str(capture / ('%03d.stdout' % number)), stderr=str(capture / ('%03d.stderr' % number)),
                                transport=self.TRANSPORT, lead_environment_policy=dict(lead_verified=True)))
            (stage / 'initial-full-raw.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in raw))
            (stage / 'initial-full-done.json').write_text('{"ready": true, "passed": false}\n')
            frozen = {p: p.read_bytes() for p in [stage / 'initial-full-raw.jsonl', *capture.iterdir()]}
            with patch.object(corpus, 'sealed_dir', return_value=sealed), \
                    patch.object(gate, 'load_freeze', return_value=({}, {})), \
                    patch.object(gate, 'launches', return_value=([], plan)), \
                    patch.object(gate, 'prepare_job', return_value=dict(files=['runtime-prefix.json'])), \
                    redirect_stdout(io.StringIO()):
                self.assertFalse(gate.check_block(stage, 'full', 'initial'))  # stored field: error
                gate.recheck(SimpleNamespace(stage=stage, profile='full', block='initial'))
                checked = corpus.read_partition(stage, 'initial-full-checked.jsonl')
                gate.check_block(stage, 'full', 'initial')  # score's path keeps re-deriving
                again = corpus.read_partition(stage, 'initial-full-checked.jsonl')
            self.assertEqual({p: p.read_bytes() for p in frozen}, frozen)
            for rows in (checked, again):
                self.assertEqual([r['check'] for r in rows], ['pass', 'pass'])
                self.assertTrue(all(gate.environment_valid(r) and r['lead_environment_policy'] for r in rows))
            record = json.loads((stage / 'initial-full-recheck.json').read_text())
            self.assertEqual([(r['launch'], r['stored_check'], r['check']) for r in record],
                             [('000.stdout', 'error', 'pass'), ('001.stdout', 'error', 'pass')])
            self.assertTrue(json.loads((stage / 'initial-full-done.json').read_text())['rechecked'])


class TransportResume(unittest.TestCase):
    """S13-01 gate: SSH-only transfers; a launch without a workload result is re-attempted."""
    CLOCK = ('CORPUS_META {"threads":1}\nCORPUS_TIME 1\n'
             'CORPUS_CLOCK {"clock":"CLOCK_MONOTONIC_RAW","boundary":"launch-to-exit",'
             '"start_ns":1,"end_ns":1000000001,"utc_start_ns":2}\n')
    # (stdout, receipt or None, card_run exit status)
    OUTCOMES = {
        'ok': (CLOCK, dict(result_class='program', exit_code=0, program_exit_code=0, card_minutes=0.1), 0),
        'transport': ('', dict(result_class='infrastructure', exit_code=126, program_exit_code=None,
                               card_minutes=0.0, detail='ssh: connect failed'), 126),
        'no-receipt': ('', None, 3221225794),  # ssh.exe/python.exe failed to start (0xC0000142)
        'timed-then-lost': (CLOCK, dict(result_class='infrastructure', exit_code=126, program_exit_code=0,
                                        card_minutes=0.1, detail='finalization failed'), 126),
        'started-then-lost': ('CORPUS_META {"threads":1}\n', dict(
            result_class='infrastructure', exit_code=126, program_exit_code=None,
            card_minutes=0.2, detail='session lost'), 126),
        'latch': ('', dict(result_class='refused', exit_code=125, program_exit_code=None, card_minutes=0.0,
                           detail='DMA cleanup unresolved; lead must inspect card-dma-active.lock'), 125),
    }

    def jobs(self):
        return [dict(program=p, compiler=compiler, run=0, profile='full', block='initial', threads=1,
                     input=corpus.INPUTS[p], variant='serial', flags=['-O2'])
                for p, compiler in (('PB-gemm', corpus.DONOR), ('PB-gemm', corpus.KNC), ('PB-adi', corpus.KNC))]

    def gate(self, temporary, script, resume=False):
        """Run the block with card outcomes scripted per launch (probes always reach the card)."""
        import m4_gate as gate
        stage, sealed = Path(temporary) / 'S13-01', Path(temporary) / 'sealed'
        stage.mkdir(exist_ok=True); sealed.mkdir(exist_ok=True)
        (stage / 'environment-policy.json').write_text(json.dumps(
            dict(lead_verified=True, clock_power_policy='fixed fixture', exclusive_window='fixture')))
        calls, sleeps = [], []
        def card_call(stage_dir, files, mode, density, out, err, profile='full', timeout=3600, record=None):
            outcome = 'ok' if mode == 'probe' else script[mode].pop(0) if script.get(mode) else 'ok'
            calls.append((mode, outcome))
            stdout, receipt, rc = self.OUTCOMES[outcome]
            out.write_text(stdout + (json.dumps(receipt) + '\n' if receipt else ''))
            err.write_text('')
            if receipt and record is not None:
                record.update(receipt)
            return rc
        error = io.StringIO()
        args = SimpleNamespace(stage=stage, profile='full', block='initial', acl_verified=True,
                               timeout=3600, resume=resume)
        with patch.object(corpus, 'sealed_dir', return_value=sealed), \
                patch.object(corpus, 'card_call', side_effect=card_call), \
                patch.object(gate, 'load_freeze', return_value=({}, {})), \
                patch.object(gate, 'launches', side_effect=lambda *a: ([], self.jobs())), \
                patch.object(gate, 'prepare_job', return_value=dict(files=['runtime-prefix.json'])), \
                patch.object(gate, 'check_block', return_value=True), \
                patch.object(gate, '_sleep', side_effect=sleeps.append), redirect_stderr(error):
            code = gate.run(args)
        log = lambda d: json.loads((d / 'initial-full-transport-retries.json').read_text())
        raw = [json.loads(l) for d in (stage, sealed) for l in (d / 'initial-full-raw.jsonl').read_text().splitlines()]
        return SimpleNamespace(code=code, calls=calls, sleeps=sleeps, stderr=error.getvalue(), raw=raw,
                               public_log=log(stage), sealed_log=log(sealed), stage=stage, sealed=sealed)

    def test_card_call_transfers_by_ssh_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            out, err = Path(temporary) / 'a.stdout', Path(temporary) / 'a.stderr'
            with patch.object(corpus.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as run:
                corpus.card_call(Path(temporary), [], 'probe', 'probe', out, err)
            command = run.call_args[0][0]
            self.assertEqual(command[command.index('--transfer') + 1], 'ssh')
            # A card_run process that cannot start is an infrastructure failure, not a crash.
            with patch.object(corpus.subprocess, 'run', side_effect=OSError('0xC0000142')):
                self.assertEqual(corpus.card_call(Path(temporary), [], 'probe', 'probe', out, err), 126)

    def test_two_transport_failures_then_one_final_row(self):
        import m4_gate as gate
        with tempfile.TemporaryDirectory() as temporary:
            result = self.gate(temporary, {'PB-gemm': ['transport', 'no-receipt', 'ok'],
                                           'PB-adi': ['transport', 'ok']})
            self.assertEqual(result.code, 0)
            self.assertEqual(result.sleeps, [30, 60, 30])
            self.assertEqual([(r['program'], r['compiler'], r['transport_retries']) for r in result.raw],
                             [('PB-gemm', corpus.DONOR, 2), ('PB-gemm', corpus.KNC, 0), ('PB-adi', corpus.KNC, 1)])
            self.assertTrue(all(Path(r['stdout']).name == '%03d.stdout' % n for n, r in enumerate(result.raw)))
            failed = [e for e in result.public_log if e['event'] == 'launch']
            self.assertEqual([(e['launch'], e['attempt'], e['result_class']) for e in failed],
                             [('000', 1, 'infrastructure'), ('000', 2, 'infrastructure')])
            self.assertEqual(sum(e['event'] == 'probe' and e['reachable'] for e in result.public_log), 2)
            capture = result.stage / 'initial-full-capture'
            self.assertTrue((capture / '000.transport-1.stdout').exists() and (capture / '000.transport-2.stdout').exists())
            # Held-out retries stay sealed.
            self.assertEqual({e['program'] for e in result.public_log}, {'PB-gemm'})
            self.assertEqual([(e['launch'], e['event']) for e in result.sealed_log], [('002', 'launch'), ('002', 'probe')])
            done = json.loads((result.stage / 'initial-full-done.json').read_text())
            self.assertEqual(done['transport_retries'], 3)
            self.assertEqual(gate.backoff_seconds(6), 600)

    def test_launch_that_started_or_timed_is_never_retried(self):
        import m4_gate as gate
        for outcome in ('timed-then-lost', 'started-then-lost'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as temporary:
                result = self.gate(temporary, {'PB-gemm': [outcome]})
                self.assertEqual(result.calls[0], ('PB-gemm', outcome))
                self.assertEqual([m for m, _ in result.calls], ['PB-gemm', 'PB-gemm', 'PB-adi'])
                self.assertEqual(result.raw[0]['check'], 'fail')
                self.assertEqual(result.sleeps, [])
                self.assertEqual(result.public_log, [])
        # Resume never repeats an interrupted launch whose capture holds a time.
        with tempfile.TemporaryDirectory() as temporary:
            result = self.gate(temporary, {'PB-gemm': ['ok', 'transport'] + ['transport'] * 4})
            self.assertEqual(result.code, gate.PAUSED_EXIT)
            (result.stage / 'initial-full-capture' / '001.stdout').write_text(self.CLOCK)
            again = self.gate(temporary, {}, resume=True)
            self.assertEqual((again.code, again.calls), (1, []))
            self.assertIn('not repeated', again.stderr)

    def test_five_failures_pause_and_resume_continues_the_block(self):
        import m4_gate as gate
        with tempfile.TemporaryDirectory() as temporary:
            first = self.gate(temporary, {'PB-gemm': ['ok'] + ['transport'] * 5})
            self.assertEqual(first.code, gate.PAUSED_EXIT)
            self.assertEqual(first.sleeps, [30, 60, 120, 240])
            self.assertIn('Card unreachable', first.stderr)
            self.assertIn('--resume', first.stderr)
            self.assertEqual(len(first.raw), 1)
            self.assertFalse((first.stage / 'initial-full-done.json').exists())
            self.assertEqual(json.loads((first.stage / 'initial-full-paused.json').read_text())['launch'], '001')
            kept = (first.stage / 'initial-full-raw.jsonl').read_bytes()
            with self.assertRaises(ValueError):  # a plain rerun still refuses a started block
                self.gate(temporary, {})
            again = self.gate(temporary, {}, resume=True)
            self.assertEqual(again.code, 0)
            self.assertEqual(again.calls, [('PB-gemm', 'ok'), ('PB-adi', 'ok')])
            self.assertTrue((first.stage / 'initial-full-raw.jsonl').read_bytes().startswith(kept))
            self.assertEqual([r['compiler'] for r in again.raw if r['program'] == 'PB-gemm'], [corpus.DONOR, corpus.KNC])
            self.assertEqual([e['event'] for e in again.public_log][-2:], ['pause', 'resume'])
            self.assertFalse((first.stage / 'initial-full-paused.json').exists())
        # A DMA latch refusal stops at once and leaves the latch to the lead.
        with tempfile.TemporaryDirectory() as temporary:
            latch = self.gate(temporary, {'PB-gemm': ['latch']})
            self.assertEqual((latch.code, latch.sleeps, len(latch.calls)), (gate.LATCH_EXIT, [], 1))
            self.assertIn('Not deleted: latch recovery is a lead decision', latch.stderr)


if __name__ == '__main__':
    unittest.main()
