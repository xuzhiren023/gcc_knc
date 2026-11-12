"""S11-11 host contract; no compilers, source extraction, or card jobs.

tools/corpus.py exposes make_plan(repetitions=3, extra_flags=None, core_count=...),
parse_results(JSONL_text), and summarize(plan, results). Plans are ordered lists
of launch dictionaries. extra_flags maps compiler names to additional flag sets,
each represented by a list of arguments; the baseline pair remains present.

Result rows add time_seconds, check (pass/fail/error), and an optional cause to
the launch identity below. Summary partitions contain one row per comparison
(program, threads, input, donor flags, candidate flags), including failed rows
with speedup=None. Speedup is the median of paired donor/candidate time ratios;
each partition's headline median weights each complete comparison equally.
Missing, duplicate, mismatched and failed launches must be reported, not dropped.
Program identity, not a supplied held_out label, controls the partition.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import corpus


DONOR = 'gcc-5.1.1'
CANDIDATE = 'gcc-knc'
HELD_OUT = {'PB-adi', 'PB-durbin', 'bzip2'}
SERIAL = {'PB-' + name for name in (
    'gemm', 'atax', 'cholesky', 'ludcmp', 'jacobi-2d', 'heat-3d', 'adi', 'durbin'
)} | {'zlib', 'SQLite', 'bzip2'}
OPENMP = {'STREAM', 'NPB-CG', 'NPB-EP', 'NPB-MG', 'NPB-IS', 'HPCG'}


def fixture(program, donor_times=(10, 20, 30), knc_times=(5, 10, 15), threads=1):
    """Independent synthetic observations, deliberately unequal across runs."""
    plan, results = [], []
    for run, (donor, knc) in enumerate(zip(donor_times, knc_times)):
        for compiler, seconds in ((DONOR, donor), (CANDIDATE, knc)):
            job = dict(program=program, compiler=compiler, flags=['-O2'],
                       run=run, threads=threads, input='fixture-seed-11',
                       held_out=program in HELD_OUT)
            plan.append(job)
            results.append(dict(job, time_seconds=seconds, check='pass'))
            if program.startswith('PB-'):
                results[-1]['checksum'] = [dict(array='A', count=2, sum=3.,
                                                abs=3., squares=5., weighted=8.)]
    return plan, results


class CorpusPlan(unittest.TestCase):
    def test_complete_baseline_and_interleaved_repetitions(self):
        plan = corpus.make_plan(repetitions=3, core_count=60)
        self.assertEqual({row['program'] for row in plan}, SERIAL | OPENMP)
        groups = {}
        for row in plan:
            self.assertEqual(row['held_out'], row['program'] in HELD_OUT)
            self.assertIn('-O2', row['flags'])
            self.assertTrue(row['input'])
            if row['compiler'] == CANDIDATE:
                self.assertIn('-march=knc', row['flags'])
            groups.setdefault((row['program'], row['threads']), []).append(row)
        for program in SERIAL | OPENMP:
            self.assertEqual({threads for name, threads in groups if name == program},
                             {60, 240} if program in OPENMP else {1})
        for rows in groups.values():
            self.assertEqual(len(rows), 6)
            seen_runs = set()
            for offset in range(0, len(rows), 2):
                pair = rows[offset:offset + 2]
                self.assertEqual({row['compiler'] for row in pair}, {DONOR, CANDIDATE})
                self.assertEqual(pair[0]['run'], pair[1]['run'])
                self.assertEqual(pair[0]['input'], pair[1]['input'])
                seen_runs.add(pair[0]['run'])
            self.assertEqual(len(seen_runs), 3)
            # Each compiler gets at least one first position (ADR-0010).
            self.assertEqual({row['compiler'] for row in rows[::2]}, {DONOR, CANDIDATE})

    def test_extra_flags_preserve_baseline_and_frozen_inputs(self):
        baseline = corpus.make_plan(repetitions=3, core_count=60)
        extended = corpus.make_plan(repetitions=3, extra_flags={
            DONOR: [['-O3']], CANDIDATE: [['-O3', '-mphinix']]}, core_count=60)
        for row in baseline:
            self.assertIn(row, extended)
        for compiler, option in ((DONOR, '-O3'), (CANDIDATE, '-mphinix')):
            extra = [row for row in extended if row['compiler'] == compiler
                     and option in row['flags']]
            self.assertEqual({row['program'] for row in extra}, SERIAL | OPENMP)
        frozen = {(row['program'], row['threads']): row['input'] for row in baseline}
        for row in extended:
            self.assertEqual(row['input'], frozen[row['program'], row['threads']])

    def test_card_core_count_is_required_and_controls_density(self):
        with self.assertRaises(ValueError):
            corpus.make_plan()
        plan = corpus.make_plan(core_count=59)
        self.assertEqual({r['threads'] for r in plan if r['program'] == 'STREAM'}, {59, 240})


class CorpusResults(unittest.TestCase):
    def test_json_lines_preserve_failure_and_launch_metadata(self):
        _, rows = fixture('NPB-CG', threads=240)
        rows[1].update(time_seconds=None, check='error', cause='missing libgfortran')
        text = '\n'.join(json.dumps(row) for row in rows) + '\n'
        self.assertEqual(corpus.parse_results(text), rows)

    def test_malformed_json_and_invalid_success_timings_are_rejected(self):
        with self.assertRaises(ValueError):
            corpus.parse_results('{broken JSON}\n')
        for seconds in (None, 0, -1, float('nan'), float('inf')):
            with self.subTest(seconds=seconds):
                _, rows = fixture('zlib')
                rows[0]['time_seconds'] = seconds
                with self.assertRaises(ValueError):
                    corpus.parse_results(json.dumps(rows[0]) + '\n')

    def test_paired_ratios_not_ratio_of_unpaired_medians(self):
        plan, rows = fixture('PB-gemm', (10, 20, 30), (1, 10, 3))
        report = corpus.summarize(plan, list(reversed(rows)))
        self.assertEqual(report['failures'], [])
        self.assertEqual(len(report['development']), 1)
        self.assertAlmostEqual(report['development'][0]['speedup'], 10)
        self.assertAlmostEqual(report['median_speedup'], 10)

    def test_held_out_programs_cannot_change_development_median(self):
        plan, rows = [], []
        for program, speedup in [('PB-gemm', 2), ('zlib', 1), ('SQLite', 4),
                                 ('PB-adi', 100), ('PB-durbin', 100), ('bzip2', 100)]:
            jobs, observations = fixture(program, (speedup,) * 3, (1,) * 3)
            plan.extend(jobs)
            rows.extend(observations)
        # Untrusted result labels cannot leak a held-out program into development.
        for row in rows:
            row['held_out'] = False
        report = corpus.summarize(plan, rows)
        self.assertEqual({row['program'] for row in report['held_out']}, HELD_OUT)
        self.assertEqual({row['program'] for row in report['development']},
                         {'PB-gemm', 'zlib', 'SQLite'})
        self.assertAlmostEqual(report['median_speedup'], 2)
        self.assertAlmostEqual(report['held_out_median_speedup'], 100)

    def test_thread_and_flag_comparisons_remain_separate(self):
        plan, rows = [], []
        for threads, flags, ratio in ((60, ['-O2'], 2), (240, ['-O2'], 4),
                                      (240, ['-O3', '-mphinix'], 8)):
            jobs, observations = fixture('STREAM', (8,) * 3, (8 / ratio,) * 3, threads)
            for row in jobs + observations:
                if row['compiler'] == CANDIDATE:
                    row['flags'] = list(flags)
            # A donor launch can be reused for comparisons to extra candidates.
            for target, source in ((plan, jobs), (rows, observations)):
                for row in source:
                    if row not in target:
                        target.append(row)
                    elif row['compiler'] != DONOR:
                        self.fail('fixture duplicated a candidate')
        report = corpus.summarize(plan, rows)
        self.assertEqual(report['failures'], [])
        self.assertEqual(sorted(row['speedup'] for row in report['development']), [2, 4, 8])

    def test_failed_or_missing_runs_are_listed_and_not_cherry_picked(self):
        for mode in ('check', 'build', 'missing', 'duplicate', 'input'):
            with self.subTest(mode=mode):
                plan, rows = fixture('zlib')
                if mode == 'check':
                    rows[1].update(check='fail', cause='round trip mismatch')
                elif mode == 'build':
                    rows[1].update(check='error', time_seconds=None,
                                   cause='compiler rejected source')
                elif mode == 'missing':
                    rows.pop(1)
                elif mode == 'duplicate':
                    rows.append(dict(rows[1]))
                else:
                    rows[1]['input'] = 'different-input'
                report = corpus.summarize(plan, rows)
                self.assertTrue(report['failures'])
                self.assertEqual(len(report['development']), 1)
                self.assertIsNone(report['development'][0]['speedup'])
                self.assertIsNone(report['median_speedup'])

    def test_empty_results_report_every_planned_program(self):
        first, _ = fixture('zlib')
        second, _ = fixture('bzip2')
        report = corpus.summarize(first + second, [])
        self.assertTrue(report['failures'])
        self.assertEqual([row['program'] for row in report['development']], ['zlib'])
        self.assertEqual([row['program'] for row in report['held_out']], ['bzip2'])
        self.assertIsNone(report['median_speedup'])
        self.assertIsNone(report['held_out_median_speedup'])

    def test_polybench_tolerance_and_missing_output_fail_closed(self):
        for value, passes in ((3. + 1e-9, True), (3.01, False), (float('nan'), False)):
            plan, rows = fixture('PB-gemm')
            rows[1]['checksum'][0]['sum'] = value
            report = corpus.summarize(plan, rows)
            self.assertEqual(report['development'][0]['speedup'] is not None, passes)
            self.assertEqual(bool(report['failures']), not passes)
        plan, rows = fixture('PB-gemm')
        del rows[1]['checksum']
        self.assertIsNone(corpus.summarize(plan, rows)['median_speedup'])

    def test_native_output_checks_and_affinity_metadata(self):
        checks = {
            'NPB-CG': 'Verification = SUCCESSFUL',
            'STREAM': 'Solution Validates: avg error less than 1e-13',
            'HPCG': 'HPCG result is VALID with a GFLOP/s rating of=1',
            'zlib': 'CORPUS_CHECK pass',
            'bzip2': 'CORPUS_CHECK pass',
            'SQLite': 'CORPUS_CHECK pass',
        }
        meta = 'CORPUS_META {"cores":59,"threads":59}\nCORPUS_TIME 1.25\n'
        for program, good in checks.items():
            plan, _ = fixture(program, threads=59)
            self.assertEqual(corpus.output_result(plan[0], meta + good, '', 0)['check'], 'pass')
            self.assertNotEqual(corpus.output_result(plan[0], meta, '', 0)['check'], 'pass')
            self.assertNotEqual(corpus.output_result(plan[0], meta + good, '', 1)['check'], 'pass')
            self.assertNotEqual(corpus.output_result(plan[0], meta.replace('"threads":59', '"threads":60') + good, '', 0)['check'], 'pass')
        plan, rows = fixture('PB-gemm', threads=59)
        good = meta + 'CORPUS_ARRAY ' + json.dumps(rows[0]['checksum'][0])
        self.assertEqual(corpus.output_result(plan[0], good, '', 0)['checksum'], rows[0]['checksum'])
        self.assertNotEqual(corpus.output_result(plan[0], meta, '', 0)['check'], 'pass')

    def test_lead_collects_fake_launches_and_marks_checksum_mismatch(self):
        # Exercise host orchestration without SSH, compilers or card execution.
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary)
            settings = dict(extra_flags={}, repetitions=3)
            corpus.write_json(stage / 'settings.json', settings)
            builds = []
            for compiler, variants in corpus.flag_sets().items():
                for program in corpus.PROGRAMS:
                    builds.append(dict(program=program, compiler=compiler, flags=variants[0],
                                       check='pass' if program == 'PB-gemm' else 'error',
                                       files=['/cygdrive/c/fixture/' + compiler + '/workload'],
                                       cause='fixture unavailable compiler', log='fixture.log'))
            corpus.write_json(stage / 'builds.json', builds)

            def fake_call(directory, files, mode, density, stdout, stderr):
                if mode == 'probe':
                    text = 'CORPUS_META {"cores":59,"threads":240}\n'
                else:
                    self.assertEqual(mode, 'PB-gemm')
                    self.assertEqual(density, 'serial')
                    self.assertTrue(files[0].startswith('C:/fixture/'))
                    checksum = dict(array='C', count=2, sum=3., abs=3., squares=5., weighted=8.)
                    if 'gcc-knc' in files[0]:
                        checksum['sum'] = 9.
                    text = ('CORPUS_META {"cores":59,"threads":1}\nCORPUS_TIME 1.0\n'
                            'CORPUS_ARRAY ' + json.dumps(checksum) + '\n')
                stdout.write_text(text)
                stderr.write_text('')
                return 0

            args = type('Args', (), {'stage': stage})()
            with patch.object(corpus, 'card_call', side_effect=fake_call), patch('builtins.print'):
                # The acceptance suite runs with Windows Python like the lead.
                corpus.lead(args)
            results = corpus.parse_results((stage / 'results.jsonl').read_text())
            self.assertEqual(len(results), 138)
            candidate = [r for r in results if r['program'] == 'PB-gemm' and r['compiler'] == CANDIDATE]
            self.assertEqual(len(candidate), 3)
            self.assertTrue(all(r['check'] == 'fail' and 'checksum' in r['cause'] for r in candidate))
            self.assertEqual({r['threads'] for r in results if r['program'] == 'STREAM'}, {59, 240})
            summary = json.loads((stage / 'summary.json').read_text())
            self.assertIsNone(summary['median_speedup'])
            self.assertEqual({r['program'] for r in summary['held_out']}, HELD_OUT)


if __name__ == '__main__':
    unittest.main()
