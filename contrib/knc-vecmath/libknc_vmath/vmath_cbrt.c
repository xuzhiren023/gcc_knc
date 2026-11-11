/* libknc_vmath: cbrt and hypot on 8 doubles and on 16 floats (S10-08). Written for this
   library: both end in one Newton correction whose residual is computed exactly, so the result
   is the correctly rounded one but for a sum rounded once (0.5 ULP and a little; 0.75 ULP for a
   subnormal hypot, which is rounded once more). Arm optimized-routines' advsimd cbrt and hypot
   state 1.6 and 1.21 ULP. */
#include "vmath_v1b.h"

static vd cbrt_8(vd x)
{
  /* 2^(-rem/3), for the start value. */
  static const double third[3] = { 1.0, 0x1.965fea53d6e3dp-1, 0x1.428a2f98d728bp-1 };
  vd a = vfabs(x), start, l, e;
  vi tiny = a < 0x1p-1022, q;
  vu ia = (vu)VSEL(tiny, VSEL(tiny, a, VD(0.0)) * 0x1p54, a), ib;
  /* |x| = 2^(3 q) b with b in [1, 8); 1023 is a multiple of 3. */
  for (int i = 0; i < 8; ++i) {
    unsigned exponent = ia[i] >> 52 & 0x7ff, rem = exponent % 3;
    q[i] = (int)(exponent / 3) - 341;
    ib[i] = (ia[i] & 0x000fffffffffffffULL) | (uint64_t)(1023 + rem) << 52;
    start[i] = third[rem];
  }
  q -= 18 & tiny;
  vd b = (vd)ib, m = (vd)((ib & 0x000fffffffffffffULL) | 0x3ff0000000000000ULL);
  /* u = b^(-1/3): a quadratic in the significand m, within 0.21%, then Newton's iteration
     u (4 - b u^3)/3, which squares the error and doubles it: 2^-64 after three. */
  vd u = (1.3835059191296826 + m * (-0.4768420562072705 + m * 0.09126116885223197)) * start;
  vd b3 = b * (1.0 / 3);
  for (int i = 0; i < 3; ++i) u = u * (4.0 / 3 - b3 * (u * u * u));
  /* y = b u^2 is the root within a few ULP. y^3 = (h + l) y exactly enough, b - y^3 is exact
     where it matters, and 1/(3 y^2) is u^2/3. */
  vd y = b * u * u, h = two_prod(y, y, &l), p = two_prod(h, y, &e);
  y += (((b - p) - e) - l * y) * (u * u * (1.0 / 3));
  y = vcopysign(y * vpow2(q), x);
  /* Zeros, infinities and NaNs are their own cube roots. */
  return VSEL((a > 0.0) & (a < VINF), y, x);
}

/* x^2 + y^2 as S + t with the products' and the sum's errors in t, on arguments scaled away
   from overflow and underflow; then sqrt(S) and the correction (S - s^2 + t)/(2 s). */
static vd hypot_8(vd x, vd y)
{
  vd ax = vfabs(x), ay = vfabs(y), l1, l2, e;
  vi swap = ax < ay;
  vd hi = VSEL(swap, ay, ax), lo = VSEL(swap, ax, ay);
  vi huge = hi > 0x1p500, tiny = hi < 0x1p-500;
  hi *= VSEL(huge, VD(0x1p-600), VSEL(tiny, VD(0x1p600), VD(1.0)));
  lo *= VSEL(huge, VD(0x1p-600), VSEL(tiny, VD(0x1p600), VD(1.0)));
  vd h1 = two_prod(hi, hi, &l1), h2 = two_prod(lo, lo, &l2);
  vd sum = h1 + h2, t = ((h1 - sum) + h2) + (l1 + l2);
  vd s = vsqrt(sum), p = two_prod(s, s, &e);
  vi positive = s > 0.0;
  s += VSEL(positive, (((sum - p) - e) + t) / (2.0 * VSEL(positive, s, VD(1.0))), VD(0.0));
  s *= VSEL(huge, VD(0x1p600), VSEL(tiny, VD(0x1p-600), VD(1.0)));
  /* An infinity wins over a NaN (C99 F.9.4.3). */
  return VSEL((ax == VINF) | (ay == VINF), VD(VINF), s);
}

/* Floats: their squares are exact in double and the sum cannot overflow. */
static vd hypotf_8(vd x, vd y)
{
  return VSEL((vfabs(x) == VINF) | (vfabs(y) == VINF), VD(VINF), vsqrt(x * x + y * y));
}

KNC_VMATH_V1B1(cbrt, cbrt_8, cbrt_8)
KNC_VMATH_V1B2(hypot, hypot_8, hypotf_8)
