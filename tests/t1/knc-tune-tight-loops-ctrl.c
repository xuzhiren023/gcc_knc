// S8-19: -mtune-ctrl=align_tight_loops still wins over the -mtune=knc
// default, and brings the unbounded alignment back.
// options: -O2 -march=knc -mtune-ctrl=align_tight_loops
// scan-asm: ^\s*\.p2align\s+[56]\s*\n(?:\s*\.p2align.*\n)*\.L\w+:
#include "knc-tune-tight-loops.h"
