// S10-08 / ADR-0014 point 2: vector math v1b, the rest of glibc's libmvec
// set.  A loop of acos, asin, cbrt, erf, erfc, exp2, exp10, expm1, log1p,
// log2 or hypot calls its libknc_vmath entry point on 16 floats and on 8
// doubles.  sincos has no entry point of its own: GCC turns the call into
// cexpi, and the vectorizer forms v1a's sin and cos pair from it (S10-07).
// options: -O2 -march=knc -fno-math-errno
// scan-asm-func vmath_acosf: \bcall\s+__knc_vmath_acosf_16\b
// scan-asm-func vmath_asinf: \bcall\s+__knc_vmath_asinf_16\b
// scan-asm-func vmath_cbrtf: \bcall\s+__knc_vmath_cbrtf_16\b
// scan-asm-func vmath_erff: \bcall\s+__knc_vmath_erff_16\b
// scan-asm-func vmath_erfcf: \bcall\s+__knc_vmath_erfcf_16\b
// scan-asm-func vmath_exp2f: \bcall\s+__knc_vmath_exp2f_16\b
// scan-asm-func vmath_exp10f: \bcall\s+__knc_vmath_exp10f_16\b
// scan-asm-func vmath_expm1f: \bcall\s+__knc_vmath_expm1f_16\b
// scan-asm-func vmath_log1pf: \bcall\s+__knc_vmath_log1pf_16\b
// scan-asm-func vmath_log2f: \bcall\s+__knc_vmath_log2f_16\b
// scan-asm-func vmath_hypotf: \bcall\s+__knc_vmath_hypotf_16\b
// scan-asm-func vmath_sincosf: \bcall\s+__knc_vmath_sinf_16\b
// scan-asm-func vmath_sincosf: \bcall\s+__knc_vmath_cosf_16\b
// scan-asm-func vmath_acos: \bcall\s+__knc_vmath_acos_8\b
// scan-asm-func vmath_asin: \bcall\s+__knc_vmath_asin_8\b
// scan-asm-func vmath_cbrt: \bcall\s+__knc_vmath_cbrt_8\b
// scan-asm-func vmath_erf: \bcall\s+__knc_vmath_erf_8\b
// scan-asm-func vmath_erfc: \bcall\s+__knc_vmath_erfc_8\b
// scan-asm-func vmath_exp2: \bcall\s+__knc_vmath_exp2_8\b
// scan-asm-func vmath_exp10: \bcall\s+__knc_vmath_exp10_8\b
// scan-asm-func vmath_expm1: \bcall\s+__knc_vmath_expm1_8\b
// scan-asm-func vmath_log1p: \bcall\s+__knc_vmath_log1p_8\b
// scan-asm-func vmath_log2: \bcall\s+__knc_vmath_log2_8\b
// scan-asm-func vmath_hypot: \bcall\s+__knc_vmath_hypot_8\b
// scan-asm-func vmath_sincos: \bcall\s+__knc_vmath_sin_8\b
// scan-asm-func vmath_sincos: \bcall\s+__knc_vmath_cos_8\b
#define _GNU_SOURCE
#include <math.h>

#define LOOP1(name, type) \
  void \
  vmath_##name (type *restrict out, const type *restrict in, int n) \
  { \
    for (int i = 0; i < n; i++) \
      out[i] = name (in[i]); \
  }

#define LOOP2(name, type) \
  void \
  vmath_##name (type *restrict out, const type *restrict x, \
		const type *restrict y, int n) \
  { \
    for (int i = 0; i < n; i++) \
      out[i] = name (x[i], y[i]); \
  }

#define SINCOS(name, type) \
  void \
  vmath_##name (type *restrict s, type *restrict c, \
		const type *restrict x, int n) \
  { \
    for (int i = 0; i < n; i++) \
      name (x[i], &s[i], &c[i]); \
  }

LOOP1 (acosf, float)
LOOP1 (asinf, float)
LOOP1 (cbrtf, float)
LOOP1 (erff, float)
LOOP1 (erfcf, float)
LOOP1 (exp2f, float)
LOOP1 (exp10f, float)
LOOP1 (expm1f, float)
LOOP1 (log1pf, float)
LOOP1 (log2f, float)
LOOP2 (hypotf, float)
SINCOS (sincosf, float)
LOOP1 (acos, double)
LOOP1 (asin, double)
LOOP1 (cbrt, double)
LOOP1 (erf, double)
LOOP1 (erfc, double)
LOOP1 (exp2, double)
LOOP1 (exp10, double)
LOOP1 (expm1, double)
LOOP1 (log1p, double)
LOOP1 (log2, double)
LOOP2 (hypot, double)
SINCOS (sincos, double)
