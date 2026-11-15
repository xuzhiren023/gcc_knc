// S12-22 B10: L1=8 and L2=4 clamp the near hint to three lines.
// The S8-03 runner also compiles this file with L2=1 and requires rejection.
// options: -O2 -ffp-contract=off --param=knc-prefetch-l1-distance=8 --param=knc-prefetch-l2-distance=4
// scan-asm-func stream_f32: \bvprefetch0\s+192\(
// scan-asm-func stream_f32: \bvprefetch1\s+256\(
#include "knc-prefetch.h"
