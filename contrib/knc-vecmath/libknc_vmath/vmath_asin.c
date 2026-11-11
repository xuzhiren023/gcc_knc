/* libknc_vmath: asin and acos on 8 doubles and on 16 floats (S10-08). Written for this
   library: asin(x) = x + x^3 P(x^2) up to 0.5, and asin(x) = pi/2 - 2 asin(sqrt((1 - x)/2))
   above it, where the square root carries its error term and pi/2 its low word, so that the
   last sum is the only one whose rounding matters. Arm optimized-routines' advsimd asin, with
   the same split, states 2.69 ULP. */
#include "vmath_v1b.h"

#define PIO2_HI 0x1.921fb54442d18p+0
#define PIO2_LO 0x1.1a62633145c07p-54

/* P(z) = (asin(sqrt z)/sqrt z - 1)/z on [0, 0.25]: the interpolant of degree 13 at the
   Chebyshev nodes, computed with MPFR at 400 bits and rounded to double; relative error 2^-54,
   which is the rounding of the first coefficient, 1/6. */
static inline vd asin_poly(vd z)
{
  static const double c[14] = {
    0x1.5555555555555p-3, 0x1.3333333333388p-4, 0x1.6db6db6dac1ep-5, 0x1.f1c71c7a52ba3p-6,
    0x1.6e8ba123e494cp-6, 0x1.1c4efce23019fp-6, 0x1.c990ad3d8fdcap-7, 0x1.7b027ee1dd585p-7,
    0x1.3b49de7121487p-7, 0x1.31622469ce5adp-7, 0x1.8f193743418ffp-9, 0x1.406192d124629p-6,
    -0x1.3b416bb7d9257p-6, 0x1.e529c6fce9bb4p-6 };
  vd p = VD(c[13]);
  for (int i = 12; i >= 0; --i) p = c[i] + z * p;
  return p;
}

/* For z = (1 - a)/2: asin(sqrt(z)) = *s + *rest, where *s is the rounded square root and *rest
   holds its error (z - s^2)/(2 s) and s z P(z). a above 1 leaves a NaN in *s. */
static inline void asin_root(vd a, vd *s, vd *rest)
{
  vd z = (1.0 - a) * 0.5, e, root = vsqrt(z), p = two_prod(root, root, &e);
  vi positive = root > 0.0;
  vd error = VSEL(positive, ((z - p) - e) / (2.0 * VSEL(positive, root, VD(1.0))), VD(0.0));
  *s = root;
  *rest = error + root * z * asin_poly(z);
}

static vd asin_8(vd x)
{
  vd a = vfabs(x), z = a * a, s, rest, e;
  asin_root(a, &s, &rest);
  vd h = two_sum(VD(PIO2_HI), -2.0 * s, &e);
  vd y = VSEL(a < 0.5, a + a * z * asin_poly(z), h + (e + (PIO2_LO - 2.0 * rest)));
  return vcopysign(y, x);
}

/* acos(x) is pi/2 - asin(x) below 0.5, 2 asin(sqrt(z)) above it and pi less that for -x. */
static vd acos_8(vd x)
{
  vd a = vfabs(x), z = a * a, s, rest, e, e2;
  asin_root(a, &s, &rest);
  vd h = two_sum(VD(PIO2_HI), -x, &e);
  vd h2 = two_sum(VD(2.0 * PIO2_HI), -2.0 * s, &e2);
  vd y = VSEL(x < 0.0, h2 + (e2 + (2.0 * PIO2_LO - 2.0 * rest)), 2.0 * (s + rest));
  return VSEL(a < 0.5, h + (e + (PIO2_LO - x * z * asin_poly(z))), y);
}

KNC_VMATH_V1B1(asin, asin_8, asin_8)
KNC_VMATH_V1B1(acos, acos_8, acos_8)
