// S6-04: the aligned dynamic remainder permits an IMCI masked epilogue.
// options: -O3 -fopt-info-vec
// scan-output: KNC candidate.*V16SF.*factor = 16
// scan-output: KNC candidate.*masked epilogue.*64-byte aligned
void report_tail (float *restrict y, const float *restrict x, int n)
{
  y = __builtin_assume_aligned (y, 64);
  x = __builtin_assume_aligned (x, 64);
  for (int i = 0; i < n; ++i)
    y[i] = x[i] + 1.0f;
}
