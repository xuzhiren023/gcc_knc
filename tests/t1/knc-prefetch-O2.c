// S8-03 / E5-07, ADR-0009 point 5: -march=knc turns -fprefetch-loop-arrays on
// at -O2 and prefetches each stream at two levels, vprefetch1 (L2) ahead of
// vprefetch0 (L1), at C5's best distances in lines: L1 16 / L2 32 for one or
// two streams; L1 8 when the L1 footprint (distance x streams x threads per
// core) would exceed a quarter of L1 (128 lines), as for eight streams at the
// default four threads.  Displacements are lines x 64 bytes; the stencil's
// one prefetched x reference is the leading x[i+1], and the loop pointer may
// be anchored on any of the three x accesses, so its displacement is within
// two elements (8 bytes) of the line.
// options: -O2 -ffp-contract=off
// scan-asm-func stream_f32: \bvprefetch0\s+1024\(
// scan-asm-func stream_f32: \bvprefetch1\s+2048\(
// Both streams of stream_f32 (x read, y written) are prefetched at both levels.
// scan-asm-func stream_f32: \bvprefetch0\s+1024\([^\n]*\n[\s\S]*?\bvprefetch0\s+1024\(
// scan-asm-func stream_f32: \bvprefetch1\s+2048\([^\n]*\n[\s\S]*?\bvprefetch1\s+2048\(
// scan-asm-func stencil_f32: \bvprefetch0\s+10(?:16|20|24|28|32)\(
// scan-asm-func stencil_f32: \bvprefetch1\s+20(?:40|44|48|52|56)\(
// scan-asm-func row8_f32: \bvprefetch0\s+512\(
// scan-asm-func row8_f32: \bvprefetch1\s+2048\(
// Never an L1 prefetch without its L2 prefetch: no other distances appear.
// scan-asm-not: \bvprefetch0\s+(?!(?:512|1016|1020|1024|1028|1032|1092)\()
// scan-asm-not: \bvprefetch1\s+(?!(?:2040|2044|2048|2052|2056|2184)\()
// scan-asm-not: \bvprefetch(?:2|nta|e[a-z0-9]*)\b
// A loop that fits in L1 gets no prefetch.
// scan-asm-loop-not l1_resident_f32: \bvprefetch
// Distances stay in bytes when the step exceeds a line (lead note, WRF's
// k loop: 51 trips, 273-float step): L2 32 lines = 2048 bytes is 2 steps
// (2184 bytes), L1 16 lines = 1024 bytes is 1 step (1092 bytes), and the
// trip check uses 4 x 2 iterations, not 4 x 32.
// scan-asm-func column_f32: \bvprefetch1\s+2184\(
// scan-asm-func column_f32: \bvprefetch0\s+1092\(
// A loop whose trip count is only known at run time is versioned on it (lead
// changes 2026-11-08, card: M2 short at length 17 ran one vector iteration
// with four prefetches and their moves, 1.30x slower).  The prefetched copy
// runs only when the loop runs at least four L2 distances, 4 x 32 = 128
// vector iterations: the guard compares the loop's iteration count less one
// against 127.  The other copy is the loop as it was, without any prefetch:
// a label, vprefetch-free lines around the vmulps, and a jump back.
// scan-asm-func stream_f32: \bcmpq\s+\$127,
// scan-asm-func stream_f32: ^(\.L\d+):\n(?:(?!\s*vprefetch)[^\n]*\n)*?\s+vmulps[^\n]*\n(?:(?!\s*vprefetch)[^\n]*\n)*?\s+j[a-z]+\s+\1$
#include "knc-prefetch.h"

void
column_f32 (float *restrict y, const float *restrict x, float a)
{
#pragma GCC novector
  for (unsigned int k = 0; k < 51; ++k)
    y[k * 273] = a * x[k * 273];
}
