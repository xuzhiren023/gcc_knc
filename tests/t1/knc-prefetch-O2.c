// S8-03 / E5-07, ADR-0009 point 5: -march=knc turns -fprefetch-loop-arrays on
// at -O2 and prefetches each stream at two levels, vprefetch1 (L2) ahead of
// vprefetch0 (L1), at C5's best distances in lines: L1 16 / L2 32 for one or
// two streams; L1 8 when the L1 footprint (distance x streams x threads per
// core) would exceed a quarter of L1 (128 lines), as for eight streams at the
// default four threads.  Displacements are lines x 64 bytes; the stencil's
// prefetched reference may sit one element (4 bytes) either side of the line.
// options: -O2 -ffp-contract=off
// scan-asm-func stream_f32: \bvprefetch0\s+1024\(
// scan-asm-func stream_f32: \bvprefetch1\s+2048\(
// Both streams of stream_f32 (x read, y written) are prefetched at both levels.
// scan-asm-func stream_f32: \bvprefetch0\s+1024\([^\n]*\n[\s\S]*?\bvprefetch0\s+1024\(
// scan-asm-func stream_f32: \bvprefetch1\s+2048\([^\n]*\n[\s\S]*?\bvprefetch1\s+2048\(
// scan-asm-func stencil_f32: \bvprefetch0\s+10(?:20|24|28)\(
// scan-asm-func stencil_f32: \bvprefetch1\s+20(?:44|48|52)\(
// scan-asm-func row8_f32: \bvprefetch0\s+512\(
// scan-asm-func row8_f32: \bvprefetch1\s+2048\(
// Never an L1 prefetch without its L2 prefetch: no other distances appear.
// scan-asm-not: \bvprefetch0\s+(?!(?:512|1020|1024|1028)\()
// scan-asm-not: \bvprefetch1\s+(?!(?:2044|2048|2052)\()
// scan-asm-not: \bvprefetch(?:2|nta|e[a-z0-9]*)\b
// A loop that fits in L1 gets no prefetch.
// scan-asm-loop-not l1_resident_f32: \bvprefetch
#include "knc-prefetch.h"
