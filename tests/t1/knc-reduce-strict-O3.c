// S5-07 / ADR-0008 point 2: -O3 alone must not reassociate.
// options: -O3
// scan-asm-not: \bvaddp[sd]\b
// scan-asm-func sum_f32: \bfadds\b
// scan-asm-func sum_f64: \bfaddl\b
#include "knc-reduce-fp.h"
