/* Source-only narrow unmasked vector ABI wrappers. No math implementation.
 * The four full-width _ZGVe... kernels are intentionally undefined here.
 * This file must eventually pass through the qualified C translation pipeline.
 */
#include "knc_mvec_abi.h"

#define NARROW_F32(NAME, TYPE, LANES, KERNEL, NEUTRAL) \
TYPE NAME(TYPE x) { \
    knc_mvec_f32x16 wide; \
    for (unsigned i = 0; i < 16; ++i) wide[i] = (NEUTRAL); \
    for (unsigned i = 0; i < (LANES); ++i) wide[i] = x[i]; \
    const knc_mvec_f32x16 value = KERNEL(wide); \
    TYPE result; \
    for (unsigned i = 0; i < (LANES); ++i) result[i] = value[i]; \
    return result; \
}

#define NARROW_F64(NAME, TYPE, LANES, KERNEL, NEUTRAL) \
TYPE NAME(TYPE x) { \
    knc_mvec_f64x8 wide; \
    for (unsigned i = 0; i < 8; ++i) wide[i] = (NEUTRAL); \
    for (unsigned i = 0; i < (LANES); ++i) wide[i] = x[i]; \
    const knc_mvec_f64x8 value = KERNEL(wide); \
    TYPE result; \
    for (unsigned i = 0; i < (LANES); ++i) result[i] = value[i]; \
    return result; \
}

NARROW_F32(__knc_vmath_expf_4, knc_mvec_f32x4, 4, __knc_vmath_expf_16, 0.0f)
NARROW_F32(__knc_vmath_expf_8, knc_mvec_f32x8, 8, __knc_vmath_expf_16, 0.0f)
NARROW_F32(__knc_vmath_logf_4, knc_mvec_f32x4, 4, __knc_vmath_logf_16, 1.0f)
NARROW_F32(__knc_vmath_logf_8, knc_mvec_f32x8, 8, __knc_vmath_logf_16, 1.0f)
NARROW_F64(__knc_vmath_exp_2, knc_mvec_f64x2, 2, __knc_vmath_exp_8, 0.0)
NARROW_F64(__knc_vmath_exp_4, knc_mvec_f64x4, 4, __knc_vmath_exp_8, 0.0)

/* No observed b/d double-log symbol exists in this G0 scope. */
#undef NARROW_F32
#undef NARROW_F64
