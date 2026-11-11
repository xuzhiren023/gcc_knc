// S10-03 / ADR-0014 points 2-3: loops over the v0 vector math set, for the card.
// check.py t2 --vmath (tools/knc_vmath.py) compiles this file twice with the
// installed driver and links the two objects with -lm and no other library:
//   -O2 -march=knc -fno-math-errno -DVMATH_VECTOR   the loops call libknc_vmath
//   -O2 -march=knc                                  the same loops on scalar libm, and main
// Each vector result must be within 1 ULP of the scalar one (the S10-02 limit),
// with the same NaNs and signed zeros.
#include <float.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#ifdef VMATH_VECTOR
#define LOOP(name) vmath_vector_##name
#else
#define LOOP(name) vmath_scalar_##name
#endif

#define LOOP1(name, type) \
  void LOOP (name) (type *restrict out, const type *restrict x, int n) \
  { for (int i = 0; i < n; i++) out[i] = name (x[i]); }
#define LOOP2(name, type) \
  void LOOP (name) (type *restrict out, const type *restrict x, \
                    const type *restrict y, int n) \
  { for (int i = 0; i < n; i++) out[i] = name (x[i], y[i]); }

LOOP1 (expf, float)
LOOP1 (logf, float)
LOOP2 (powf, float)
LOOP1 (exp, double)
LOOP1 (log, double)
LOOP2 (pow, double)

#ifndef VMATH_VECTOR
#define VECTOR1(name, type) \
  void vmath_vector_##name (type *restrict, const type *restrict, int);
#define VECTOR2(name, type) \
  void vmath_vector_##name (type *restrict, const type *restrict, \
                            const type *restrict, int);
VECTOR1 (expf, float)
VECTOR1 (logf, float)
VECTOR2 (powf, float)
VECTOR1 (exp, double)
VECTOR1 (log, double)
VECTOR2 (pow, double)

// 256 vectors of 16 and 3 more: every loop ends in a partial vector.
#define N 4099
#define COUNT(a) ((int) (sizeof (a) / sizeof (a)[0]))

// Special values, then the overflow and underflow boundaries of exp.
static const float special_f[] = {
  NAN, INFINITY, -INFINITY, 0.0f, -0.0f, 1.0f, -1.0f, FLT_MIN, -FLT_MIN,
  FLT_MAX, -FLT_MAX, 0x1p-149f, -0x1p-149f, 0x1.fffffcp-127f,
  88.72283f, 88.72284f, -87.33654f, -87.33655f, -103.2789f, -103.9721f,
  -103.9722f, -104.0f, 89.0f };
static const double special_d[] = {
  NAN, INFINITY, -INFINITY, 0.0, -0.0, 1.0, -1.0, DBL_MIN, -DBL_MIN,
  DBL_MAX, -DBL_MAX, 0x1p-1074, -0x1p-1074, 0x1.ffffffffffffep-1023,
  709.782712893384, 709.7827128933841, -708.3964185322641,
  -708.3964185322642, -744.4400719213812, -745.1332191019411,
  -745.1332191019412, -746.0, 710.0 };
// Every pair of these goes to pow.
static const double pow_x[] = {
  NAN, INFINITY, -INFINITY, 0.0, -0.0, 1.0, -1.0, 2.0, -2.0, 0.5, -0.5,
  0x1p-149, 0x1.fffffep127 };
static const double pow_y[] = {
  NAN, INFINITY, -INFINITY, 0.0, -0.0, 1.0, -1.0, 2.0, 3.0, -3.0, 0.5,
  -0.5, 0x1p40, 0x1p24 + 1.0 };

static float xf[N], yf[N], vf[N], sf[N];
static double xd[N], yd[N], vd[N], sd[N];
static uint64_t seed = 0x5eed10035eed1003;
static int failed;

static uint32_t
next (void)
{
  seed = seed * 6364136223846793005 + 1442695040888963407;
  return seed >> 32;
}

// A value in [low, high).
static double
range (double low, double high)
{
  return low + (high - low) * (next () / 4294967296.0);
}

// Order the bit patterns as the values are ordered; adjacent values differ by one.
static int64_t
order_f (float value)
{
  uint32_t bits;
  memcpy (&bits, &value, sizeof bits);
  return bits >> 31 ? -(int64_t) (bits & 0x7fffffff) : (int64_t) bits;
}

static int64_t
order_d (double value)
{
  uint64_t bits;
  memcpy (&bits, &value, sizeof bits);
  return bits >> 63 ? -(int64_t) (bits & INT64_MAX) : (int64_t) bits;
}

// ULPs between two results; UINT64_MAX when only one is a NaN or zeros differ in sign.
#define DISTANCE(suffix, type) \
  static uint64_t \
  distance_##suffix (type v, type s) \
  { \
    int64_t a = order_##suffix (v), b = order_##suffix (s); \
    if (v != v || s != s) \
      return v != v && s != s ? 0 : UINT64_MAX; \
    if (a == b) \
      return !signbit (v) == !signbit (s) ? 0 : UINT64_MAX; \
    return a > b ? (uint64_t) a - (uint64_t) b : (uint64_t) b - (uint64_t) a; \
  }
DISTANCE (f, float)
DISTANCE (d, double)

#define CHECK(suffix, type) \
  static void \
  check_##suffix (const char *name, const type *v, const type *s, \
                  const type *x, const type *y) \
  { \
    uint64_t worst = 0; \
    int differ = 0, at = 0; \
    for (int i = 0; i < N; i++) \
      { \
        uint64_t d = distance_##suffix (v[i], s[i]); \
        differ += d != 0; \
        if (d > worst) \
          worst = d, at = i; \
      } \
    printf ("S10-03 %s: %d lanes, %d differ, worst ", name, N, differ); \
    if (worst == UINT64_MAX) \
      printf ("is a NaN or zero-sign mismatch"); \
    else \
      printf ("%llu ULP", (unsigned long long) worst); \
    if (worst) \
      { \
        printf (" at x=%a", (double) x[at]); \
        if (y) \
          printf (" y=%a", (double) y[at]); \
        printf (": vector %a, scalar %a", (double) v[at], (double) s[at]); \
      } \
    puts (worst > 1 ? " FAIL" : " PASS"); \
    failed |= worst > 1; \
  }
CHECK (f, float)
CHECK (d, double)

int
main (void)
{
  int pairs = COUNT (pow_x) * COUNT (pow_y);

  // exp: the special values, then from below underflow to above overflow.
  for (int i = 0; i < N; i++)
    {
      xf[i] = i < COUNT (special_f) ? special_f[i] : (float) range (-110, 90);
      xd[i] = i < COUNT (special_d) ? special_d[i] : range (-750, 720);
    }
  vmath_vector_expf (vf, xf, N);
  vmath_scalar_expf (sf, xf, N);
  check_f ("expf", vf, sf, xf, 0);
  vmath_vector_exp (vd, xd, N);
  vmath_scalar_exp (sd, xd, N);
  check_d ("exp", vd, sd, xd, 0);

  // log: the special values, then every positive finite exponent, subnormals included.
  for (int i = COUNT (special_f); i < N; i++)
    {
      uint32_t bits = next () % 0x7f800000;
      memcpy (&xf[i], &bits, sizeof bits);
    }
  for (int i = COUNT (special_d); i < N; i++)
    {
      uint64_t bits = ((uint64_t) next () << 32 | next ()) % 0x7ff0000000000000;
      memcpy (&xd[i], &bits, sizeof bits);
    }
  vmath_vector_logf (vf, xf, N);
  vmath_scalar_logf (sf, xf, N);
  check_f ("logf", vf, sf, xf, 0);
  vmath_vector_log (vd, xd, N);
  vmath_scalar_log (sd, xd, N);
  check_d ("log", vd, sd, xd, 0);

  // pow: the special pairs, then positive bases with results from underflow to overflow.
  for (int i = 0; i < N; i++)
    {
      xf[i] = i < pairs ? (float) pow_x[i / COUNT (pow_y)] : (float) range (0.01, 20);
      yf[i] = i < pairs ? (float) pow_y[i % COUNT (pow_y)] : (float) range (-40, 40);
      xd[i] = i < pairs ? pow_x[i / COUNT (pow_y)] : range (0.01, 20);
      yd[i] = i < pairs ? pow_y[i % COUNT (pow_y)] : range (-300, 300);
    }
  vmath_vector_powf (vf, xf, yf, N);
  vmath_scalar_powf (sf, xf, yf, N);
  check_f ("powf", vf, sf, xf, yf);
  vmath_vector_pow (vd, xd, yd, N);
  vmath_scalar_pow (sd, xd, yd, N);
  check_d ("pow", vd, sd, xd, yd);

  puts (failed ? "S10-03 vmath loops FAIL" : "S10-03 vmath loops PASS");
  return failed;
}
#endif
