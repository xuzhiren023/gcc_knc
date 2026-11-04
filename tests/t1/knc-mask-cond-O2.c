// S4-03 / ADR-0007: selects, min/max, fabs and conditional loads/stores
// vectorize into IMCI compares, k-register logic, blends and 64-byte aligned
// masked moves guarded against an empty mask.  fmin/fmax stay scalar: libm
// returns its first argument for opposite zeros, vgminps/vgmaxps do not.
// options: -O2 -ftree-vectorize
// scan-asm-func sel_f32: \bvcmpps\s+\$1,[^\n]*%k[0-7]\s*$
// scan-asm-func sel_f32: \bvmovaps\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func sel_f64: \bvcmppd\s+\$1,[^\n]*%k[0-7]\s*$
// scan-asm-func sel_f64: \bvmovapd\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func sel_i32: \bvpcmpd\s+\$6,[^\n]*%k[0-7]\s*$
// scan-asm-func sel_i32: \bvmovdqa32\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func minx_f32: \bvcmpps\s+\$1,[^\n]*%k[0-7]\s*$
// scan-asm-func minx_f32: \bvblendmps\s[^\n]*\{%k[1-7]\}
// scan-asm-func minx_f64: \bvcmppd\s+\$1,[^\n]*%k[0-7]\s*$
// scan-asm-func minx_f64: \bvblendmpd\s[^\n]*\{%k[1-7]\}
// scan-asm-func min_i32: \bvpminsd\s[^\n]*%zmm
// scan-asm-func max_i32: \bvpmaxsd\s[^\n]*%zmm
// scan-asm-func min_u32: \bvpminud\s[^\n]*%zmm
// scan-asm-func max_u32: \bvpmaxud\s[^\n]*%zmm
// scan-asm-func abs_f32: \bvpandd\s[^\n]*%zmm
// scan-asm-func abs_f64: \bvpandq\s[^\n]*%zmm
// scan-asm-func fmin_f32: \bcall\s+fminf\b
// scan-asm-func fmin_f32: \A(?![\s\S]*\bv(?:gmin|cmpp))
// scan-asm-func fmax_f64: \bcall\s+fmax\b
// scan-asm-func fmax_f64: \A(?![\s\S]*\bv(?:gmax|cmpp))
// scan-asm-func cst_f32: \bjkzd\s+\S+,\s*%k[0-7]\s*$
// scan-asm-func cst_f32: \bvmovaps\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func cst_f32: \bvmovaps\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func cst_f32: \A(?![\s\S]*\b(?:vloadunpack|vpackstore)\w*\s[^\n]*\{%k)
// scan-asm-func cst_f64: \bvmovapd\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func cst_f64: \bvmovapd\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func cst_f64: \A(?![\s\S]*\b(?:vloadunpack|vpackstore)\w*\s[^\n]*\{%k)
// scan-asm-func cst_i32: \bjkzd\s+\S+,\s*%k[0-7]\s*$
// scan-asm-func cst_i32: \bvmovdqa32\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func cst_i32: \bvmovdqa32\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func cst_ptr_f32: \A(?![\s\S]*\bv(?:cmpps|movaps|blendmps)\b)
// scan-asm-func cadd_f32: \bvaddps\s[^\n]*\{%k[1-7]\}
// scan-asm-func cadd_f32: \bvmovaps\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func cadd_i32: \bvpaddd\s[^\n]*%zmm
// scan-asm-func cadd_i32: \bvmovdqa32\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func and_i32: \bk(?:and|or)\s+%k[0-7],\s*%k[0-7]\s*$
// scan-asm-func and_i32: \A(?![\s\S]*\bkmov\s+%k[0-7],\s*%(?:e[a-z]+|r\d+d)\s*$)
// scan-asm-func or_f32: \bk(?:or|and)\s+%k[0-7],\s*%k[0-7]\s*$
// scan-asm-func or_f32: \A(?![\s\S]*\bkmov\s+%k[0-7],\s*%(?:e[a-z]+|r\d+d)\s*$)
// scan-asm-func xor_f32: \bkx(?:or|nor)\s+%k[0-7],\s*%k[0-7]\s*$
// scan-asm-func xor_f32: \A(?![\s\S]*\bkmov\s+%k[0-7],\s*%(?:e[a-z]+|r\d+d)\s*$)
// scan-asm-func andnot_f64: \bknot\s+%k[0-7],\s*%k[0-7]\s*$
// scan-asm-func andnot_f64: \bkand\s+%k[0-7],\s*%k[0-7]\s*$
// scan-asm-func andnot_f64: \A(?![\s\S]*\bkmov\s+%k[0-7],\s*%(?:e[a-z]+|r\d+d)\s*$)
// scan-asm-not: %(?:xmm|ymm)\d
#include "knc-mask-cond.h"
