/* Compiled with the compiler under test, separately from driver.c, so the
   loops see runtime inputs and cannot be folded or specialized.  */
#include "affine.h"

void
affine_f32 (float *restrict y, const float *restrict x,
	    float a, float b, unsigned long n)
{
  for (unsigned long i = 0; i < n; ++i)
    y[i] = a * x[i] + b;
}

void
affine_f64 (double *restrict y, const double *restrict x,
	    double a, double b, unsigned long n)
{
  for (unsigned long i = 0; i < n; ++i)
    y[i] = a * x[i] + b;
}

void
recurrence_f32 (float *restrict y, const float *restrict x, unsigned long n)
{
  float prev = 0.0f;
  for (unsigned long i = 0; i < n; ++i)
    {
      prev = x[i] - prev;
      y[i] = prev;
    }
}
