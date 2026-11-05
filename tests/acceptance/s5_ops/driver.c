/* Sprint 5 acceptance driver: scalar references, exact checks, guard pages.
   Build at -O0 -fwrapv (never vectorized), link with loops.c and -lm.
   Prints "S5-OPS PASS failures=0" and one INFO line; exit 0 only if every
   check passes.  A fault prints "S5-OPS FAULT ..." and exits 3.

   References are exact on the card's x87 driver: every FP input set is
   chosen so the reference cannot depend on excess precision (dyadic values
   with exact sums and products, single-rounding conversions, FP32 division
   and square root through double, which is innocuous because 53 >= 2*24+2).
   FP64 division and square root are checked by the residuals of the result
   and its two neighbours, computed exactly with fma.  */
#include <math.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include "ops.h"

#define MAXN 65
#define MAXO 16
static unsigned long checks, failures;
static long page;

static const char *cur = "setup";
static int cur_n, cur_o, cur_where;
static void
on_fault (int sig, siginfo_t *info, void *ctx)
{
  (void) ctx;
  printf ("S5-OPS FAULT sig=%d kernel=%s n=%d o=%d where=%d addr=%p\n", sig,
          cur, cur_n, cur_o, cur_where, info->si_addr);
  fflush (stdout);
  _exit (3);
}
#define SET_CASE(NAME) (cur = (NAME), cur_n = n, cur_o = o, cur_where = where)

/* The first failure of each check is always printed, then up to 20.  */
static void
fail (const char *what, int n, int i, int o)
{
  static const char *last;
  if (failures++ < 20 || what != last)
    printf ("FAIL %s n=%d i=%d o=%d\n", what, n, i, o);
  last = what;
}

static uint64_t seed = 0x9e3779b97f4a7c15ull;
static uint64_t
rnd (void)
{
  seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17;
  return seed;
}

/* Inputs.  */
static const float fspecial[] = { 0.0f, -0.0f, 1.0f, -1.0f, INFINITY,
  -INFINITY, NAN, 1e-45f, -1e-45f, 3.4e38f, -3.4e38f, 0.5f };
static const double dspecial[] = { 0.0, -0.0, 1.0, -1.0, INFINITY, -INFINITY,
  NAN, 5e-324, -5e-324, 1.7e308, -1.7e308, 0.5 };
#define NSPEC 12
static int ibits (void)
{
  static const int edge[] = { 0, 1, -1, 0x7fffffff, -0x7fffffff - 1, 0x01000001 };
  uint64_t r = rnd ();
  return r % 4 == 0 ? edge[(r >> 8) % 6] : (int) (r >> 16);
}
static unsigned ubits (void)
{
  static const unsigned edge[] = { 0, 1, 0xffffffffu, 0x80000000u, 0x80000001u,
    0x01000001u, 0xfffffffeu };
  uint64_t r = rnd ();
  return r % 4 == 0 ? edge[(r >> 8) % 7] : (unsigned) (r >> 16);
}
static long lbits (void)
{
  static const long edge[] = { 0, 1, -1, 0x20000000000001L, -0x20000000000001L,
    INT64_MAX, INT64_MIN };
  uint64_t r = rnd ();
  return r % 4 == 0 ? edge[(r >> 8) % 7] : (long) rnd () >> (r % 40);
}
static float fbits (void)
{
  uint64_t r = rnd ();
  if (r % 3 == 0) return fspecial[(r >> 8) % NSPEC];
  float f; uint32_t u = (uint32_t) (r >> 16);
  memcpy (&f, &u, 4);
  return isnan (f) ? NAN : f;  /* no signalling NaN: x87 would quiet it */
}
static double dbits (void)
{
  uint64_t r = rnd ();
  if (r % 3 == 0) return dspecial[(r >> 8) % NSPEC];
  double d; uint64_t u = rnd ();
  memcpy (&d, &u, 8);
  return isnan (d) ? NAN : d;
}
/* Dyadic k/8, |k| <= 1000: sums of 65 are exact in float.  No -0, no NaN.  */
static float fexact (void) { return (float) ((long) (rnd () >> 8) % 2001 - 1000) / 8.0f; }
static double dexact (void) { return (double) ((long) (rnd () >> 8) % 2001 - 1000) / 8.0; }
/* |k| <= 100: products and sums of 65 products are exact in float.  */
static float fsmall (void) { return (float) ((long) (rnd () >> 8) % 201 - 100) / 8.0f; }
/* Values whose conversion to int is defined: |x| < 2^31, with fractions,
   halves and negative values that truncate to zero.  */
static double inrange (void)
{
  uint64_t r = rnd ();
  if (r % 5 == 0) return (double) ((long) (r >> 8) % 41 - 20) / 2.0;
  double m = 1.0 + (double) (rnd () >> 11) / 9007199254740992.0;
  return ((r >> 7) & 1 ? -1 : 1) * ldexp (m, (int) ((r >> 8) % 36) - 5);
}
static float fconv (void) { float f = (float) inrange (); return fabsf (f) >= 2147483648.0f ? 1.5f : f; }
/* Normal FP32 operands over a wide range, subnormals, and specials.  */
static float fdiv_in (void)
{
  uint64_t r = rnd ();
  if (r % 8 == 0) return fspecial[(r >> 8) % NSPEC];
  if (r % 8 == 1) { float f; uint32_t u = (uint32_t) (r >> 20) & 0x807fffffu; memcpy (&f, &u, 4); return f; }
  float m = 1.0f + (float) ((r >> 16) & 0x7fffff) / 8388608.0f;
  return ((r >> 9) & 1 ? -1 : 1) * ldexpf (m, (int) ((r >> 40) % 160) - 80);
}
/* Normal FP64 operands whose quotients and roots stay normal.  */
static double ddiv_in (void)
{
  uint64_t r = rnd ();
  double m = 1.0 + (double) (rnd () >> 12) / 4503599627370496.0;
  return ((r >> 9) & 1 ? -1 : 1) * ldexp (m, (int) (r % 400) - 200);
}

/* One guarded page per array: PROT_NONE pages on both sides.  "where"
   places n elements at element offset o from the low guard (where = 0) or
   ending o elements before the high guard (where = 1).  */
struct buf { unsigned char *lo; };
static struct buf
guarded (void)
{
  unsigned char *p = mmap (0, 3 * page, PROT_READ | PROT_WRITE,
                           MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (p == MAP_FAILED) { perror ("mmap"); _exit (2); }
  mprotect (p, page, PROT_NONE);
  mprotect (p + 2 * page, page, PROT_NONE);
  struct buf b = { p + page };
  return b;
}
#define SLACK 256
static unsigned char *
win_lo (struct buf b, unsigned char *p)
{
  return p - b.lo > SLACK ? p - SLACK : b.lo;
}
static unsigned char *
win_hi (struct buf b, unsigned char *p, int bytes)
{
  return b.lo + page - (p + bytes) > SLACK ? p + bytes + SLACK : b.lo + page;
}
static void *
place (struct buf b, int size, int n, int o, int where)
{
  unsigned char *p = where ? b.lo + page - (n + o) * size : b.lo + o * size;
  unsigned char *lo = win_lo (b, p), *hi = win_hi (b, p, n * size);
  memset (lo, 0xA5, hi - lo);
  return p;
}
static int
sentinels_ok (struct buf b, void *p, int bytes)
{
  unsigned char *s = p;
  for (unsigned char *q = win_lo (b, s); q < win_hi (b, s, bytes); q++)
    if ((q < s || q >= s + bytes) && *q != 0xA5)
      return 0;
  return 1;
}
/* An index from p (elements of SIZE) into one of b's guard pages.  */
static int
bad_index (struct buf b, void *p, int size)
{
  long lo = ((unsigned char *) p - b.lo) / size;   /* elements above the low guard */
  long hi = (b.lo + page - (unsigned char *) p) / size;
  long k = (long) (rnd () % (page / size / 2));
  return (int) (rnd () & 1 ? hi + k : -lo - 1 - k);
}

static struct buf A, B, C, D, I, M, TBL;

#define SAMEBITS(T, u, v) (memcmp (&(u), &(v), sizeof (T)) == 0)
#define NANEQ(u, v) (isnan (u) && isnan (v))
#define BITS_OK(T) (SAMEBITS (T, c[i], r))
#define FP_OK(T) (SAMEBITS (T, c[i], r) || NANEQ (c[i], r))

#define CASES                                                                 \
  for (int where = 0; where < 2; where++)                                     \
    for (int n = 0; n <= MAXN; n++)                                           \
      for (int o = 0; o < MAXO; o += (n > 20 ? 5 : 1))

/* Element-wise c[i] = f(a[i], b[i]).  */
#define CHECK_EW(TC, TA, TB, NAME, GENA, GENB, CALL, REF, OK)                 \
  CASES                                                                       \
    {                                                                         \
      TA *a = place (A, sizeof (TA), n, o, where);                            \
      TB *b = place (B, sizeof (TB), n, o, where);                            \
      TC *c = place (C, sizeof (TC), n, o, where);                            \
      for (int i = 0; i < n; i++) { a[i] = GENA (); b[i] = GENB (); }         \
      SET_CASE (NAME);                                                        \
      CALL;                                                                   \
      for (int i = 0; i < n; i++, checks++)                                   \
        { TC r; REF; if (!(OK)) fail (NAME, n, i, o); }                       \
      if (!sentinels_ok (C, c, n * sizeof (TC)))                              \
        fail (NAME " wrote outside", n, -1, o);                               \
    }

/* Reductions: the result must equal the in-order reference exactly.  */
#define CHECK_RED(T, NAME, GEN, CALL, INIT, STEP)                             \
  CASES                                                                       \
    {                                                                         \
      T *a = place (A, sizeof (T), n, o, where);                              \
      T *b = place (B, sizeof (T), n, o, where);                              \
      for (int i = 0; i < n; i++) { a[i] = GEN (); b[i] = GEN (); }           \
      SET_CASE (NAME);                                                        \
      T got = CALL, r = INIT;                                                 \
      for (int i = 0; i < n; i++) STEP;                                       \
      checks++;                                                               \
      if (!SAMEBITS (T, got, r)) fail (NAME, n, -1, o);                       \
    }

/* Gathers: a table of nb elements flush against a guard page, indices
   covering both ends with duplicates.  Masked forms point the indices of
   inactive lanes into a guard page and expect c unchanged there.  */
#define CHECK_GAT(T, NAME, GEN, MASKED, CALL)                                 \
  CASES                                                                       \
    {                                                                         \
      int nb = 1 + (int) (rnd () % 64);                                       \
      T *b = place (TBL, sizeof (T), nb, o, where);                             \
      T *c = place (C, sizeof (T), n, o, where);                              \
      int *idx = place (I, sizeof (int), n, o, where);                        \
      int *m = place (M, sizeof (int), n, o, where);                          \
      T old[MAXN + 1];                                                        \
      for (int i = 0; i < nb; i++) b[i] = GEN ();                             \
      for (int i = 0; i < n; i++)                                             \
        {                                                                     \
          idx[i] = i == 0 ? nb - 1 : i == 1 ? 0 : (int) (rnd () % nb);        \
          m[i] = MASKED ? (int) (rnd () & 1) : 1;                             \
          if (!m[i]) idx[i] = bad_index (TBL, b, sizeof (T));                   \
          c[i] = old[i] = GEN ();                                             \
        }                                                                     \
      SET_CASE (NAME);                                                        \
      CALL;                                                                   \
      for (int i = 0; i < n; i++, checks++)                                   \
        {                                                                     \
          T r = m[i] ? b[idx[i]] : old[i];                                    \
          if (!SAMEBITS (T, c[i], r)) fail (NAME, n, i, o);                   \
        }                                                                     \
      if (!sentinels_ok (C, c, n * sizeof (T)))                               \
        fail (NAME " wrote outside", n, -1, o);                               \
    }

/* Scatters into c[0..n): a permutation, or random indices with duplicates
   (the last write in source order wins).  */
#define CHECK_SCA(T, NAME, GEN, MASKED, CALL)                                 \
  for (int dup = 0; dup < 2; dup++)                                           \
    CASES                                                                     \
      {                                                                       \
        T *b = place (B, sizeof (T), n, o, where);                            \
        T *c = place (C, sizeof (T), n, o, where);                            \
        int *idx = place (I, sizeof (int), n, o, where);                      \
        int *m = place (M, sizeof (int), n, o, where);                        \
        T r[MAXN + 1];                                                        \
        for (int i = 0; i < n; i++)                                           \
          { b[i] = GEN (); c[i] = r[i] = GEN (); idx[i] = i;                  \
            m[i] = MASKED ? (int) (rnd () & 1) : 1; }                         \
        for (int i = n - 1; i > 0; i--)                                       \
          {                                                                   \
            int j = dup ? (int) (rnd () % n) : (int) (rnd () % (i + 1));      \
            if (dup) idx[i] = j;                                              \
            else { int t = idx[i]; idx[i] = idx[j]; idx[j] = t; }             \
          }                                                                   \
        for (int i = 0; i < n; i++)                                           \
          if (m[i]) r[idx[i]] = b[i];                                         \
          else idx[i] = bad_index (C, c, sizeof (T));                         \
        SET_CASE (NAME);                                                      \
        CALL;                                                                 \
        for (int i = 0; i < n; i++, checks++)                                 \
          if (!SAMEBITS (T, c[i], r[i])) fail (NAME, n, i, o);                \
        if (!sentinels_ok (C, c, n * sizeof (T)))                             \
          fail (NAME " wrote outside", n, -1, o);                             \
      }

/* FP64 correct rounding, decided exactly in 128-bit integers (no libm, no
   x87 rounding), for normal operands and results.  x = m 2^e with m a
   53-bit integer.  */
typedef unsigned __int128 u128;
static void
split (double x, uint64_t *m, int *e)
{
  int k;
  *m = (uint64_t) ldexp (frexp (fabs (x), &k), 53);
  *e = k - 53;
}
static u128
shl (u128 v, int s)
{
  return s < 0 || s > 120 ? 0 : v << s;
}
/* Division: q = RN(a/b) iff |a - q b| < |b| g / 2, where g is the gap from
   q to its neighbour on the side of a/b (2^eq, or 2^(eq-1) below a power of
   two).  A quotient of doubles is never a midpoint, so there are no ties.
   Scaled by 2^-E with E = min(ea, eq + eb) - 1, every term is an integer.  */
static int
div_ok (double a, double b, double q)
{
  if (!isnormal (q) || signbit (q) != (signbit (a) ^ signbit (b))) return 0;
  uint64_t ma, mb, mq; int ea, eb, eq;
  split (a, &ma, &ea); split (b, &mb, &eb); split (q, &mq, &eq);
  int E = (ea < eq + eb ? ea : eq + eb) - 1;
  if (ea - E > 70 || eq + eb - E > 20) return 0;
  u128 x = shl (ma, ea - E), y = shl ((u128) mq * mb, eq + eb - E);
  int up = x > y;                      /* a/b lies above q */
  u128 r = up ? x - y : y - x;
  int g = eq - (!up && mq == (1ull << 52));
  return 2 * r < shl (mb, eb + g - E);
}
/* Square root: q = RN(sqrt a) iff (2q - gd)^2 < 4a < (2q + gu)^2, with
   gu = 2^eq and gd = 2^eq or 2^(eq-1) when mq is a power of two.  */
static int
sqrt_ok (double a, double q)
{
  if (!isnormal (q) || q < 0) return 0;
  uint64_t ma, mq; int ea, eq;
  split (a, &ma, &ea); split (q, &mq, &eq);
  int pow2 = mq == (1ull << 52);
  u128 hi = (u128) (2 * mq + 1) * (2 * mq + 1);                     /* 2^(2eq) */
  u128 lo = pow2 ? (u128) (4 * mq - 1) * (4 * mq - 1)               /* 2^(2eq-2) */
                 : (u128) (2 * mq - 1) * (2 * mq - 1);              /* 2^(2eq) */
  int elo = pow2 ? 2 * eq - 2 : 2 * eq;
  int E = elo < ea + 2 ? elo : ea + 2;
  if (ea + 2 - E > 70 || 2 * eq - E > 2) return 0;
  u128 four_a = shl (ma, ea + 2 - E);
  return shl (lo, elo - E) < four_a && four_a < shl (hi, 2 * eq - E);
}
static double
dpos (void)
{
  return fabs (ddiv_in ());
}
static double
dspec (void)
{
  return dspecial[rnd () % NSPEC];
}

int
main (void)
{
  page = sysconf (_SC_PAGESIZE);
  struct sigaction sa;
  memset (&sa, 0, sizeof sa);
  sa.sa_sigaction = on_fault;
  sa.sa_flags = SA_SIGINFO;
  sigaction (SIGSEGV, &sa, 0);
  sigaction (SIGBUS, &sa, 0);
  A = guarded (); B = guarded (); C = guarded (); D = guarded ();
  I = guarded (); M = guarded (); TBL = guarded ();

  /* Conversions.  */
  CHECK_EW (float, int, int, "cvt_i32_f32", ibits, ibits, cvt_i32_f32 (c, a, n),
            r = (float) a[i], BITS_OK (float))
  CHECK_EW (float, unsigned, int, "cvt_u32_f32", ubits, ibits, cvt_u32_f32 (c, a, n),
            r = (float) a[i], BITS_OK (float))
  CHECK_EW (int, float, int, "cvt_f32_i32", fconv, ibits, cvt_f32_i32 (c, a, n),
            r = (int) a[i], BITS_OK (int))
  if (!s5_ops_fast_math)  /* DAZ and FTZ change subnormal inputs and results */
    {
      CHECK_EW (double, float, int, "cvt_f32_f64", fbits, ibits, cvt_f32_f64 (c, a, n),
                r = a[i], FP_OK (double))
      CHECK_EW (float, double, int, "cvt_f64_f32", dbits, ibits, cvt_f64_f32 (c, a, n),
                r = (float) a[i], FP_OK (float))
    }
  CHECK_EW (double, int, int, "cvt_i32_f64", ibits, ibits, cvt_i32_f64 (c, a, n),
            r = a[i], BITS_OK (double))
  CHECK_EW (int, double, int, "cvt_f64_i32", inrange, ibits, cvt_f64_i32 (c, a, n),
            r = (int) a[i], BITS_OK (int))
  CHECK_EW (double, long, int, "cvt_i64_f64", lbits, ibits, cvt_i64_f64 (c, a, n),
            r = (double) a[i], BITS_OK (double))
  CHECK_EW (double, float, double, "mix_f32_f64", fexact, dexact, mix_f32_f64 (c, a, b, n),
            r = a[i] * b[i], BITS_OK (double))

  /* Permutes.  */
  CHECK_EW (float, float, int, "rev_f32", fbits, ibits, rev_f32 (c, a, n),
            r = a[n - 1 - i], BITS_OK (float))
  CHECK_EW (double, double, int, "rev_f64", dbits, ibits, rev_f64 (c, a, n),
            r = a[n - 1 - i], BITS_OK (double))
  CHECK_EW (int, int, int, "rev_i32", ibits, ibits, rev_i32 (c, a, n),
            r = a[n - 1 - i], BITS_OK (int))
  CASES
    {
      float *a = place (A, 4, 2 * n, o, where), *b = place (B, 4, 2 * n, o, where);
      float *c = place (C, 4, 2 * n, o, where);
      for (int i = 0; i < 2 * n; i++) { a[i] = fsmall (); b[i] = fsmall (); }
      SET_CASE ("cmul_f32");
      cmul_f32 (c, a, b, n);
      for (int i = 0; i < n; i++, checks += 2)
        {
          float re = a[2 * i] * b[2 * i] - a[2 * i + 1] * b[2 * i + 1];
          float im = a[2 * i] * b[2 * i + 1] + a[2 * i + 1] * b[2 * i];
          if (!SAMEBITS (float, c[2 * i], re) || !SAMEBITS (float, c[2 * i + 1], im))
            fail ("cmul_f32", n, i, o);
        }
      if (!sentinels_ok (C, c, 8 * n)) fail ("cmul_f32 wrote outside", n, -1, o);
    }
  CASES
    {
      float *z = place (A, 4, 2 * n, o, where);
      float *re = place (C, 4, n, o, where), *im = place (D, 4, n, o, where);
      for (int i = 0; i < 2 * n; i++) z[i] = fbits ();
      SET_CASE ("deint_f32");
      deint_f32 (re, im, z, n);
      for (int i = 0; i < n; i++, checks++)
        if (!SAMEBITS (float, re[i], z[2 * i]) || !SAMEBITS (float, im[i], z[2 * i + 1]))
          fail ("deint_f32", n, i, o);
      if (!sentinels_ok (C, re, 4 * n) || !sentinels_ok (D, im, 4 * n))
        fail ("deint_f32 wrote outside", n, -1, o);
    }
  CASES
    {
      float *re = place (A, 4, n, o, where), *im = place (B, 4, n, o, where);
      float *z = place (C, 4, 2 * n, o, where);
      for (int i = 0; i < n; i++) { re[i] = fbits (); im[i] = fbits (); }
      SET_CASE ("inter_f32");
      inter_f32 (z, re, im, n);
      for (int i = 0; i < n; i++, checks++)
        if (!SAMEBITS (float, re[i], z[2 * i]) || !SAMEBITS (float, im[i], z[2 * i + 1]))
          fail ("inter_f32", n, i, o);
      if (!sentinels_ok (C, z, 8 * n)) fail ("inter_f32 wrote outside", n, -1, o);
    }

  /* Reductions.  */
  CHECK_RED (int, "sum_i32", ibits, sum_i32 (a, n), 0, r = (int) ((unsigned) r + (unsigned) a[i]))
  CHECK_RED (long, "sum_i64", lbits, sum_i64 (a, n), 0,
             r = (long) ((unsigned long) r + (unsigned long) a[i]))
  CHECK_RED (int, "min_i32", ibits, min_i32 (a, n), 0x7fffffff, r = a[i] < r ? a[i] : r)
  CHECK_RED (int, "max_i32", ibits, max_i32 (a, n), -0x7fffffff - 1, r = a[i] > r ? a[i] : r)
  CHECK_RED (unsigned, "max_u32", ubits, max_u32 (a, n), 0, r = a[i] > r ? a[i] : r)
  CHECK_RED (int, "and_i32", ibits, and_i32 (a, n), -1, r &= a[i])
  CHECK_RED (int, "or_i32", ibits, or_i32 (a, n), 0, r |= a[i])
  CHECK_RED (int, "xor_i32", ibits, xor_i32 (a, n), 0, r ^= a[i])
  CHECK_RED (float, "sum_f32", fexact, sum_f32 (a, n), 0.0f, r += a[i])
  CHECK_RED (double, "sum_f64", dexact, sum_f64 (a, n), 0.0, r += a[i])
  CHECK_RED (float, "dot_f32", fsmall, dot_f32 (a, b, n), 0.0f, r += a[i] * b[i])
  CHECK_RED (float, "maxf_f32", fexact, maxf_f32 (a, n), -INFINITY, r = a[i] > r ? a[i] : r)

  /* Gather and scatter.  */
  CHECK_GAT (float, "gat_f32", fbits, 0, gat_f32 (c, b, idx, n))
  CHECK_GAT (double, "gat_f64", dbits, 0, gat_f64 (c, b, idx, n))
  CHECK_GAT (int, "gat_i32", ibits, 0, gat_i32 (c, b, idx, n))
  CHECK_GAT (long, "gat_i64", lbits, 0, gat_i64 (c, b, idx, n))
  CHECK_GAT (float, "mgat_f32", fbits, 1, mgat_f32 (c, m, b, idx, n))
  CHECK_GAT (double, "mgat_f64", dbits, 1, mgat_f64 (c, m, b, idx, n))
  CHECK_SCA (float, "sca_f32", fbits, 0, sca_f32 (c, b, idx, n))
  CHECK_SCA (double, "sca_f64", dbits, 0, sca_f64 (c, b, idx, n))
  CHECK_SCA (float, "msca_f32", fbits, 1, msca_f32 (c, m, b, idx, n))

  /* Division and square root.  Scalar x87 code on the card runs at 64-bit
     precision, so its FP64 results are rounded twice and may miss correct
     rounding (S5-03); an element equal to that x87 result came from a
     scalar peel or remainder and is accepted.  Under -ffast-math these are
     not checked: DAZ, FTZ and reciprocal approximation are allowed there.  */
  if (s5_ops_fast_math)
    printf ("INFO div/sqrt and FP32/FP64 conversion checks skipped (-ffast-math)\n");
  else
    {
      CHECK_EW (float, float, float, "div_f32", fdiv_in, fdiv_in, div_f32 (c, a, b, n),
                r = (float) ((double) a[i] / (double) b[i]), FP_OK (float))
      CHECK_EW (float, float, int, "sqrt_f32", fdiv_in, ibits, sqrt_f32 (c, a, n),
                r = (float) sqrt ((double) a[i]), FP_OK (float))
      CHECK_EW (double, double, double, "div_f64", ddiv_in, ddiv_in, div_f64 (c, a, b, n),
                r = (double) ((long double) a[i] / b[i]),
                div_ok (a[i], b[i], c[i]) || BITS_OK (double))
      CHECK_EW (double, double, int, "sqrt_f64", dpos, ibits, sqrt_f64 (c, a, n),
                r = (double) sqrtl (a[i]), sqrt_ok (a[i], c[i]) || BITS_OK (double))
      /* Special operands: zeros, infinities, NaN, extremes, negative roots.  */
      CHECK_EW (double, double, double, "div_f64_special", dspec, dbits, div_f64 (c, a, b, n),
                r = (double) ((long double) a[i] / b[i]),
                FP_OK (double) || (isnormal (r) && div_ok (a[i], b[i], c[i])))
      CHECK_EW (double, double, int, "sqrt_f64_special", dspec, ibits, sqrt_f64 (c, a, n),
                r = sqrt (a[i]), FP_OK (double))
    }

  printf ("INFO checks=%lu\n", checks);
  if (failures)
    {
      printf ("S5-OPS FAIL failures=%lu\n", failures);
      return 1;
    }
  printf ("S5-OPS PASS failures=0\n");
  return 0;
}
