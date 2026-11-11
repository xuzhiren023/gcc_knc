/* libknc_vmath: erf and erfc on 8 doubles and on 16 floats (S10-08), after Arm
   optimized-routines v26.01 (ADR-0011). Both expand around r, the multiple of 1/128 nearest
   |x|, with d = |x| - r and scale = 2/sqrt(pi) exp(-r^2) (math/aarch64/advsimd/erf.c and erfc.c,
   tables __v_erf_data and __v_erfc_data):

     erf(r + d) = erf(r) + scale d poly(r, d),  erfc(r + d) = erfc(r) - scale d poly(r, d).

   The tables hold erf(r) and erfc(r) rounded to one double, so a result is off by up to half
   an ULP of the table value before its own rounding: erf within 1.05 ULP, erfc within
   upstream's 1.71. Below 0.5 erf would lose more (upstream: 2.29 ULP), so it takes the
   polynomial of math/erf.c there. */
#include "vmath_v1b.h"
#include "math_config.h"

#define THIRD 0x1.5555555555555p-2

/* p1 to p5 of poly(r, d) = 1 - d (p1 + d p2 + d^2 p3 + ...); r2 is r^2. */
static inline void erf_terms(vd r, vd r2, vd p[5])
{
  p[0] = r;
  p[1] = THIRD - r2 * (2 * THIRD);
  p[2] = r * (r2 * THIRD - 0.5);
  p[3] = -0.1 - r2 * (-0.4 + r2 * (2.0 / 15));
  p[4] = r * (0.5 * THIRD + r2 * (-2.0 / 9 + r2 * (2.0 / 45)));
}

static vd erf_8(vd x)
{
  static const double c[10] = {
    0x1.06eba8214db68p-3, -0x1.812746b037948p-2, 0x1.ce2f21a03872p-4, -0x1.b82ce30e6548p-6,
    0x1.565bcc360a2f2p-8, -0x1.c02d812bc979ap-11, 0x1.f99bddfc1ebe9p-14, -0x1.f42c457cee912p-17,
    0x1.b0e414ec20ee9p-20, -0x1.18c47fd143c5ep-23 };
  vd a = vfabs(x), p[5];
  /* |x| < 0.5: x + x q(x^2). */
  vd t = VSEL(a < 0.5, x, VD(0.0)), t2 = t * t, q = VD(c[9]);
  for (int i = 8; i >= 0; --i) q = c[i] + t2 * q;
  /* The table ends at 6 - 1/128, where erf is 1 already. */
  vd ac = VSEL(a <= 5.9921875, a, VD(5.9921875)), z = ac + 0x1p45;
  vu i = (vu)z - 0x42c0000000000000ULL;
  vd r = z - 0x1p45, d = ac - r, d2 = d * d;
  vd erfr = VGATHER(vd, __v_erf_data.tab[i[l_]].erf), scale = VGATHER(vd, __v_erf_data.tab[i[l_]].scale);
  erf_terms(r, r * r, p);
  vd y = (p[0] + d * p[1]) + d2 * ((p[2] + d * p[3]) + d2 * p[4]);
  y = VSEL(a < 0.5, t + q * t, vcopysign(erfr + scale * (d - d2 * y), x));
  return VSEL(x != x, x, y);
}

static vd erfc_8(vd x)
{
  /* (i + 1)/i and -2 i/((i + 1) (i + 2)) for i = 5 to 9: p(i+2) = (p(i) + r Q(i+1) p(i+1)) R(i+1). */
  static const double qr[5][2] = {
    { 0x1.3333333333333p0, -0x1.e79e79e79e79ep-3 }, { 0x1.2aaaaaaaaaaabp0, -0x1.b6db6db6db6dbp-3 },
    { 0x1.2492492492492p0, -0x1.8e38e38e38e39p-3 }, { 0x1.2p0, -0x1.6c16c16c16c17p-3 },
    { 0x1.1c71c71c71c72p0, -0x1.4f2094f2094f2p-3 } };
  vd a = vfabs(x), p[10];
  /* The table ends at 3487/128, where erfc underflows to nothing. Its entries are scaled by
     2^128 to stay normal. */
  vd ac = VSEL(a <= 0x1.b3ep+4, a, VD(0x1.b3ep+4)), z = ac + 0x1p45;
  vu i = (vu)z - 0x42c0000000000000ULL;
  vd r = z - 0x1p45, d = ac - r, d2 = d * d;
  vd erfcr = VGATHER(vd, __v_erfc_data.tab[i[l_]].erfc), scale = VGATHER(vd, __v_erfc_data.tab[i[l_]].scale);
  erf_terms(r, r * r, p);
  for (int n = 0; n < 5; ++n) p[n + 5] = (p[n + 3] + p[n + 4] * (r * qr[n][0])) * qr[n][1];
  vd y = (p[6] + d * p[7]) + d2 * (p[8] + d * p[9]);
  y = (p[4] + d * p[5]) + d2 * y;
  y = (p[2] + d * p[3]) + d2 * y;
  y = (p[0] + d * p[1]) + d2 * y;
  /* erfc(r) - scale d + scale d^2 y: the product scale d and the difference are taken with
     their errors, as the correction is up to a fifth of erfc(r) and the result can lie a
     binade below it. */
  vd tl, e, th = two_prod(scale, d, &tl), s = two_sum(erfcr, -th, &e);
  y = (s + ((e - tl) + scale * (d2 * y))) * 0x1p-128;
  y = VSEL(x < 0.0, 2.0 - y, y);
  return VSEL(x != x, x, VSEL(x == VINF, VD(0.0), y));
}

KNC_VMATH_V1B1(erf, erf_8, erf_8)
KNC_VMATH_V1B1(erfc, erfc_8, erfc_8)
