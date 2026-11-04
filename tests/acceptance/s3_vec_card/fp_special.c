/* Card probe: FP state and special values for KNC packed FP (S3-06 onward).

   Reports, rather than assumes:
   - MXCSR and the x87 control word at startup, without fast-math;
   - CPUID leaf 1 SSE/SSE2 bits (libgfortran's fpu-387.h writes MXCSR
     exception masks, reserved on KNC, when CPUID reports SSE);
   - V16SF and V8DF add, sub, mul on signed zeros, infinities, NaN, the
     smallest normal and subnormals, each lane against an x87 long double
     reference rounded to the element type (NaN matches NaN, zeros must
     match in sign);
   - which exception flags fetestexcept sees after vector and scalar ops.

   Prints INFO lines and one summary line; exits 0 only if every lane
   matches.  Build: xgcc -B<build>/gcc/ -O0|-O2 -march=knc fp_special.c -lm  */

#include <cpuid.h>
#include <fenv.h>
#include <float.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

static unsigned long cases, failures;

#define DEFINE_SPECIAL(ID, T, N, MIN, TRUE_MIN, MAX, FMT)                     \
  typedef T v##ID __attribute__ ((vector_size (64)));                         \
  __attribute__ ((noipa)) static void                                         \
  add_##ID (v##ID *r, const v##ID *a, const v##ID *b) { *r = *a + *b; }       \
  __attribute__ ((noipa)) static void                                         \
  sub_##ID (v##ID *r, const v##ID *a, const v##ID *b) { *r = *a - *b; }       \
  __attribute__ ((noipa)) static void                                         \
  mul_##ID (v##ID *r, const v##ID *a, const v##ID *b) { *r = *a * *b; }       \
  __attribute__ ((noipa)) static T                                            \
  sadd_##ID (T a, T b) { return a + b; }                                      \
  __attribute__ ((noipa)) static T                                            \
  smul_##ID (T a, T b) { return a * b; }                                      \
                                                                              \
  static int                                                                  \
  same_##ID (T x, T y)                                                        \
  {                                                                           \
    if (isnan (x) || isnan (y))                                               \
      return isnan (x) && isnan (y);                                          \
    return memcmp (&x, &y, sizeof x) == 0;                                    \
  }                                                                           \
                                                                              \
  static void                                                                 \
  lanes_##ID (const char *op, const T *a, const T *b, const T *got)           \
  {                                                                           \
    for (int i = 0; i < N; i++)                                               \
      {                                                                       \
        long double x = a[i], y = b[i];                                       \
        T want = op[0] == 'a' ? (T) (x + y) : op[0] == 's' ? (T) (x - y)      \
                                            : (T) (x * y);                    \
        cases++;                                                              \
        if (!same_##ID (got[i], want))                                        \
          {                                                                   \
            failures++;                                                       \
            printf ("MISMATCH " #ID " %s lane %d: " FMT " op " FMT            \
                    " = " FMT ", x87 reference " FMT "\n",                    \
                    op, i, a[i], b[i], got[i], want);                         \
          }                                                                   \
      }                                                                       \
  }                                                                           \
                                                                              \
  static void                                                                 \
  flags_##ID (const char *what, int vector, T a, T b, int mul)                \
  {                                                                           \
    static v##ID va, vb, vr;                                                  \
    T x[N], y[N];                                                             \
    for (int i = 0; i < N; i++)                                               \
      x[i] = a, y[i] = b;                                                     \
    memcpy (&va, x, 64);                                                      \
    memcpy (&vb, y, 64);                                                      \
    feclearexcept (FE_ALL_EXCEPT);                                            \
    volatile T s;                                                             \
    if (vector)                                                               \
      (mul ? mul_##ID : add_##ID) (&vr, &va, &vb);                            \
    else                                                                      \
      s = mul ? smul_##ID (a, b) : sadd_##ID (a, b);                          \
    (void) s;                                                                 \
    int f = fetestexcept (FE_ALL_EXCEPT);                                     \
    printf ("INFO flags " #ID " %-9s %s:%s%s%s%s%s\n", what,                  \
            vector ? "vector" : "x87   ", f & FE_INVALID ? " invalid" : "",   \
            f & FE_DIVBYZERO ? " divbyzero" : "",                             \
            f & FE_OVERFLOW ? " overflow" : "",                               \
            f & FE_UNDERFLOW ? " underflow" : "",                             \
            f & FE_INEXACT ? " inexact" : "");                                \
  }                                                                           \
                                                                              \
  static void                                                                 \
  run_##ID (void)                                                             \
  {                                                                           \
    static const T a[16] = { 0.0, -0.0, 0.0, -0.0, INFINITY, -INFINITY,       \
                             INFINITY, NAN, 1.0, MIN, MIN, TRUE_MIN,          \
                             -TRUE_MIN, MAX, 3 * TRUE_MIN, MIN / 2 };         \
    static const T b[16] = { -0.0, -0.0, 0.0, 0.0, 1.0, INFINITY,             \
                             -INFINITY, 1.0, -1.0, (T) 0.5, -MIN, (T) 1.0,    \
                             TRUE_MIN, MAX, (T) 0.25, MIN / 4 };              \
    static v##ID va, vb, vr;                                                  \
    T got[N];                                                                 \
    for (int base = 0; base < 16; base += N)                                  \
      {                                                                       \
        memcpy (&va, a + base, 64);                                           \
        memcpy (&vb, b + base, 64);                                           \
        add_##ID (&vr, &va, &vb);                                             \
        memcpy (got, &vr, 64);                                                \
        lanes_##ID ("add", a + base, b + base, got);                          \
        sub_##ID (&vr, &va, &vb);                                             \
        memcpy (got, &vr, 64);                                                \
        lanes_##ID ("sub", a + base, b + base, got);                          \
        mul_##ID (&vr, &va, &vb);                                             \
        memcpy (got, &vr, 64);                                                \
        lanes_##ID ("mul", a + base, b + base, got);                          \
      }                                                                       \
    for (int v = 1; v >= 0; v--)                                              \
      {                                                                       \
        flags_##ID ("exact", v, (T) 1.0, (T) 2.0, 0);                         \
        flags_##ID ("inexact", v, (T) 1.0, (T) 1e-30, 0);                     \
        flags_##ID ("inf-inf", v, INFINITY, -INFINITY, 0);                    \
        flags_##ID ("overflow", v, MAX, (T) 4.0, 1);                          \
        flags_##ID ("underflow", v, MIN, (T) 0.25, 1);                        \
      }                                                                       \
  }

/* 16 lanes for float; double uses the first 8 of the same table.  */
DEFINE_SPECIAL (sf, float, 16, FLT_MIN, FLT_TRUE_MIN, FLT_MAX, "%a")
DEFINE_SPECIAL (df, double, 8, DBL_MIN, DBL_TRUE_MIN, DBL_MAX, "%a")

int
main (void)
{
  unsigned int mxcsr;
  unsigned short cw;
  __asm__ volatile ("stmxcsr %0" : "=m" (mxcsr));
  __asm__ volatile ("fnstcw %0" : "=m" (cw));
  printf ("INFO startup mxcsr=0x%08x x87cw=0x%04x\n", mxcsr, cw);
  unsigned int eax, ebx, ecx, edx;
  if (__get_cpuid (1, &eax, &ebx, &ecx, &edx))
    printf ("INFO cpuid1 eax=0x%08x edx=0x%08x sse=%u sse2=%u\n", eax, edx,
            (edx >> 25) & 1, (edx >> 26) & 1);
  else
    printf ("INFO cpuid1 unavailable\n");
  run_sf ();
  run_df ();
  printf ("S3-FPSPECIAL %s cases=%lu failures=%lu\n",
          failures ? "FAIL" : "PASS", cases, failures);
  return failures != 0;
}
