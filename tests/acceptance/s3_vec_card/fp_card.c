/* Card check for S3-06: packed V16SF/V8DF add, sub, mul, broadcast and FMA.

   Inputs are small multiples of 1/4, so add, sub and mul are exact in
   both types and x87 excess precision cannot change the scalar reference.
   The FMA case uses a, b, c where a fused multiply-add and a separate
   multiply then add differ (fused: 2^-24 for float, 2^-54 for double;
   unfused: 0); the long double reference gets the fused value.  FMA is
   only checked when optimizing, since -O0 does not contract.

   Build: xgcc -B<build>/gcc/ -O0|-O2 -march=knc fp_card.c -o fp_card.  */

#include <stdio.h>
#include <string.h>

static unsigned long cases, failures;

static void
check (const char *what, int type, const void *got, const void *want)
{
  cases++;
  if (memcmp (got, want, 64) && failures++ < 20)
    printf ("FAIL %s type=%d\n", what, type);
}

#define DEFINE_FP(ID, T, N, EPS)                                              \
  typedef T v##ID __attribute__ ((vector_size (64)));                         \
  __attribute__ ((noipa)) static void                                         \
  add_##ID (v##ID *r, const v##ID *a, const v##ID *b) { *r = *a + *b; }       \
  __attribute__ ((noipa)) static void                                         \
  sub_##ID (v##ID *r, const v##ID *a, const v##ID *b) { *r = *a - *b; }       \
  __attribute__ ((noipa)) static void                                         \
  mul_##ID (v##ID *r, const v##ID *a, const v##ID *b) { *r = *a * *b; }       \
  __attribute__ ((noipa)) static void                                         \
  scale_##ID (v##ID *r, const v##ID *a, T s) { *r = *a * s; }                 \
  __attribute__ ((noipa)) static void                                         \
  fma_##ID (v##ID *r, const v##ID *a, const v##ID *b, const v##ID *c)         \
  {                                                                           \
    *r = *a * *b + *c;                                                        \
  }                                                                           \
  static void                                                                 \
  run_##ID (int type)                                                         \
  {                                                                           \
    static v##ID a, b, c, r;                                                  \
    T x[N], y[N], w[N];                                                       \
    for (int i = 0; i < N; i++)                                               \
      {                                                                       \
        x[i] = (T) (i + 1) * (T) 0.25;                                        \
        y[i] = (T) (N - i) * (T) -0.5;                                        \
      }                                                                       \
    memcpy (&a, x, 64);                                                       \
    memcpy (&b, y, 64);                                                       \
    for (int i = 0; i < N; i++)                                               \
      w[i] = (T) ((long double) x[i] + y[i]);                                 \
    add_##ID (&r, &a, &b);                                                    \
    check ("add", type, &r, w);                                               \
    for (int i = 0; i < N; i++)                                               \
      w[i] = (T) ((long double) x[i] - y[i]);                                 \
    sub_##ID (&r, &a, &b);                                                    \
    check ("sub", type, &r, w);                                               \
    for (int i = 0; i < N; i++)                                               \
      w[i] = (T) ((long double) x[i] * y[i]);                                 \
    mul_##ID (&r, &a, &b);                                                    \
    check ("mul", type, &r, w);                                               \
    volatile T s = (T) 1.5;                                                   \
    for (int i = 0; i < N; i++)                                               \
      w[i] = (T) ((long double) x[i] * s);                                    \
    scale_##ID (&r, &a, s);                                                   \
    check ("broadcast-mul", type, &r, w);                                     \
    if (OPTIMIZING)                                                           \
      {                                                                       \
        T e = (T) 1 + EPS, f = -((T) 1 + 2 * EPS);                            \
        for (int i = 0; i < N; i++)                                           \
          {                                                                   \
            x[i] = e;                                                         \
            y[i] = f;                                                         \
            w[i] = (T) ((long double) e * e + f);                             \
          }                                                                   \
        memcpy (&a, x, 64);                                                   \
        memcpy (&c, y, 64);                                                   \
        fma_##ID (&r, &a, &a, &c);                                            \
        check ("fma", type, &r, w);                                           \
        if (w[0] == 0 && failures++ < 20)                                     \
          printf ("FAIL fma-reference type=%d\n", type);                      \
      }                                                                       \
  }

#ifdef __OPTIMIZE__
#define OPTIMIZING 1
#else
#define OPTIMIZING 0
#endif

DEFINE_FP (sf, float, 16, 0x1p-12f)
DEFINE_FP (df, double, 8, 0x1p-27)

int
main (void)
{
  run_sf (0);
  run_df (1);
  printf ("S3-FP %s cases=%lu failures=%lu\n", failures ? "FAIL" : "PASS",
          cases, failures);
  return failures != 0;
}
