/* libknc_vmath v0: pointer-form cores of the copied vector math (ADR-0011, ADR-0014 point 3).

   Each core reads LANES input words (bit patterns of float or double), computes the active lanes
   (bit i of ACTIVE), copies the inactive lanes from MERGE, and writes OUT. It returns nonzero only
   for an ACTIVE bit above LANES. Round to nearest, IEEE special values; errno is never set.

   The by-value entry points __knc_vmath_<name>_<lanes> compute every lane through these cores.
   Loops compiled with -mveclibabi=knc (the -march=knc default) call them; their 64-byte vector
   arguments and results travel in zmm (ADR-0014 points 1-2). */
#ifndef KNC_VMATH_H
#define KNC_VMATH_H
#include <stdint.h>

#ifdef __FAST_MATH__
#error "libknc_vmath is built without fast-math (ADR-0014 point 4)"
#endif

int __knc_vmath_core_expf_16(const uint32_t in[16], unsigned active, const uint32_t merge[16],
                             uint32_t out[16]);
int __knc_vmath_core_logf_16(const uint32_t in[16], unsigned active, const uint32_t merge[16],
                             uint32_t out[16]);
int __knc_vmath_core_powf_16(const uint32_t x[16], const uint32_t y[16], unsigned active,
                             const uint32_t merge[16], uint32_t out[16]);
int __knc_vmath_core_exp_8(const uint64_t in[8], unsigned active, const uint64_t merge[8],
                           uint64_t out[8]);
int __knc_vmath_core_log_8(const uint64_t in[8], unsigned active, const uint64_t merge[8],
                           uint64_t out[8]);
int __knc_vmath_core_pow_8(const uint64_t x[8], const uint64_t y[8], unsigned active,
                           const uint64_t merge[8], uint64_t out[8]);

typedef float __knc_vmath_v16sf __attribute__((vector_size(64)));
typedef double __knc_vmath_v8df __attribute__((vector_size(64)));

__knc_vmath_v16sf __knc_vmath_expf_16(__knc_vmath_v16sf x);
__knc_vmath_v16sf __knc_vmath_logf_16(__knc_vmath_v16sf x);
__knc_vmath_v16sf __knc_vmath_powf_16(__knc_vmath_v16sf x, __knc_vmath_v16sf y);
__knc_vmath_v8df __knc_vmath_exp_8(__knc_vmath_v8df x);
__knc_vmath_v8df __knc_vmath_log_8(__knc_vmath_v8df x);
__knc_vmath_v8df __knc_vmath_pow_8(__knc_vmath_v8df x, __knc_vmath_v8df y);

/* v1a (S10-07): the other copied algorithms. The 8-lane atan is missing because the copy has
   none. Their cores stay inside their members. Each entry point has a masked form (ADR-0014
   point 4): bit i of MASK set computes lane i; a clear bit returns lane i of the first argument
   unchanged, and whatever that lane holds raises no exception. */
#define KNC_VMATH_DECLARE1(name, lanes, vector) \
  vector __knc_vmath_##name##_##lanes(vector x); \
  vector __knc_vmath_##name##_##lanes##_m(vector x, unsigned mask);
#define KNC_VMATH_DECLARE2(name, lanes, vector) \
  vector __knc_vmath_##name##_##lanes(vector y, vector x); \
  vector __knc_vmath_##name##_##lanes##_m(vector y, vector x, unsigned mask);
KNC_VMATH_DECLARE1(sinf, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(cosf, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(tanf, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(log10f, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(atanf, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE2(atan2f, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(sinhf, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(coshf, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(tanhf, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(sin, 8, __knc_vmath_v8df)
KNC_VMATH_DECLARE1(cos, 8, __knc_vmath_v8df)
KNC_VMATH_DECLARE1(tan, 8, __knc_vmath_v8df)
KNC_VMATH_DECLARE1(log10, 8, __knc_vmath_v8df)
KNC_VMATH_DECLARE2(atan2, 8, __knc_vmath_v8df)
KNC_VMATH_DECLARE1(sinh, 8, __knc_vmath_v8df)
KNC_VMATH_DECLARE1(cosh, 8, __knc_vmath_v8df)
KNC_VMATH_DECLARE1(tanh, 8, __knc_vmath_v8df)

/* v1b (S10-08): the rest of glibc's libmvec set, written for this library after Arm's
   optimized-routines (README.md). hypot's masked form returns lane i of x where bit i is clear.
   sincos has no entry point: the compiler calls the sin and cos above. */
KNC_VMATH_DECLARE1(acosf, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(asinf, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(cbrtf, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(erff, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(erfcf, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(exp2f, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(exp10f, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(expm1f, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(log1pf, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(log2f, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE2(hypotf, 16, __knc_vmath_v16sf)
KNC_VMATH_DECLARE1(acos, 8, __knc_vmath_v8df)
KNC_VMATH_DECLARE1(asin, 8, __knc_vmath_v8df)
KNC_VMATH_DECLARE1(cbrt, 8, __knc_vmath_v8df)
KNC_VMATH_DECLARE1(erf, 8, __knc_vmath_v8df)
KNC_VMATH_DECLARE1(erfc, 8, __knc_vmath_v8df)
KNC_VMATH_DECLARE1(exp2, 8, __knc_vmath_v8df)
KNC_VMATH_DECLARE1(exp10, 8, __knc_vmath_v8df)
KNC_VMATH_DECLARE1(expm1, 8, __knc_vmath_v8df)
KNC_VMATH_DECLARE1(log1p, 8, __knc_vmath_v8df)
KNC_VMATH_DECLARE1(log2, 8, __knc_vmath_v8df)
KNC_VMATH_DECLARE2(hypot, 8, __knc_vmath_v8df)
#endif
