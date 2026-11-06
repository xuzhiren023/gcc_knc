/* Reduced from gcc.dg/vect/pr114322.c; S6-07 baseline ICE. */
int
foo (int *A, int *B, int x, int stride)
{
  int sum = 0;
  if (stride > 1)
    {
      for (int i = 0; i < 1024; ++i)
        sum += A[(i + x) * stride] + B[i];
    }
  return sum;
}
