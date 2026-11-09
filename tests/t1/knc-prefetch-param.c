// S8-03: one documented --param per distance, in lines.  L1 8 / L2 64 gives
// 512- and 4096-byte displacements; eight streams at 8 x 8 x 4 = 256 lines
// still exceed the L1 quarter, so row8_f32 halves to 4 lines (256 bytes).
// options: -O2 -ffp-contract=off --param=knc-prefetch-l1-distance=8 --param=knc-prefetch-l2-distance=64
// scan-asm-func stream_f32: \bvprefetch0\s+512\(
// scan-asm-func stream_f32: \bvprefetch1\s+4096\(
// scan-asm-func row8_f32: \bvprefetch0\s+256\(
// scan-asm-func row8_f32: \bvprefetch1\s+4096\(
// scan-asm-not: \bvprefetch0\s+(?!(?:256|504|508|512|516|520)\()
// scan-asm-not: \bvprefetch1\s+(?!(?:4088|4092|4096|4100|4104)\()
#include "knc-prefetch.h"
