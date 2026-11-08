// S6-04: exercise the actual M1 affine fixture without changing acceptance.
// options: -O3 -fopt-info-vec
// scan-output: KNC candidate.*V16SF.*factor = 16
// scan-output: KNC candidate.*V8DF.*factor = 8
// S8-02: unknown alignment now takes the gather/scatter masked epilogue.
// scan-output: KNC candidate.*masked epilogue eligible: alignment unknown
#include "../acceptance/m1_affine/loops.c"
