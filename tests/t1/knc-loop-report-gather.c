// S6-04: use the existing gather/scatter fixture and require target notes.
// options: -O3 -fopt-info-vec
// scan-output: KNC candidate.*gather
// scan-output: KNC candidate.*scatter
#include "knc-gather16-f32.c"
