// S6-04: exercise the actual M1 affine fixture without changing acceptance.
// options: -O3 -fopt-info-vec
// scan-output: KNC candidate.*V16SF.*factor[ =:] +16
// scan-output: KNC candidate.*V8DF.*factor[ =:] +8
// scan-output: KNC candidate.*scalar epilogue.*alignment
#include "../acceptance/m1_affine/loops.c"
