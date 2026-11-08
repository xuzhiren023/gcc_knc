// S8-03: the L1 footprint rule scales with knc-threads-per-core.  At one
// thread per core eight streams at 16 lines use 128 lines, a quarter of L1,
// so row8_f32 keeps the full L1 distance; the L2 distance never changes
// (C5: 32 lines best at 2 and 4 threads, S8-12 rerun).
// options: -O2 -ffp-contract=off --param=knc-threads-per-core=1
// scan-asm-func stream_f32: \bvprefetch0\s+1024\(
// scan-asm-func stream_f32: \bvprefetch1\s+2048\(
// scan-asm-func row8_f32: \bvprefetch0\s+1024\(
// scan-asm-func row8_f32: \bvprefetch1\s+2048\(
// scan-asm-not: \bvprefetch0\s+(?!(?:1020|1024|1028)\()
// scan-asm-not: \bvprefetch1\s+(?!(?:2044|2048|2052)\()
#include "knc-prefetch.h"
