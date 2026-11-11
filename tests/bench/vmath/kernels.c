/* S10-04: the timed loops of the vector math measurement (ADR-0014, ADR-0010).

   tools/s10_04_vmath_bench.py compiles this file twice with the installed driver:
     -O2 -march=knc -fno-math-errno -DBUILD=vec                     calls libknc_vmath
     -O2 -march=knc -fno-math-errno -fno-tree-vectorize -DBUILD=scl  scalar libm
   Every kernel has one signature so that the driver can keep them in one table:
   out[i] = f (a[i], b[i], c[i]) for i < n, with the inputs it does not use ignored.  */
#include <math.h>

#define CAT2(a, b) a##_##b
#define CAT(a, b) CAT2 (a, b)
#define KERNEL(name) \
  void CAT (name, BUILD) (void *restrict out_, const void *restrict a_, \
                          const void *restrict b_, const void *restrict c_, int n)

#define UNARY(name, type) \
  KERNEL (name) \
  { \
    type *restrict out = out_; \
    const type *restrict a = a_; \
    (void) b_, (void) c_; \
    for (int i = 0; i < n; i++) \
      out[i] = name (a[i]); \
  }
#define BINARY(name, type) \
  KERNEL (name) \
  { \
    type *restrict out = out_; \
    const type *restrict a = a_, *restrict b = b_; \
    (void) c_; \
    for (int i = 0; i < n; i++) \
      out[i] = name (a[i], b[i]); \
  }

UNARY (expf, float)
UNARY (logf, float)
BINARY (powf, float)
UNARY (exp, double)
UNARY (log, double)
BINARY (pow, double)

/* A WRF-shaped column diagnostic: equivalent potential temperature (Bolton 1980, eqs. 15, 22,
   43), as WRF's post-processing computes it, from temperature a (K), pressure b (Pa) and water
   vapour mixing ratio c (kg/kg) at every point of a column tile.  It mixes powf with a varying
   exponent, logf and expf with the divides and multiplies around them.  */
KERNEL (column)
{
  float *restrict out = out_;
  const float *restrict t = a_, *restrict p = b_, *restrict q = c_;
  for (int i = 0; i < n; i++)
    {
      float r = q[i] * 1000.0f;                          /* g/kg */
      float e = q[i] * p[i] / (0.622f + q[i]) * 0.01f;   /* vapour pressure, hPa */
      float tl = 2840.0f / (3.5f * logf (t[i]) - logf (e) - 4.805f) + 55.0f;
      float theta = t[i] * powf (100000.0f / p[i], 0.2854f * (1.0f - 0.00028f * r));
      out[i] = theta * expf ((3.376f / tl - 0.00254f) * r * (1.0f + 0.00081f * r));
    }
}
