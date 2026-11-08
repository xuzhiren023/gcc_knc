// S8-03: the same defaults hold at -O3 (knc-prefetch-O2.c has the rules).
// options: -O3 -ffp-contract=off
// scan-asm-func stream_f32: \bvprefetch0\s+1024\(
// scan-asm-func stream_f32: \bvprefetch1\s+2048\(
// scan-asm-func stencil_f32: \bvprefetch0\s+10(?:20|24|28)\(
// scan-asm-func stencil_f32: \bvprefetch1\s+20(?:44|48|52)\(
// scan-asm-func row8_f32: \bvprefetch0\s+512\(
// scan-asm-func row8_f32: \bvprefetch1\s+2048\(
// scan-asm-not: \bvprefetch0\s+(?!(?:512|1020|1024|1028)\()
// scan-asm-not: \bvprefetch1\s+(?!(?:2044|2048|2052)\()
// scan-asm-loop-not l1_resident_f32: \bvprefetch
#include "knc-prefetch.h"
