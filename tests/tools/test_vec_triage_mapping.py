"""Captured addr2line input for S12-19's production PC mapping seam.

Captured on 2026-11-14 with the installed gcc-knc-16.2.0 prefix:
  k1om-mpss-linux-gcc -O2 -march=knc -g -fopt-info-vec-all=mapping.opt
      mapping.c -o mapping
  k1om-mpss-linux-addr2line -a -f -C -e mapping
      0x4005b0 0x4005bf 0x4006c0 0x40061f 0x1
The source is below. Only the absolute source prefix is replaced by src/.
Raw captures are in .work/_shared/S12-19/mapping.{addr2line,opt}.
No native execution was performed or is required by these host tests.

regions_from_addr2line(text, source_regions, module) must group exact queried
PCs into source regions, returning the existing region fields plus pc_ranges
(half-open pairs). A queried PC is evidence only for that PC, not the gap to
the next query. The triage API accepts these discontiguous pc_ranges in place
of start/end. Source regions are established separately; a function name alone
never establishes either a source loop or straight-line code.

Production must query the sampled ELF (or debug data demonstrably belonging
to that ELF), never apply addresses from a new build to an old PC capture.
"""
import importlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))

SOURCE = '''__attribute__((noinline, noclone))
double strict_sum(const double *a, int n)
{
    double s = 0.0;
    for (int i = 0; i < n; ++i)
        s += a[i];
    return s;
}
__attribute__((noinline, noclone))
void update(double *a, int n)
{
    for (int i = 0; i < n; ++i)
        a[i] *= 2.0;
}
static double a[64];
int main(int argc, char **argv)
{
    update(a, argc < 64 ? argc : 64);
    return strict_sum(a, argc < 64 ? argc : 64) != 0.0;
}
'''

ADDR2LINE = '''0x00000000004005b0
strict_sum
src/mapping.c:6
0x00000000004005bf
strict_sum
src/mapping.c:6
0x00000000004006c0
update
src/mapping.c:13
0x000000000040061f
strict_sum
src/mapping.c:8
0x0000000000000001
??
??:0
'''

# Verbatim messages from mapping.opt, excluding repeated candidate reports.
# The two candidate messages deliberately retain their "optimized" severity:
# a candidate is not a successful loop vectorization.
OPT_INFO = '''src/mapping.c:5:23: optimized:  KNC candidate access mode V8DF, factor = 8
src/mapping.c:5:23: optimized:  KNC candidate accesses: gather 0, scatter 0, converting 0, masked 0; reductions 1
src/mapping.c:5:23: missed: couldn't vectorize loop
src/mapping.c:5:23: missed: Loop costings may not be worthwhile.
src/mapping.c:2:8: note: vectorized 0 loops in function.
src/mapping.c:12:23: optimized: loop vectorized using 64 byte vectors and unroll factor 8
src/mapping.c:12:23: optimized: epilogue loop vectorized using masked 64 byte vectors and unroll factor 8
src/mapping.c:10:6: note: vectorized 1 loops in function.
'''


def source_region(name, first, last, function, kind='loop'):
    return dict(id=name, file='src/mapping.c', line_start=first,
                line_end=last, function=function, kind=kind)


def samples(pc, count):
    return ''.join(f'serial-STREAM profile-workload {pc:x} tid=17 ignored ??:0\n'
                   for _ in range(count))


class VecTriageMappingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triage = importlib.import_module('vec_triage')

    def test_captured_addresses_map_to_source_loops_without_filling_gaps(self):
        discovered = self.triage.source_loops('src/mapping.c', SOURCE)
        self.assertEqual([(r['line_start'], r['line_end']) for r in discovered],
                         [(5, 6), (12, 13)])
        regions = self.triage.regions_from_addr2line(
            ADDR2LINE,
            [source_region('sum', 5, 6, 'strict_sum'),
             source_region('update', 12, 13, 'update'),
             source_region('epilogue', 7, 8, 'strict_sum', 'not a loop')],
            module='profile-workload')
        by_id = {r['id']: r for r in regions}
        self.assertEqual(set(by_id), {'sum', 'update', 'epilogue'})
        self.assertEqual([tuple(p) for p in by_id['sum']['pc_ranges']],
                         [(0x4005b0, 0x4005b1), (0x4005bf, 0x4005c0)])
        self.assertTrue(all(r['module'] == 'profile-workload' for r in regions))
        result = self.triage.triage_program(
            program='STREAM', opt_info=OPT_INFO, regions=regions,
            pc_text=(samples(0x4005b0, 3) + samples(0x4005bf, 2)
                     + samples(0x4006c0, 2) + samples(0x40061f, 1)
                     + samples(0x1, 1) + samples(0x4005b1, 1)),
            cpu_seconds=1.0)
        self.assertEqual(result['total_samples'], 10)
        self.assertEqual(result['unmapped_samples'], 2)
        self.assertEqual([(r['id'], r['samples']) for r in result['rows']],
                         [('sum', 5), ('update', 2), ('epilogue', 1)])
        self.assertEqual(result['rows'][0]['status'], 'missed-with-reason')
        # Real strict sum output is cost-related, not an in-order refusal.
        # gcc/tree-vect-loop.cc:2556 supplies this actual diagnostic.
        self.assertEqual(result['rows'][0]['reasons'], ['cost model'])
        self.assertAlmostEqual(result['rows'][0]['cpu_seconds'], 0.5)
        self.assertEqual(result['rows'][1]['status'], 'vectorized')
        self.assertEqual(result['rows'][2]['status'], 'not a loop')

    def test_frozen_executable_unknown_line_does_not_inherit_a_named_function(self):
        # Actual capture with the same addr2line flags against
        # .work/_shared/S11-18/gcc-knc/0/serial/STREAM/workload.
        captured = '0x0000000000400960\nmain\n??:0\n'
        regions = self.triage.regions_from_addr2line(
            captured, [source_region('candidate', 5, 6, 'main')],
            module='profile-workload')
        self.assertEqual(regions, [])
        result = self.triage.triage_program(
            program='STREAM', opt_info='', regions=regions,
            pc_text=samples(0x400960, 1), cpu_seconds=0.01)
        self.assertEqual(result['unmapped_samples'], 1)
        self.assertEqual(result['rows'], [])


if __name__ == '__main__':
    unittest.main()
