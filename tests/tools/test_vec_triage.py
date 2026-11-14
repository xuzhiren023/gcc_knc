"""S12-19 host contract: GCC diagnostic text and S11-15 attributed PC rows.

No compiler, corpus source, or card is needed. Region addresses describe the
SAMPLED executable, not a newly rebuilt executable. Production collection must
establish that mapping before calling this analysis seam.

Proposed API: triage_program(program, opt_info, regions, pc_text, cpu_seconds)
returns {program, rows, total_samples, unmapped_samples}. Each hot region row
has id, status, reasons, samples, cpu_seconds. summarize(program_results)
returns {reasons: [{reason, cpu_seconds, ...}], ...}. Reason totals are
non-additive when a loop has multiple blockers; each reason counts a loop once.
Regions use half-open PC ranges and inclusive source line ranges, and explicitly
distinguish proven loops from non-loop code. Unknown mapping is not non-loop code.
"""
import importlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))


def region(name, line, pc, *, kind='loop', file='src/kernel.c'):
    return dict(id=name, file=file, function='kernel', line_start=line,
                line_end=line + 3, start=pc, end=pc + 16,
                module='profile-workload', kind=kind)


def pcs(pc, count, *, program='STREAM', module='profile-workload'):
    # Same textual shape as S11-15/batch-attribution-pcs.txt. Repeated PCs
    # are distinct samples; source lookup may be absent in that artifact.
    return ''.join(f'serial-{program} {module} {pc:x} tid=17 kernel ??:0\n'
                   for _ in range(count))


class VecTriageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triage = importlib.import_module('vec_triage')

    def analyze(self, diagnostics, regions, samples, seconds=1.0,
                program='STREAM'):
        return self.triage.triage_program(
            program=program, opt_info=diagnostics, regions=regions,
            pc_text=samples, cpu_seconds=seconds)

    def test_known_reasons_rank_by_samples_and_preserve_nonloops(self):
        # Message templates from the shared GCC tree; only %T/%G operands
        # and source coordinates are fixture substitutions.
        cases = [
            # gcc/tree-vect-data-refs.cc:484
            ('alias', 'possible alias involving gather/scatter between a and b'),
            # gcc/tree-vect-data-refs.cc:5445-5446
            ('unknown stride', 'not vectorized: not suitable for strided load x = *a;'),
            # gcc/tree-vect-loop.cc:1475-1476
            ('control flow', 'not vectorized: unsupported control flow in loop.'),
            # gcc/tree-vect-loop.cc:1865
            ('cost model', 'not vectorized: vectorization not profitable.'),
            # gcc/tree-vect-stmts.cc:13329-13330
            ('unsupported operation', 'not vectorized: relevant stmt not supported: x = foo ();'),
            # gcc/tree-vect-loop.cc:7480
            ('reduction order', 'in-order reduction chain without SLP.'),
        ]
        diagnostics, regions, samples = [], [], []
        for index, (reason, message) in enumerate(cases, 1):
            line, pc = index * 10, 0x1000 + index * 32
            regions.append(region(reason, line, pc))
            # Reasons often refer to a statement inside the loop, not its header.
            diagnostics.append(f'src/kernel.c:{line + 1}:9: missed: {message}')
            samples.append(pcs(pc + 4, 9 - index))
        regions += [region('vector', 70, 0x1200),
                    region('setup', 80, 0x1300, kind='not a loop')]
        diagnostics += ['src/kernel.c:70:3: optimized: loop vectorized using 64 byte vectors']
        samples += [pcs(0x1204, 2), pcs(0x1304, 1)]
        result = self.analyze('\n'.join(diagnostics), regions,
                              ''.join(samples), seconds=0.36)
        self.assertEqual(result['total_samples'], 36)
        self.assertEqual(result['unmapped_samples'], 0)
        rows = result['rows']
        self.assertEqual([r['id'] for r in rows],
                         [c[0] for c in cases] + ['vector', 'setup'])
        self.assertEqual([r['samples'] for r in rows], list(range(8, 0, -1)))
        for row, (reason, _) in zip(rows, cases):
            self.assertEqual(row['status'], 'missed-with-reason')
            self.assertEqual(set(row['reasons']), {reason})
            self.assertAlmostEqual(row['cpu_seconds'], row['samples'] * 0.01)
        self.assertEqual(rows[-2]['status'], 'vectorized')
        self.assertEqual(rows[-1]['status'], 'not a loop')
        summary = self.triage.summarize([result])
        self.assertEqual([r['reason'] for r in summary['reasons']],
                         [c[0] for c in cases])
        self.assertAlmostEqual(summary['reasons'][0]['cpu_seconds'], 0.08)

    def test_vectorized_wins_over_failed_analysis_modes_and_slp_is_not_a_loop(self):
        diagnostics = '''src/kernel.c:10:3: missed: couldn't vectorize loop
src/kernel.c:11:7: missed: not vectorized: no vectype for stmt: x = *a;
src/kernel.c:10:3: optimized: loop vectorized using 64 byte vectors
src/kernel.c:10:3: optimized: loop versioned for vectorization because of possible aliasing
src/kernel.c:20:3: optimized: basic block part vectorized using 64 byte vectors
'''
        result = self.analyze(diagnostics,
                              [region('loop', 10, 0x1000),
                               region('slp', 20, 0x2000, kind='not a loop')],
                              pcs(0x1004, 3) + pcs(0x2004, 1))
        loop, slp = result['rows']
        self.assertEqual(loop['status'], 'vectorized')
        self.assertEqual(loop['reasons'], [])
        self.assertEqual(slp['status'], 'not a loop')
        self.assertEqual(self.triage.summarize([result])['reasons'], [])

    def test_nested_loops_have_exclusive_time_and_body_diagnostics(self):
        outer = region('outer', 10, 0x1000)
        outer.update(line_end=40, end=0x1100)
        inner = region('inner', 20, 0x1040)
        result = self.analyze(
            'src/kernel.c:21:9: missed: not vectorized: unsupported control flow in loop.',
            [outer, inner], pcs(0x1044, 7) + pcs(0x1010, 3))
        rows = {r['id']: r for r in result['rows']}
        self.assertEqual(rows['inner']['samples'], 7)
        self.assertEqual(rows['outer']['samples'], 3)
        self.assertEqual(set(rows['inner']['reasons']), {'control flow'})
        # Silence is not evidence of success or of straight-line code.
        self.assertEqual(rows['outer']['status'], 'unknown')
        self.assertEqual(rows['outer']['reasons'], [])
        self.assertAlmostEqual(sum(r['cpu_seconds'] for r in rows.values()), 1.0)

    def test_unmapped_pcs_modules_and_other_programs_do_not_inherit_hot_function(self):
        result = self.analyze(
            'src/kernel.c:10:3: optimized: loop vectorized using 64 byte vectors',
            [region('loop', 10, 0x1000)],
            pcs(0x1004, 2) + pcs(0x1010, 1)  # End is exclusive.
            + pcs(0x1004, 3, module='libc-2.21.so')
            + pcs(0x9999, 4) + pcs(0x1004, 100, program='NPB-CG'))
        self.assertEqual(result['total_samples'], 10)
        self.assertEqual(result['unmapped_samples'], 8)
        self.assertEqual(len(result['rows']), 1)
        self.assertEqual(result['rows'][0]['samples'], 2)
        self.assertAlmostEqual(result['rows'][0]['cpu_seconds'], 0.2)

    def test_repeated_blockers_count_once_and_file_paths_disambiguate(self):
        diagnostics = '''src/kernel.c:11:4: missed: not vectorized: unsupported control flow in loop.
src/kernel.c:11:4: missed: not vectorized: unsupported control flow in loop.
src/kernel.c:12:4: missed: possible alias involving gather/scatter between a and b
other/kernel.c:10:4: optimized: loop vectorized using 64 byte vectors
'''
        result = self.analyze(diagnostics, [region('loop', 10, 0x1000)],
                              pcs(0x1004, 5), seconds=0.5)
        row = result['rows'][0]
        self.assertEqual(row['status'], 'missed-with-reason')
        self.assertEqual(set(row['reasons']), {'alias', 'control flow'})
        summary = self.triage.summarize([result])
        self.assertEqual(len(summary['reasons']), 2)
        for reason in summary['reasons']:
            self.assertAlmostEqual(reason['cpu_seconds'], 0.5)

    def test_corpus_summary_sums_time_not_raw_counts_across_programs(self):
        first = self.analyze(
            'src/kernel.c:11:4: missed: not vectorized: unsupported control flow in loop.',
            [region('loop', 10, 0x1000)], pcs(0x1004, 10), seconds=0.1)
        second = self.analyze(
            'src/kernel.c:11:4: missed: possible alias involving gather/scatter between a and b',
            [region('loop', 10, 0x1000)], pcs(0x1004, 2, program='NPB-CG'),
            seconds=0.4, program='NPB-CG')
        reasons = self.triage.summarize([first, second])['reasons']
        self.assertEqual([r['reason'] for r in reasons], ['alias', 'control flow'])
        self.assertAlmostEqual(reasons[0]['cpu_seconds'], 0.4)
        self.assertAlmostEqual(reasons[1]['cpu_seconds'], 0.1)

    def test_development_allowlist(self):
        for name in ('PB-adi', 'adi', 'PB-durbin', 'durbin', 'bzip2', 'unknown'):
            with self.subTest(program=name), self.assertRaises(ValueError):
                self.analyze('', [], '', program=name)

    def test_in_order_double_reduction_refusal(self):
        # gcc/tree-vect-loop.cc:7652. Do not infer this reason merely from
        # the presence of a floating-point sum in the source.
        result = self.analyze(
            'src/kernel.c:10:3: missed: in-order double reduction not supported.',
            [region('loop', 10, 0x1000)], pcs(0x1004, 1))
        self.assertEqual(result['rows'][0]['status'], 'missed-with-reason')
        self.assertEqual(result['rows'][0]['reasons'], ['reduction order'])


if __name__ == '__main__':
    unittest.main()
