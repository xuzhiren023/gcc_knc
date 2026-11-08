// S4-14 / ADR-0007 point 7, superseded form by S8-02 / ADR-0009 amendment 1
// point 9: a conditional load or store through a pointer of unknown
// alignment is a gather or scatter (lane index iota, scale = element
// size) under the lane mask, not one GPR move per lane, not a masked
// unpack/pack pair and no longer the S4-14 split (two aligned masked
// moves behind GPR tests and a vpermd rotation).  A gather or scatter
// touches only the lines that hold active elements, which the scalar
// loop accesses too, so the S4-14 guard-page tests still hold.  The
// retry loop (jknzd) belongs to the gather/scatter instruction.  8-lane
// masks are never tested with jkzd (bits 15:8 of a QI mask are undefined),
// and their gathers run with bits 15:8 cleared through a GPR.
// options: -O2 -ftree-vectorize -fvect-cost-model=unlimited --param vect-max-peeling-for-alignment=0
// scan-asm-func cst_f32: \bvgatherdps\s+[^\n]*\{%k[1-7]\}
// scan-asm-func cst_f32: \bvscatterdps\s+%zmm\d+,\s*[^\n]*\{%k[1-7]\}
// scan-asm-func cst_f32: \bjknzd\s
// scan-asm-func cst_f32: \A(?![\s\S]*\bvpermd\s)
// scan-asm-func cst_f32: \A(?![\s\S]*\bv(?:loadunpack|packstore)\w*\s[^\n]*\{%k)
// scan-asm-func cst_f32: \A(?![\s\S]*\bvmovaps\s+[^\n]*\{%k)
// scan-asm-func cst_f64: \bvgatherdpd\s+[^\n]*\{%k[1-7]\}
// scan-asm-func cst_f64: \bvscatterdpd\s+%zmm\d+,\s*[^\n]*\{%k[1-7]\}
// scan-asm-func cst_f64: \A(?![\s\S]*\bvpermd\s)
// scan-asm-func cst_f64: \A(?![\s\S]*\bv(?:loadunpack|packstore)\w*\s[^\n]*\{%k)
// scan-asm-func cst_f64: \A(?![\s\S]*\bjkn?zd)
// scan-asm-func cst_i32: \bvpgatherdd\s+[^\n]*\{%k[1-7]\}
// scan-asm-func cst_i32: \bvpscatterdd\s+%zmm\d+,\s*[^\n]*\{%k[1-7]\}
// scan-asm-func cst_i32: \A(?![\s\S]*\bvpermd\s)
// scan-asm-func cst_i32: \A(?![\s\S]*\bv(?:loadunpack|packstore)\w*\s[^\n]*\{%k)
// scan-asm-func cst_i64: \bvpgatherdq\s+[^\n]*\{%k[1-7]\}
// scan-asm-func cst_i64: \bvpscatterdq\s+%zmm\d+,\s*[^\n]*\{%k[1-7]\}
// scan-asm-func cst_i64: \A(?![\s\S]*\bvpermd\s)
// scan-asm-func cst_i64: \A(?![\s\S]*\bv(?:loadunpack|packstore)\w*\s[^\n]*\{%k)
// scan-asm-func cst_i64: \A(?![\s\S]*\bjkn?zd)
// scan-asm-not: %(?:xmm|ymm)\d
/* x[i] is a conditional load and c[i] a conditional store; with peeling
   disabled both stay misaligned in the vector loop.  */
#define LOOP for (int i = 0; i < n; i++)
#define CST(T, C, S)                                                      \
  void cst_##S (T *restrict c, const C *restrict a, const T *restrict x,  \
                int n)                                                    \
  { LOOP if (a[i] > 0) c[i] = x[i]; }
CST (float, float, f32) CST (double, double, f64) CST (int, int, i32)
CST (long, double, i64)
