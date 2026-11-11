// S10-09: with -fmath-errno (the C default) sqrt may set errno, so the
// loop of knc-divsqrt-f64.c keeps its scalar x87 square root.
// options: -O2 -march=knc
// scan-asm-func sqrt_f64: \bfsqrt\b
// scan-asm-not: \bvrsqrt23ps\b|\bvfixupnanpd\b

void
sqrt_f64 (double *restrict c, const double *restrict a)
{
  c = __builtin_assume_aligned (c, 64);
  a = __builtin_assume_aligned (a, 64);
  for (int i = 0; i < 1024; ++i)
    c[i] = __builtin_sqrt (a[i]);
}
