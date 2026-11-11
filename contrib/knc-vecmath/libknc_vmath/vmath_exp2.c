/* libknc_vmath: exp2, exp10 and expm1 on 8 doubles and on 16 floats (S10-08). The reduction,
   table and polynomials are those of Arm optimized-routines v26.01 math/exp2.c, exp10.c and
   exp.c (__exp_data, ADR-0011); the vector form, the scaling and expm1 are written here. */
#include "vmath_v1b.h"
#include "math_config.h"
_Static_assert(EXP_TABLE_BITS == 7 && EXP_POLY_ORDER == 5 && EXP2_POLY_ORDER == 5, "unsupported upstream configuration");

/* k = 128 n + j: the table's tail and 2^(j/128) in [1, 2), and n. */
static inline void exp_table(vu k, vd *tail, vd *scale, vi *n)
{
  vu j = k & 127;
  *tail = (vd)VGATHER(vu, __exp_data.tab[2 * j[l_]]);
  *scale = (vd)(VGATHER(vu, __exp_data.tab[2 * j[l_] + 1]) + (j << 45));
  *n = (vi)k >> 7;
}

/* A result that overflows or underflows comes from vscale, which rounds once more: such a
   subnormal result is within 0.75 ULP. Clamping x keeps n in vscale's range, and x beyond the
   clamp gives the same infinity or zero. */
static vd exp2_8(vd x)
{
  const double *c = __exp_data.exp2_poly, shift = __exp_data.exp2_shift;
  vd tail, scale; vi n;
  x = VSEL(x > 1025.0, VD(1025.0), VSEL(x < -1080.0, VD(-1080.0), x));
  vd kd = x + shift;
  exp_table((vu)kd - 0x42c8000000000000ULL /* shift's bits */, &tail, &scale, &n);
  vd r = x - (kd - shift), r2 = r * r;
  vd tmp = tail + r * c[0] + r2 * (c[1] + r * c[2]) + r2 * r2 * (c[3] + r * c[4]);
  return vscale(scale + scale * tmp, n);
}

static vd exp10_8(vd x)
{
  const double *c = __exp_data.exp10_poly, shift = __exp_data.shift;
  vd tail, scale; vi n;
  x = VSEL(x > 310.0, VD(310.0), VSEL(x < -350.0, VD(-350.0), x));
  vd kd = x * __exp_data.invlog10_2N + shift;
  exp_table((vu)kd - 0x4338000000000000ULL, &tail, &scale, &n);
  kd -= shift;
  vd r = x + kd * __exp_data.neglog10_2hiN + kd * __exp_data.neglog10_2loN, r2 = r * r;
  vd y = (c[0] + r * c[1]) + r2 * (c[2] + r * c[3] + r2 * c[4]);
  return vscale(scale + scale * (tail + y * r), n);
}

/* expm1. |x| < 0.25: the Taylor series x + x^2/2 + x^3 q(x), whose terms after x are too small
   for their rounding to matter. Otherwise exp's reduction, e^x = s (1 + tmp) with s = 2^n
   2^(j/128): s - 1 is taken with its rounding error, and s is at least 0.28 away from 1, so
   nothing cancels. Above n = 60 the 1 is below the last place. */
static vd expm1_8(vd x)
{
  const double *c = __exp_data.poly, shift = __exp_data.shift;
  vd tail, scale, e, a = vfabs(x); vi n;
  vd xc = VSEL(x > 710.0, VD(710.0), VSEL(x < -40.0, VD(-40.0), x));
  vd kd = xc * __exp_data.invln2N + shift;
  exp_table((vu)kd - 0x4338000000000000ULL, &tail, &scale, &n);
  kd -= shift;
  vd r = xc + kd * __exp_data.negln2hiN + kd * __exp_data.negln2loN, r2 = r * r;
  vd tmp = tail + r + r2 * (c[0] + r * c[1]) + r2 * r2 * (c[2] + r * c[3]);
  vi big = n > 60;
  vd s = scale * vpow2(n & ~big);
  vd h = two_sum(s, VD(-1.0), &e);
  vd y = VSEL(big, vscale(scale + scale * tmp, n), h + (e + s * tmp));
  vd t = VSEL(a < 0.25, x, VD(0.0)), t2 = t * t;
  vd q = 1.0 / 6 + t * (1.0 / 24 + t * (1.0 / 120 + t * (1.0 / 720 + t * (1.0 / 5040 + t * (1.0 / 40320
         + t * (1.0 / 362880 + t * (1.0 / 3628800 + t * (1.0 / 39916800 + t * (1.0 / 479001600
         + t * (1.0 / 6227020800.0))))))))));
  y = VSEL(a < 0.25, t + (0.5 * t2 + t2 * t * q), y);
  /* Also x = -0, which the sum above would turn into +0. */
  return VSEL(a < 0x1p-54, x, y);
}

KNC_VMATH_V1B1(exp2, exp2_8, exp2_8)
KNC_VMATH_V1B1(exp10, exp10_8, exp10_8)
KNC_VMATH_V1B1(expm1, expm1_8, expm1_8)
