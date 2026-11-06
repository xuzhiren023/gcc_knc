// S6-04: use the existing gather/scatter fixture and require target notes.
// options: -O3 -fopt-info-vec
// scan-output: KNC candidate.*gather [1-9][0-9]*
// scan-output: KNC candidate.*scatter [1-9][0-9]*
#include "knc-gather16-f32.c"
