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


if __name__ == '__main__':
    unittest.main()
