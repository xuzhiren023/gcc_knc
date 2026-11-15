/* S13-06 trial loops for knc-twin: compiled by the frozen GCC-KNC prefix at
   -O2 -march=knc (trial.s); no native time exists for them. */
void saxpy(unsigned long n, float a, const float *restrict xx, float *restrict yy)
{
  const float *restrict x = __builtin_assume_aligned(xx, 64);
  float *restrict y = __builtin_assume_aligned(yy, 64);
  for (unsigned long i = 0; i < n; ++i)
    y[i] = a * x[i] + y[i];
}

float fsum(unsigned long n, const float *restrict xx)
{
  const float *restrict x = __builtin_assume_aligned(xx, 64);
  float s = 0;
  for (unsigned long i = 0; i < n; ++i)
    s += x[i];
  return s;
}

/* stencil1 of tests/acceptance/m2_kernels/kernels.c */
void stencil1(unsigned long n, const float *restrict xx, float *restrict yy)
{
  float *restrict y = __builtin_assume_aligned(yy, 64);
  const float *restrict x = __builtin_assume_aligned(xx, 64);
  for (unsigned long i = 0; i < n; ++i)
    y[i] = (x[(long)i - 1] + x[i]) + x[i + 1];
}
