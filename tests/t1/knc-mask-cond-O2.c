// S4-03 / ADR-0007: selects, min/max, fabs and conditional loads/stores
// vectorize into IMCI compares, blends and 64-byte aligned
// masked moves guarded against an empty mask.  S5-15 / ADR-0008 point 3:
// fmin/fmax use vgminps/vgmaxpd; either zero sign is permitted.
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
// scan-asm-func fmin_f32: \bvgminps\s[^\n]*%zmm
// scan-asm-func fmax_f64: \bvgmaxpd\s[^\n]*%zmm
// x[i] is in bounds of a global array, so if-conversion loads it
// unconditionally (aligned); sel_* covers the masked load.
// scan-asm-func cst_f32: \bjkzd\s+\S+,\s*%k[0-7]\s*$
// scan-asm-func cst_f32: \bvmovaps\s+x_f32\(%\w+\),\s*%zmm\d+\s*$
// scan-asm-func cst_f32: \bvmovaps\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func cst_f32: \A(?![\s\S]*\b(?:vloadunpack|vpackstore)\w*\s[^\n]*\{%k)
// scan-asm-func cst_f64: \bvmovapd\s+x_f64\(%\w+\),\s*%zmm\d+\s*$
// scan-asm-func cst_f64: \bvmovapd\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func cst_f64: \A(?![\s\S]*\b(?:vloadunpack|vpackstore)\w*\s[^\n]*\{%k)
// scan-asm-func cst_i32: \bjkzd\s+\S+,\s*%k[0-7]\s*$
// scan-asm-func cst_i32: \bvmovdqa32\s+x_i32\(%\w+\),\s*%zmm\d+\s*$
// scan-asm-func cst_i32: \bvmovdqa32\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// cst_ptr_f32 stores through pointers of unknown alignment: since S8-02
// (ADR-0009 amendment 1 point 9) its masked accesses are a gather and a
// scatter under the compare mask, never the S4-14 split or an x87 loop.
// scan-asm-func cst_ptr_f32: \bvcmpps\s+\$1,[^\n]*%k[0-7]\s*$
// scan-asm-func cst_ptr_f32: \bvgatherdps\s+[^\n]*\{%k[1-7]\}
// scan-asm-func cst_ptr_f32: \bvscatterdps\s+%zmm\d+,\s*[^\n]*\{%k[1-7]\}
// scan-asm-func cst_ptr_f32: \A(?![\s\S]*\bvpermd\s)
// scan-asm-func cst_ptr_f32: \A(?![\s\S]*\bfld)
// scan-asm-func cadd_f32: \bvaddps\s[^\n]*\{%k[1-7]\}
// scan-asm-func cadd_f32: \bvmovaps\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func cadd_i32: \bvpaddd\s[^\n]*%zmm
// scan-asm-func cadd_i32: \bvmovdqa32\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-not: %(?:xmm|ymm)\d
#include "knc-mask-cond.h"
