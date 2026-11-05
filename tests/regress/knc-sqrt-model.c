/* S5-03 host experiments: exact emulation of FMA-based div/sqrt in a
   p-bit binary format with unbounded exponent.  Values are (sign, M, E):
   (-1)^s * M * 2^E with 2^(p-1) <= M < 2^p, or zero.  */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef __int128 i128;
typedef unsigned __int128 u128;

enum { RN, RD, RU, RZ };
static int P;               /* precision */
static int inexact;         /* set by rnd when the result is inexact */

typedef struct { int s; int64_t M; int E; } fp;   /* M == 0: zero */

static fp mk (int64_t M, int E)
{ fp r; r.s = M < 0; r.M = M < 0 ? -M : M; r.E = E; return r; }

/* Round the exact value v * 2^e (v signed) to P bits in mode m.  */
static fp rnd (i128 v, int e, int m)
{
  fp r; r.s = v < 0; u128 a = v < 0 ? -(u128) v : (u128) v;
  inexact = 0;
  if (a == 0) { r.M = 0; r.E = 0; r.s = 0; return r; }
  int nb = 0; for (u128 t = a; t; t >>= 1) nb++;
  int sh = nb - P;
  if (sh <= 0) { r.M = (int64_t) (a << -sh); r.E = e + sh; return r; }
  u128 q = a >> sh, rem = a - (q << sh), half = (u128) 1 << (sh - 1);
  int up = 0;
  if (rem) inexact = 1;
  switch (m) {
    case RN: up = rem > half || (rem == half && (q & 1)); break;
    case RZ: up = 0; break;
    case RU: up = rem && !r.s; break;
    case RD: up = rem && r.s; break;
  }
  q += up;
  if (q >> P) { q >>= 1; sh++; }
  r.M = (int64_t) q; r.E = e + sh; return r;
}

/* Exact x*y + z, rounded.  Aligns on the smaller exponent.  */
static fp fma_ (fp x, fp y, fp z, int m)
{
  i128 pm = (i128) x.M * y.M; if (x.s ^ y.s) pm = -pm;
  int pe = x.E + y.E;
  i128 zm = z.M; if (z.s) zm = -zm;
  int ze = z.E;
  if (x.M == 0 || y.M == 0) { pm = 0; pe = ze; }
  if (z.M == 0) { zm = 0; ze = pe; }
  int e = pe < ze ? pe : ze;
  if (pe - e > 120 - 2 * P || ze - e > 120 - P) { fprintf (stderr, "span\n"); exit (2); }
  i128 v = pm * ((i128) 1 << (pe - e)) + zm * ((i128) 1 << (ze - e));
  return rnd (v, e, m);
}
static fp neg (fp x) { x.s ^= 1; return x; }
static fp zero (void) { fp r = {0, 0, 0}; return r; }
static fp mul (fp x, fp y, int m) { return fma_ (x, y, zero (), m); }
static int eq (fp a, fp b)
{ if (a.M == 0 || b.M == 0) return a.M == b.M;
  return a.s == b.s && a.M == b.M && a.E == b.E; }

/* Compare sign of (A*2^ea - B*2^eb), both nonnegative integers.  */
static int cmp2 (u128 A, int ea, u128 B, int eb)
{
  int e = ea < eb ? ea : eb;
  A <<= ea - e; B <<= eb - e;
  return A < B ? -1 : A > B;
}

/* Correct rounding of sqrt(x) (x positive) in mode m.  */
static fp sqrt_ref (fp x, int m)
{
  int64_t M = x.M; int E = x.E;
  if (E & 1) { M <<= 1; E--; }
  int k = P + 3;
  u128 n = (u128) M << (2 * k);
  u128 s = 0;                      /* integer sqrt */
  for (int b = 63; b >= 0; b--) { u128 t = s | ((u128) 1 << b); if (t * t <= n) s = t; }
  int exact = s * s == n;
  i128 v = (i128) ((s << 1) | !exact);
  return rnd (v, E / 2 - k - 1, m);
}

static const char *mname[] = {"RN", "RD", "RU", "RZ"};

/* ---- E3: square root core on m in [1/2, 2) ---- */
static int rsqrt_cands (fp m, int cn, int cd, fp *out)
{
  /* 1/sqrt(m) in (0.707, 1.414].  Candidates y = Y 2^-P (y<1) or Y 2^-(P-1) (y in [1,2)).  */
  int n = 0;
  for (int bin = 0; bin < 2; bin++) {
    int ey = bin ? -(P - 1) : -P;
    /* approx Y = 2^-ey / sqrt(m): search by integer sqrt bracket */
    /* y^2 m ~ 1 -> Y^2 M 2^(2ey+em) ~ 1 */
    int K = -(2 * ey + m.E);   /* Y^2 M ~ 2^K */
    if (K < 0) continue;
    u128 target = ((u128) 1 << K) / (u128) m.M;   /* Y^2 ~ target */
    u128 s = 0;
    for (int b = 62; b >= 0; b--) { u128 t = s | ((u128) 1 << b); if (t * t <= target) s = t; }
    for (int64_t Y = (int64_t) s - 3; Y <= (int64_t) s + 3; Y++) {
      if (Y < ((int64_t) 1 << (P - 1)) || Y >= ((int64_t) 1 << P)) continue;
      /* |y - 1/sqrt m| <= c u, u = 2^ey:  m (y - c u)^2 <= 1 <= m (y + c u)^2.
         Scale: y = Y 2^ey, c u = (cn/cd) 2^ey.  Let W = Y cd.
         m (W -+ cn)^2 2^(2ey) / cd^2 vs 1  ->  M (W -+ cn)^2 vs cd^2 2^K */
      i128 W = (i128) Y * cd;
      u128 lo = (u128) (W - cn) * (u128) (W - cn) * (u128) m.M;
      u128 hi = (u128) (W + cn) * (u128) (W + cn) * (u128) m.M;
      u128 rhs = (u128) cd * cd << K;
      if (lo <= rhs && rhs <= hi) out[n++] = mk (Y, ey);
    }
  }
  return n;
}

static int e3_sqrt (int p, int cn, int cd)
{
  P = p;
  long runs = 0, fail[4] = {0}, flagfail = 0, dinexact = 0, g1unf = 0, maxc = 0, nocand = 0;
  fp half = mk ((int64_t) 1 << (P - 1), -P);
  for (int bin = 0; bin < 2; bin++)
    for (int64_t M = (int64_t) 1 << (P - 1); M < ((int64_t) 1 << P); M++) {
      fp m = mk (M, bin ? -(P - 1) : -P), c[16];
      int n = rsqrt_cands (m, cn, cd, c);
      if (n > maxc) maxc = n;
      if (!n) nocand++;
      fp rd = sqrt_ref (m, RD), ru = sqrt_ref (m, RU);
      fp ref[4]; int exact;
      for (int k = 0; k < 4; k++) ref[k] = sqrt_ref (m, k);
      exact = eq (rd, ru);
      for (int i = 0; i < n; i++) {
        fp y0 = c[i];
        fp g0 = mul (m, y0, RN);
        fp h0 = mul (half, y0, RN);
        fp r0 = fma_ (neg (g0), h0, half, RN);
        fp g1 = fma_ (g0, r0, g0, RN);
        fp h1 = fma_ (h0, r0, h0, RN);
        fp d = fma_ (neg (g1), g1, m, RN); if (inexact) dinexact++;
        if (!eq (g1, rd) && !eq (g1, ru)) g1unf++;
        runs++;
        for (int k = 0; k < 4; k++) {
          fp g2 = fma_ (d, h1, g1, k);
          if (!eq (g2, ref[k])) { fail[k]++; if (fail[k] <= 3) printf ("  sqrt %s fail M=%llx bin=%d y0=%llx\n", mname[k], (long long) M, bin, (long long) y0.M); }
          if (inexact == exact) flagfail++;
        }
      }
    }
  printf ("E3 sqrt p=%d bound=%d/%d: runs=%ld (max %ld cands, %ld inputs without) g1_unfaithful=%ld d_inexact=%ld fail RN=%ld RD=%ld RU=%ld RZ=%ld inexact_flag_wrong=%ld\n",
          p, cn, cd, runs, maxc, nocand, g1unf, dinexact, fail[0], fail[1], fail[2], fail[3], flagfail);
  return nocand || g1unf || flagfail || fail[0] || fail[1] || fail[2] || fail[3];
}


int main (void)
{
  int bad = e3_sqrt (24, 775, 1000);
  bad |= e3_sqrt (24, 1, 1);
  return bad;
}
