/* Generated from the accepted G0 receipt; source interfaces only. */
#ifndef KNC_MVEC_ABI_H
#define KNC_MVEC_ABI_H

#if !defined(__GNUC__) || !defined(__STDC_VERSION__) || __STDC_VERSION__ < 201112L
#error "libknc_mvec scaffold requires GCC vector extensions and C11"
#endif

typedef float knc_mvec_f32x4 __attribute__((vector_size(16)));
_Static_assert(sizeof(knc_mvec_f32x4) == 16, "vector size mismatch");
typedef float knc_mvec_f32x8 __attribute__((vector_size(32)));
_Static_assert(sizeof(knc_mvec_f32x8) == 32, "vector size mismatch");
typedef float knc_mvec_f32x16 __attribute__((vector_size(64)));
_Static_assert(sizeof(knc_mvec_f32x16) == 64, "vector size mismatch");
typedef double knc_mvec_f64x2 __attribute__((vector_size(16)));
_Static_assert(sizeof(knc_mvec_f64x2) == 16, "vector size mismatch");
typedef double knc_mvec_f64x4 __attribute__((vector_size(32)));
_Static_assert(sizeof(knc_mvec_f64x4) == 32, "vector size mismatch");
typedef double knc_mvec_f64x8 __attribute__((vector_size(64)));
_Static_assert(sizeof(knc_mvec_f64x8) == 64, "vector size mismatch");

/* Declarations do not establish KNC ABI/numerical qualification. */
/* declaration-only; verified=false */
knc_mvec_f64x2 __knc_vmath_cos_2(knc_mvec_f64x2 x0);
/* narrow-wrapper-source-only; verified=false */
knc_mvec_f64x2 __knc_vmath_exp_2(knc_mvec_f64x2 x0);
/* declaration-only; verified=false */
knc_mvec_f64x2 __knc_vmath_log10_2(knc_mvec_f64x2 x0);
/* declaration-only; verified=false */
knc_mvec_f64x2 __knc_vmath_pow_2(knc_mvec_f64x2 x0, knc_mvec_f64x2 x1);
/* narrow-wrapper-source-only; verified=false */
knc_mvec_f32x4 __knc_vmath_expf_4(knc_mvec_f32x4 x0);
/* declaration-only; verified=false */
knc_mvec_f32x4 __knc_vmath_log10f_4(knc_mvec_f32x4 x0);
/* narrow-wrapper-source-only; verified=false */
knc_mvec_f32x4 __knc_vmath_logf_4(knc_mvec_f32x4 x0);
/* declaration-only; verified=false */
knc_mvec_f32x4 __knc_vmath_powf_4(knc_mvec_f32x4 x0, knc_mvec_f32x4 x1);
/* narrow-wrapper-source-only; verified=false */
knc_mvec_f64x4 __knc_vmath_exp_4(knc_mvec_f64x4 x0);
/* declaration-only; verified=false */
knc_mvec_f64x4 __knc_vmath_pow_4(knc_mvec_f64x4 x0, knc_mvec_f64x4 x1);
/* narrow-wrapper-source-only; verified=false */
knc_mvec_f32x8 __knc_vmath_expf_8(knc_mvec_f32x8 x0);
/* narrow-wrapper-source-only; verified=false */
knc_mvec_f32x8 __knc_vmath_logf_8(knc_mvec_f32x8 x0);
/* declaration-only; verified=false */
knc_mvec_f32x8 __knc_vmath_powf_8(knc_mvec_f32x8 x0, knc_mvec_f32x8 x1);
/* declaration-only; verified=false */
knc_mvec_f32x16 __knc_vmath_atanf_16(knc_mvec_f32x16 x0);
/* declaration-only; verified=false */
knc_mvec_f32x16 __knc_vmath_cosf_16(knc_mvec_f32x16 x0);
/* declaration-only; verified=false */
knc_mvec_f32x16 __knc_vmath_coshf_16(knc_mvec_f32x16 x0);
/* undefined-full-width-kernel; verified=false */
knc_mvec_f32x16 __knc_vmath_expf_16(knc_mvec_f32x16 x0);
/* declaration-only; verified=false */
knc_mvec_f32x16 __knc_vmath_log10f_16(knc_mvec_f32x16 x0);
/* undefined-full-width-kernel; verified=false */
knc_mvec_f32x16 __knc_vmath_logf_16(knc_mvec_f32x16 x0);
/* declaration-only; verified=false */
knc_mvec_f32x16 __knc_vmath_sinf_16(knc_mvec_f32x16 x0);
/* declaration-only; verified=false */
knc_mvec_f32x16 __knc_vmath_sinhf_16(knc_mvec_f32x16 x0);
/* declaration-only; verified=false */
knc_mvec_f32x16 __knc_vmath_tanf_16(knc_mvec_f32x16 x0);
/* declaration-only; verified=false */
knc_mvec_f32x16 __knc_vmath_tanhf_16(knc_mvec_f32x16 x0);
/* declaration-only; verified=false */
knc_mvec_f32x16 __knc_vmath_atan2f_16(knc_mvec_f32x16 x0, knc_mvec_f32x16 x1);
/* declaration-only; verified=false */
knc_mvec_f32x16 __knc_vmath_powf_16(knc_mvec_f32x16 x0, knc_mvec_f32x16 x1);
/* declaration-only; verified=false */
knc_mvec_f64x8 __knc_vmath_cos_8(knc_mvec_f64x8 x0);
/* declaration-only; verified=false */
knc_mvec_f64x8 __knc_vmath_cosh_8(knc_mvec_f64x8 x0);
/* undefined-full-width-kernel; verified=false */
knc_mvec_f64x8 __knc_vmath_exp_8(knc_mvec_f64x8 x0);
/* undefined-full-width-kernel; verified=false */
knc_mvec_f64x8 __knc_vmath_log_8(knc_mvec_f64x8 x0);
/* declaration-only; verified=false */
knc_mvec_f64x8 __knc_vmath_log10_8(knc_mvec_f64x8 x0);
/* declaration-only; verified=false */
knc_mvec_f64x8 __knc_vmath_sin_8(knc_mvec_f64x8 x0);
/* declaration-only; verified=false */
knc_mvec_f64x8 __knc_vmath_sinh_8(knc_mvec_f64x8 x0);
/* declaration-only; verified=false */
knc_mvec_f64x8 __knc_vmath_tan_8(knc_mvec_f64x8 x0);
/* declaration-only; verified=false */
knc_mvec_f64x8 __knc_vmath_tanh_8(knc_mvec_f64x8 x0);
/* declaration-only; verified=false */
knc_mvec_f64x8 __knc_vmath_atan2_8(knc_mvec_f64x8 x0, knc_mvec_f64x8 x1);
/* declaration-only; verified=false */
knc_mvec_f64x8 __knc_vmath_pow_8(knc_mvec_f64x8 x0, knc_mvec_f64x8 x1);

#endif /* KNC_MVEC_ABI_H */
