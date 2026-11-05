// S5-06 / ADR-0008 point 1: KNC vec_perm_const lets reversed, stride-2 and
// complex loops vectorize.  A reversal is one vpermd with a hoisted index
// for every mode; a stride-2 load extracts even and odd lanes with vpermd
// plus a write-masked vpermd; swapping re and im is a register swizzle.
// KNC has no vpermt2, vpermq or 128/256-bit registers.
// options: -O3
// scan-asm-func rev_f32: \bvpermd\s
// scan-asm-func rev_f64: \bvpermd\s
// scan-asm-func rev_i32: \bvpermd\s
// scan-asm-func rev_i64: \bvpermd\s
// scan-asm-func sum2_f32: \bvpermd\s+[^\n]*\{%k[1-7]\}
// scan-asm-func sum2_f64: \bvpermd\s+[^\n]*\{%k[1-7]\}
// scan-asm-func cswap_f32: \bvmovdqa32\s+%zmm\d+\{cdab\}
// scan-asm-func cswap_f32: \A(?![\s\S]*\bvpermd\s)
// scan-asm-func cswap_f64: \bvmovdqa64\s+%zmm\d+\{cdab\}
// scan-asm-func cswap_f64: \A(?![\s\S]*\bvpermd\s)
// scan-asm-func cmul_f32: %zmm\d+\{cdab\}|\bvpermd\s
// scan-asm-not: \bvpermt2|\bvpermq\b|%(?:xmm|ymm)\d
#define R __restrict
#define REV(T, S)                                                         \
  void rev_##S (T *R c, const T *R a, int n)                              \
  { for (int i = 0; i < n; i++) c[i] = a[n - 1 - i]; }
REV (float, f32) REV (double, f64) REV (int, i32) REV (long, i64)

#define SUM2(T, S)                                                        \
  void sum2_##S (T *R c, const T *R b, int n)                             \
  { for (int i = 0; i < n; i++) c[i] = b[2 * i] + b[2 * i + 1]; }
SUM2 (float, f32) SUM2 (double, f64)

#define CSWAP(T, S)                                                       \
  void cswap_##S (T *R c, const T *R a, int n)                            \
  {                                                                       \
    for (int i = 0; i < n; i++)                                           \
      {                                                                   \
        c[2 * i] = a[2 * i + 1];                                          \
        c[2 * i + 1] = a[2 * i];                                          \
      }                                                                   \
  }
CSWAP (float, f32) CSWAP (double, f64)

void cmul_f32 (float *R c, const float *R a, const float *R b, int n)
{
  for (int i = 0; i < n; i++)
    {
      c[2 * i] = a[2 * i] * b[2 * i] - a[2 * i + 1] * b[2 * i + 1];
      c[2 * i + 1] = a[2 * i] * b[2 * i + 1] + a[2 * i + 1] * b[2 * i];
    }
}
