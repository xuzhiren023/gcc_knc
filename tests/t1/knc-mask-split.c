// S4-14 / ADR-0007 point 7: a conditional load or store through a pointer
// of unknown alignment is a guarded aligned split, not one GPR move per
// lane.  The two 64-byte lines the vector touches are each one aligned
// masked move, skipped by a GPR test (je/jz) when its share of the mask is
// empty, and one vpermd rotates the data.  8-lane masks are never tested
// with jkzd (bits 15:8 of a QI mask are undefined).
// options: -O2 -ftree-vectorize -fvect-cost-model=unlimited --param vect-max-peeling-for-alignment=0
// scan-asm-func cst_f32: \bvpermd\s[\s\S]*\bvpermd\s
// scan-asm-func cst_f32: \bvmovaps\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}[\s\S]*\bvmovaps\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func cst_f32: \bvmovaps\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}[\s\S]*\bvmovaps\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func cst_f32: \A(?![\s\S]*^(?!\s*j[ez]\s|\.L\d+:)(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:)[^\n]*\n(?:(?!(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:))[^\n]*\n)*\s*vmovaps\s[^\n]*\([^\n]*\{%k)
// scan-asm-func cst_f32: \A(?![\s\S]*\b(?:vloadunpack|vpackstore)\w*\s[^\n]*\{%k)
// scan-asm-func cst_f64: \bvpermd\s[\s\S]*\bvpermd\s
// scan-asm-func cst_f64: \bvmovapd\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}[\s\S]*\bvmovapd\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func cst_f64: \bvmovapd\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}[\s\S]*\bvmovapd\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func cst_f64: \A(?![\s\S]*^(?!\s*j[ez]\s|\.L\d+:)(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:)[^\n]*\n(?:(?!(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:))[^\n]*\n)*\s*vmovapd\s[^\n]*\([^\n]*\{%k)
// scan-asm-func cst_f64: \A(?![\s\S]*\bjkn?zd)
// scan-asm-func cst_i32: \bvpermd\s[\s\S]*\bvpermd\s
// scan-asm-func cst_i32: \bvmovdqa32\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}[\s\S]*\bvmovdqa32\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func cst_i32: \bvmovdqa32\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}[\s\S]*\bvmovdqa32\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func cst_i32: \A(?![\s\S]*^(?!\s*j[ez]\s|\.L\d+:)(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:)[^\n]*\n(?:(?!(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:))[^\n]*\n)*\s*vmovdqa32\s[^\n]*\([^\n]*\{%k)
// scan-asm-func cst_i64: \bvpermd\s[\s\S]*\bvpermd\s
// scan-asm-func cst_i64: \bvmovdqa64\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}[\s\S]*\bvmovdqa64\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func cst_i64: \bvmovdqa64\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}[\s\S]*\bvmovdqa64\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func cst_i64: \A(?![\s\S]*^(?!\s*j[ez]\s|\.L\d+:)(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:)[^\n]*\n(?:(?!(?:\s*(?:j\w+|ret\w*)\b|\.L\w+:))[^\n]*\n)*\s*vmovdqa64\s[^\n]*\([^\n]*\{%k)
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
