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
static int fix = 1; static long failures; static int P;               /* precision */
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
  i128 v = (pm << (pe - e)) + (zm << (ze - e));
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

/* Correct rounding of a/b (a, b positive) in mode m, by exact search.  */
static fp div_ref (fp a, fp b, int m)
{
  /* a/b = (A/B) 2^(ea-eb).  Long division with sticky.  */
  int k = 2 * P + 4;
  u128 n = (u128) a.M << k;
  u128 q = n / b.M, r = n % b.M;
  i128 v = (i128) ((q << 1) | (r != 0));   /* sticky bit */
  return rnd (v, a.E - b.E - k - 1, m);
}

static const char *mname[] = {"RN", "RD", "RU", "RZ"};

/* ---- E1/E2: division core ---- */
/* Candidates y0 for 1/b with |y0 - 1/b| <= c ulp(y0), c = cn/cd.  b in [1,2).  */
static int recip_cands (fp b, int cn, int cd, fp *out)
{
  int n = 0;
  /* y in (1/2, 1]: y = Y 2^-P, Y in [2^(P-1), 2^P]; y = 1 is 2^(P-1) 2^-(P-1).  */
  int64_t B = b.M;   /* b = B 2^b.E, b.E = -(P-1) */
  /* 1/b = 2^(P-1)/B.  Y0 = floor(2^(2P-1)/B).  */
  int64_t Y0 = (int64_t) (((u128) 1 << (2 * P - 1)) / B);
  for (int64_t Y = Y0 - 3; Y <= Y0 + 3; Y++) {
    if (Y < ((int64_t) 1 << (P - 1)) || Y > ((int64_t) 1 << P)) continue;
    /* ulp(y): 2^-P for y < 1, 2^-(P-1) for y == 1 (binade [1,2)).  We
       treat ulp relative to y's binade.  */
    int64_t ulpu = (Y == ((int64_t) 1 << P)) ? 2 : 1;   /* in units of 2^-P */
    /* |Y 2^-P - 2^(P-1)/B| <= c ulpu 2^-P  <=>  |Y B - 2^(2P-1)| * cd <= cn ulpu B */
    i128 d = (i128) Y * B - ((i128) 1 << (2 * P - 1)); if (d < 0) d = -d;
    if (d * cd <= (i128) cn * ulpu * B) {
      fp y = (Y == ((int64_t) 1 << P)) ? mk ((int64_t) 1 << (P - 1), -(P - 1)) : mk (Y, -P);
      out[n++] = y;
    }
  }
  return n;
}

/* |b y - 1| < 1/(B+1), B = integer significand of b.  */
static int cond_C (fp b, fp y)
{
  /* b y - 1 = (B Y 2^(eb+ey)) - 1.  Multiply by 2^-(eb+ey) = 2^K.  */
  int K = -(b.E + y.E);
  i128 d = (i128) b.M * y.M - ((i128) 1 << K); if (d < 0) d = -d;
  /* d 2^-K < 1/(B+1)  <=>  d (B+1) < 2^K */
  return d * (b.M + 1) < ((i128) 1 << K);
}

static void e1_recip (int p, int cn, int cd)
{
  P = p;
  long nb = 0, nc = 0, e0inexact = 0, failC = 0, notRN = 0, maxc = 0;
  fp one = mk ((int64_t) 1 << (P - 1), -(P - 1));
  for (int64_t B = (int64_t) 1 << (P - 1); B < ((int64_t) 1 << P); B++) {
    fp b = mk (B, -(P - 1)), c[8];
    int n = recip_cands (b, cn, cd, c);
    if (n > maxc) maxc = n;
    nb++;
    fp yr = div_ref (one, b, RN);
    for (int i = 0; i < n; i++) {
      nc++;
      fp y0 = c[i];
      fp e0 = fma_ (neg (b), y0, one, RN); if (inexact) e0inexact++;
      fp y1 = fma_ (e0, y0, y0, RN);
      if (fix && B == ((int64_t) 1 << P) - 1)
        y1 = mk (((int64_t) 1 << (P - 1)) + 1, -P);
      if (!cond_C (b, y1)) { failC++; if (failC <= 5) printf ("  condC fails B=%llx y0=%llx\n", (long long) B, (long long) y0.M); }
      if (!eq (y1, yr)) notRN++;
    }
  }
  failures += e0inexact + failC;
  printf ("E1 p=%d bound=%d/%d: b=%ld cands=%ld (max %ld per b) e0_inexact=%ld condC_fail=%ld y1!=RN(1/b): %ld\n",
          p, cn, cd, nb, nc, maxc, e0inexact, failC, notRN);
}

/* 8-op division on mantissas a, b in [1,2):
   y0=rcp; e0=1-b y0; y1=y0+e0 y0; q0=a y1; r0=a-b q0; q1=q0+r0 y1;
   r1=a-b q1; q2=q1+r1 y1 (final in mode m).  */
static void e2_div (int p, int cn, int cd)
{
  P = p;
  long runs = 0, fail[4] = {0}, flagfail = 0, r1inexact = 0, q1unf = 0;
  fp one = mk ((int64_t) 1 << (P - 1), -(P - 1));
  for (int64_t B = (int64_t) 1 << (P - 1); B < ((int64_t) 1 << P); B++) {
    fp b = mk (B, -(P - 1)), c[8];
    int n = recip_cands (b, cn, cd, c);
    for (int i = 0; i < n; i++) {
      fp y0 = c[i];
      fp e0 = fma_ (neg (b), y0, one, RN);
      fp y1 = fma_ (e0, y0, y0, RN);
      if (fix && B == ((int64_t) 1 << P) - 1)
        y1 = mk (((int64_t) 1 << (P - 1)) + 1, -P);
      for (int64_t A = (int64_t) 1 << (P - 1); A < ((int64_t) 1 << P); A++) {
        fp a = mk (A, -(P - 1));
        fp q0 = mul (a, y1, RN);
        fp r0 = fma_ (neg (b), q0, a, RN);
        fp q1 = fma_ (r0, y1, q0, RN);
        fp r1 = fma_ (neg (b), q1, a, RN); if (inexact) r1inexact++;
        /* q1 faithful: q1 is RD or RU of a/b */
        if (!eq (q1, div_ref (a, b, RD)) && !eq (q1, div_ref (a, b, RU))) q1unf++;
        runs++;
        for (int m = 0; m < 4; m++) {
          fp q2 = fma_ (r1, y1, q1, m);
          int ix = inexact;
          fp ref = div_ref (a, b, m);
          int ex = !inexact;   /* div_ref sets inexact for a/b */
          if (!eq (q2, ref)) { fail[m]++; if (fail[m] <= 3) printf ("  %s fail A=%llx B=%llx\n", mname[m], (long long) A, (long long) B); }
          if (ix == ex) flagfail++;
        }
      }
    }
  }
  failures += q1unf + r1inexact + flagfail + fail[0] + fail[1] + fail[2] + fail[3];
  printf ("E2 div p=%d bound=%d/%d: runs=%ld q1_unfaithful=%ld r1_inexact=%ld fail RN=%ld RD=%ld RU=%ld RZ=%ld inexact_flag_wrong=%ld\n",
          p, cn, cd, runs, q1unf, r1inexact, fail[0], fail[1], fail[2], fail[3], flagfail);
}

static int64_t inv_mod (int64_t a, int64_t m)
{
  int64_t g = m, x = 0, x1 = 1, a1 = a % m;
  while (a1) { int64_t q = g / a1, t = g - q * a1; g = a1; a1 = t; t = x - q * x1; x = x1; x1 = t; }
  if (g != 1) return -1;
  return ((x % m) + m) % m;
}

static long e4_fail[4], e4_runs, e4_flag;
static void e4_one (fp a, fp b, fp y1)
{
  fp q0 = mul (a, y1, RN);
  fp r0 = fma_ (neg (b), q0, a, RN);
  fp q1 = fma_ (r0, y1, q0, RN);
  fp r1 = fma_ (neg (b), q1, a, RN);
  e4_runs++;
  for (int m = 0; m < 4; m++) {
    fp q2 = fma_ (r1, y1, q1, m); int ix = inexact;
    fp ref = div_ref (a, b, m); int ex = !inexact;
    if (!eq (q2, ref)) e4_fail[m]++;
    if (ix == ex) e4_flag++;
  }
}

/* p=24 hard cases: a/b within u/(2B) * N of a midpoint, N = 1..NMAX,
   both quotient binades; plus a/b near 1 and a = 1.  fix: blend
   y1 = RN(1/b) when B is all ones.  */
static void e4_hard (int nmax)
{
  P = 24;
  memset (e4_fail, 0, sizeof e4_fail); e4_runs = e4_flag = 0;
  fp one = mk ((int64_t) 1 << 23, -23);
  long cases = 0;
  for (int64_t B = (int64_t) 1 << 23; B < ((int64_t) 1 << 24); B++) {
    fp b = mk (B, -23), c[8];
    int n = recip_cands (b, 912, 1000, c);
    int64_t As[64]; int na = 0;
    if (B & 1)
      for (int s = 24; s <= 25; s++) {
        int64_t i2 = inv_mod ((int64_t) (((u128) 1 << s) % B), B);
        for (int N = 1; N <= nmax; N++)
          for (int sg = -1; sg <= 1; sg += 2) {
            int64_t A0 = (int64_t) (((u128) i2 * (u128) (sg > 0 ? N : B - N)) % B);
            for (int64_t A = A0; A < ((int64_t) 1 << 24); A += B)
              if (A >= ((int64_t) 1 << 23) && ((s == 24) == (A >= B)) && na < 60) As[na++] = A;
          }
      }
    for (int64_t A = B - 3; A <= B + 3; A++)
      if (A >= ((int64_t) 1 << 23) && A < ((int64_t) 1 << 24) && na < 64) As[na++] = A;
    cases += na;
    for (int i = 0; i < n; i++) {
      fp y0 = c[i];
      fp e0 = fma_ (neg (b), y0, one, RN);
      fp y1 = fma_ (e0, y0, y0, RN);
      if (fix && B == ((int64_t) 1 << 24) - 1) y1 = div_ref (one, b, RN);
      for (int j = 0; j < na; j++) e4_one (mk (As[j], -23), b, y1);
      e4_one (one, b, y1);
    }
  }
  failures += e4_flag + e4_fail[0] + e4_fail[1] + e4_fail[2] + e4_fail[3];
  printf ("E4 p=24 hard N<=%d fix=%d: (a,b) cases=%ld runs=%ld fail RN=%ld RD=%ld RU=%ld RZ=%ld inexact_flag_wrong=%ld\n",
          nmax, fix, cases, e4_runs, e4_fail[0], e4_fail[1], e4_fail[2], e4_fail[3], e4_flag);
}

int main (int argc, char **argv)
{
  setbuf (stdout, NULL);
  fix = !(argc > 1 && !strcmp (argv[1], "--omit-step-15"));
  e1_recip (24, 912, 1000);
  e1_recip (24, 1, 1);
  for (int p = 6; p <= 11; p++) {
    e2_div (p, 912, 1000);
    e2_div (p, 1, 1);
  }
  e4_hard (4);
  printf ("step15=%d failures=%ld\n", fix, failures);
  return failures != 0;
}
