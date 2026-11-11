// S10-03 / ADR-0014 point 2: with -fmath-errno (the C default) expf may set
// errno, so the loop of knc-vmath-call.c stays a scalar call of expf.
// options: -O2 -march=knc -fmath-errno
// scan-asm-func vmath_expf: \bcall\s+expf\b
// scan-asm-not: __knc_vmath
#include <math.h>

void
vmath_expf (float *restrict out, const float *restrict in, int n)
{
  for (int i = 0; i < n; i++)
    out[i] = expf (in[i]);
}
