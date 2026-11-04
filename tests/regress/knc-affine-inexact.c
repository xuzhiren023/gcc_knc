/* S3-10: link against m1_affine/loops.c built at default
   -O2 -ftree-vectorize -march=knc (contraction enabled).
   Length-one calls to the same function take its scalar remainder; compare
   them with the long loop at all offsets, without requiring identical bits.
   This driver is a separate, unoptimized TU so the reference stays long double. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "affine.h"

static unsigned long failures;

#define PROBE(TAG, T, U, A, B, ONE, MASK)                                    \
static void probe_##TAG(void)                                               \
{                                                                          \
  static T x[96] __attribute__((aligned(64)));                               \
  static T y[96] __attribute__((aligned(64)));                               \
  static T scalar[96] __attribute__((aligned(64)));                          \
  volatile T a = A, b = B;                                                  \
  unsigned long seed = 1;                                                   \
  for (unsigned i = 0; i < 96; ++i)                                        \
    {                                                                      \
      seed = seed * 6364136223846793005UL + 1;                              \
      U bits = ONE | ((U)(seed >> 11) & MASK);                             \
      memcpy(x + i, &bits, sizeof bits);                                   \
    }                                                                      \
  for (unsigned off = 0; off < 16; ++off)                                  \
    {                                                                      \
      unsigned long differences = 0, checked = 0;                          \
      for (unsigned long n = 0; n <= 65; ++n)                              \
        {                                                                  \
          affine_##TAG(y + off, x + off, a, b, n);                         \
          for (unsigned long i = 0; i < n; ++i)                           \
            {                                                              \
              affine_##TAG(scalar + off + i, x + off + i, a, b, 1);       \
              volatile long double wide = (long double)a * x[off+i] + b; \
              volatile T want = (T)wide;                                  \
              U w, v, s;                                                   \
              memcpy(&w, (const void *)&want, sizeof w);                  \
              memcpy(&v, y + off + i, sizeof v);                           \
              memcpy(&s, scalar + off + i, sizeof s);                      \
              if (CONTROL_BIAS) v += 4;                                   \
              U dv = v > w ? v-w : w-v, ds = s > w ? s-w : w-s;           \
              if ((dv > 1 || ds > 1) && failures++ < 20)                  \
                printf("FAIL " #TAG " off=%u n=%lu i=%lu loop=%a "       \
                       "scalar=%a reference=%a loop-ulp=%llu scalar-ulp=%llu\n", \
                       off, n, i, (double)y[off+i], (double)scalar[off+i], \
                       (double)want, (unsigned long long)dv,               \
                       (unsigned long long)ds);                            \
              differences += v != s;                                      \
              checked++;                                                   \
            }                                                              \
        }                                                                  \
      printf("INFO " #TAG " offset=%u elements=%lu scalar-loop-differences=%lu\n", \
             off, checked, differences);                                   \
    }                                                                      \
}

#ifndef CONTROL_BIAS
#define CONTROL_BIAS 0
#endif
PROBE(f32, float, uint32_t, 1.234567f, 0.345678f,
      UINT32_C(0x3f800000), UINT32_C(0x007fffff))
PROBE(f64, double, uint64_t, 1.2345678901234567, 0.3456789012345678,
      UINT64_C(0x3ff0000000000000), UINT64_C(0x000fffffffffffff))

int main(void)
{
  probe_f32();
  probe_f64();
  printf("S3-INEXACT %s failures=%lu\n", failures ? "FAIL" : "PASS", failures);
  return failures != 0;
}
