// S10-03 / ADR-0014 point 2: -mphinix adds -fno-math-errno, so with no errno
// flag given the loop of knc-vmath-call.c calls the 16-lane entry point of
// libknc_vmath.
// options: -O2 -march=knc -mphinix
// scan-asm-func vmath_expf: \bcall\s+__knc_vmath_expf_16\b
#include <math.h>

void
vmath_expf (float *restrict out, const float *restrict in, int n)
{
  for (int i = 0; i < n; i++)
    out[i] = expf (in[i]);
}
