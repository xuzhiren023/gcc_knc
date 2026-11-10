// S8-19: -mtune=knc clears X86_TUNE_ALIGN_TIGHT_LOOPS.  The pass serves the
// decoded-icache rules of big cores, which KNC lacks (lead card 2026-11-10:
// 56 nops per outer trip in m2_mat8, 1.105x slower).
// options: -O2 -march=knc
// scan-asm-not: ^\s*\.p2align\s+[56]\s*\n(?:\s*\.p2align.*\n)*\.L\w+:
#include "knc-tune-tight-loops.h"
