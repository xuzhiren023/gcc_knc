// S10-07 / ADR-0014 point 2: vector math v1a.  A loop of each function whose
// algorithm is copied (ADR-0011) calls its libknc_vmath entry point: sin, cos,
// tan, log10, atan2, sinh, cosh and tanh on 16 floats and on 8 doubles, and
// atanf on 16 floats.  The copy has no 8-lane atan, so a double atan loop
// keeps its scalar call.
// options: -O2 -march=knc -fno-math-errno
// scan-asm-func vmath_sinf: \bcall\s+__knc_vmath_sinf_16\b
// scan-asm-func vmath_cosf: \bcall\s+__knc_vmath_cosf_16\b
// scan-asm-func vmath_tanf: \bcall\s+__knc_vmath_tanf_16\b
// scan-asm-func vmath_log10f: \bcall\s+__knc_vmath_log10f_16\b
// scan-asm-func vmath_sinhf: \bcall\s+__knc_vmath_sinhf_16\b
// scan-asm-func vmath_coshf: \bcall\s+__knc_vmath_coshf_16\b
// scan-asm-func vmath_tanhf: \bcall\s+__knc_vmath_tanhf_16\b
// scan-asm-func vmath_atanf: \bcall\s+__knc_vmath_atanf_16\b
// scan-asm-func vmath_atan2f: \bcall\s+__knc_vmath_atan2f_16\b
// scan-asm-func vmath_sin: \bcall\s+__knc_vmath_sin_8\b
// scan-asm-func vmath_cos: \bcall\s+__knc_vmath_cos_8\b
// scan-asm-func vmath_tan: \bcall\s+__knc_vmath_tan_8\b
// scan-asm-func vmath_log10: \bcall\s+__knc_vmath_log10_8\b
// scan-asm-func vmath_sinh: \bcall\s+__knc_vmath_sinh_8\b
// scan-asm-func vmath_cosh: \bcall\s+__knc_vmath_cosh_8\b
// scan-asm-func vmath_tanh: \bcall\s+__knc_vmath_tanh_8\b
// scan-asm-func vmath_atan2: \bcall\s+__knc_vmath_atan2_8\b
// scan-asm-func vmath_atan: \bcall\s+atan\b
// scan-asm-not: __knc_vmath_atan_8
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
  vmath_##name (type *restrict out, const type *restrict y, \
		const type *restrict x, int n) \
  { \
    for (int i = 0; i < n; i++) \
      out[i] = name (y[i], x[i]); \
  }

LOOP1 (sinf, float)
LOOP1 (cosf, float)
LOOP1 (tanf, float)
LOOP1 (log10f, float)
LOOP1 (sinhf, float)
LOOP1 (coshf, float)
LOOP1 (tanhf, float)
LOOP1 (atanf, float)
LOOP2 (atan2f, float)
LOOP1 (sin, double)
LOOP1 (cos, double)
LOOP1 (tan, double)
LOOP1 (log10, double)
LOOP1 (sinh, double)
LOOP1 (cosh, double)
LOOP1 (tanh, double)
LOOP1 (atan, double)
LOOP2 (atan2, double)
