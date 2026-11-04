#include "knc-abi-gaps.h"
#include <fenv.h>

/* Distinct real/imaginary transformations expose swaps and lost components. */
_Complex float scalar_cf(_Complex float x)
{ return __builtin_complex(__real__ x + 0.5f, __imag__ x - 0.25f); }
_Complex double scalar_cd(_Complex double x)
{ return __builtin_complex(__real__ x + 0.25, __imag__ x - 0.5); }
_Complex long double scalar_cld(_Complex long double x)
{ return __builtin_complex(__real__ x + 0.5L, __imag__ x - 0.25L); }

/* Volatile double stores force rounding out of x87's extended precision.
   Arguments cross the compiler boundary; neither sum can be folded. */
int scalar_round(double x, double delta, double *positive, double *negative)
{
  volatile double p = x + delta;
  volatile double n = -x - delta;
  *positive = p;
  *negative = n;
  return fegetround();
}
