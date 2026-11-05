// S5-07 / ADR-0008 point 2: keep GCC's in-order x87 fold.
// options: -O2 -ftree-vectorize
// scan-asm-not: \bvaddp[sd]\b
// scan-asm-func sum_f32: \bfadds\b
// scan-asm-func sum_f64: \bfaddl\b
#include "knc-reduce-fp.h"
