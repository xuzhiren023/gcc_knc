/* libknc_vmath: log2 and log1p on 8 doubles and on 16 floats (S10-08). log2 is Arm
   optimized-routines v26.01 math/log2.c without fma (__log2_data); log1p evaluates math/log.c
   (__log_data, ADR-0011) on 1 + x with the rounding error of that sum carried into the reduced
   argument. Both paths of each are computed and the lane's one is selected. */
#include "vmath_v1b.h"
#include "math_config.h"
_Static_assert(!HAVE_FAST_FMA && LOG_TABLE_BITS == 7 && LOG_POLY_ORDER == 6 && LOG_POLY1_ORDER == 12
               && LOG2_TABLE_BITS == 6 && LOG2_POLY_ORDER == 7 && LOG2_POLY1_ORDER == 11,
               "unsupported upstream configuration");
#define OFF 0x3fe6000000000000ULL

/* The cases the arithmetic does not produce: log(0) for x = ZERO, a negative argument below
   it, +infinity and NaN. */
static inline vd log_specials(vd x, double zero, vd y)
{
  y = VSEL(x == zero, VD(-VINF), y);
  y = VSEL(x < zero, VD(__builtin_nan("")), y);
  return VSEL((x == VINF) | (x != x), x, y);
}

static vd log2_8(vd x)
{
  const double *a = __log2_data.poly, *b = __log2_data.poly1;
  const double ln2hi = __log2_data.invln2hi, ln2lo = __log2_data.invln2lo;
  /* Near 1: r = x - 1 is exact. */
  vi near = (x >= 1.0 - 0x1.5b51p-5) & (x < 1.0 + 0x1.6ab2p-5);
  vd r = VSEL(near, x, VD(1.0)) - 1.0;
  vd rhi = (vd)((vu)r & (-1ULL << 32)), rlo = r - rhi;
  vd hi = rhi * ln2hi, lo = rlo * ln2hi + r * ln2lo;
  vd r2 = r * r, r4 = r2 * r2, p = r2 * (b[0] + r * b[1]);
  vd y1 = hi + p;
  lo += hi - y1 + p;
  lo += r4 * (b[2] + r * b[3] + r2 * (b[4] + r * b[5]) + r4 * (b[6] + r * b[7] + r2 * (b[8] + r * b[9])));
  y1 += lo;
  /* x = 2^k z with z in [OFF, 2 OFF), a subnormal x scaled first; c is near z's table interval. */
  vi tiny = x < 0x1p-1022;
  vu ix = VSEL(tiny, (vu)(VSEL(tiny, x, VD(0.0)) * 0x1p52) - (52ULL << 52), (vu)x);
  vu tmp = ix - OFF, i = tmp >> 46 & 63;
  vd z = (vd)(ix - (tmp & 0xfffULL << 52)), kd = vfromint((vi)tmp >> 52);
  vd invc = VGATHER(vd, __log2_data.tab[i[l_]].invc), logc = VGATHER(vd, __log2_data.tab[i[l_]].logc);
  vd chi = VGATHER(vd, __log2_data.tab2[i[l_]].chi), clo = VGATHER(vd, __log2_data.tab2[i[l_]].clo);
  r = (z - chi - clo) * invc;
  rhi = (vd)((vu)r & (-1ULL << 32)); rlo = r - rhi;
  vd t1 = rhi * ln2hi, t2 = rlo * ln2hi + r * ln2lo, t3 = kd + logc;
  hi = t3 + t1; lo = t3 - hi + t1 + t2;
  r2 = r * r; r4 = r2 * r2;
  p = a[0] + r * a[1] + r2 * (a[2] + r * a[3]) + r4 * (a[4] + r * a[5]);
  return log_specials(x, 0.0, VSEL(near, y1, lo + r2 * p + hi));
}

static vd log1p_8(vd x)
{
  const double *a = __log_data.poly, *b = __log_data.poly1;
  /* Near 0: log.c's path near 1, whose r = x - 1 is our x. */
  vi near = (x >= -0x1p-4) & (x < 0x1.09p-4);
  vd r = VSEL(near, x, VD(0.0)), w = r * 0x1p27, rhi = r + w - w, rlo = r - rhi;
  w = rhi * rhi * b[0];
  vd hi = r + w, lo = r - hi + w;
  lo += b[0] * rlo * (rhi + r);
  vd r2 = r * r, r3 = r * r2;
  vd y1 = r3 * (b[1] + r * b[2] + r2 * b[3] + r3 * (b[4] + r * b[5] + r2 * b[6]
          + r3 * (b[7] + r * b[8] + r2 * b[9] + r3 * b[10])));
  y1 = y1 + lo + hi;
  /* 1 + x = u + c exactly, u = 2^k z. log.c's r is z/c' - 1 for the table's c'; ours also takes
     c 2^-k, which is u's rounding error in units of z. Past k = 60 that term is nothing. */
  vd c, u = two_sum(VD(1.0), VSEL(x == VINF, VD(1.0), x), &c);
  vu iu = (vu)u, tmp = iu - OFF, i = tmp >> 45 & 127;
  vi k = (vi)tmp >> 52;
  vd z = (vd)(iu - (tmp & 0xfffULL << 52)), kd = vfromint(k);
  vd invc = VGATHER(vd, __log_data.tab[i[l_]].invc), logc = VGATHER(vd, __log_data.tab[i[l_]].logc);
  vd chi = VGATHER(vd, __log_data.tab2[i[l_]].chi), clo = VGATHER(vd, __log_data.tab2[i[l_]].clo);
  r = (z - chi - clo) * invc + c * vpow2(-VSEL(k > 60, (vi)VU(60), k)) * invc;
  w = kd * __log_data.ln2hi + logc;
  hi = w + r; lo = w - hi + r + kd * __log_data.ln2lo;
  r2 = r * r;
  vd y = lo + r2 * a[0] + r * r2 * (a[1] + r * a[2] + r2 * (a[3] + r * a[4])) + hi;
  /* x below 2^-54 is its own logarithm, and so is -0, which y1 would turn into +0. */
  y = VSEL(vfabs(x) < 0x1p-54, x, VSEL(near, y1, y));
  return log_specials(x, -1.0, y);
}

KNC_VMATH_V1B1(log2, log2_8, log2_8)
KNC_VMATH_V1B1(log1p, log1p_8, log1p_8)
