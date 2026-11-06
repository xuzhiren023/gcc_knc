/* Reduced from gcc.dg/vect/vect-fmin-3.c; S6-07 baseline ICE. */
void __attribute__((noipa))
test (double x0, double x1, double *restrict res, double *restrict ptr, int n)
{
  for (int i = 0; i < n; i += 2)
    {
      x0 = __builtin_fmin (x0, ptr[i + 0]);
      x1 = __builtin_fmin (x1, ptr[i + 1]);
    }
  res[0] = x0;
  res[1] = x1;
}
#define N 128
#define HALF (N / 2)
