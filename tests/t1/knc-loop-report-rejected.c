// S6-04 / ADR-0007 point 7: unknown alignment rejects the masked choice.
// options: -O3 -fopt-info-vec-missed
// scan-output: KNC.*reject.*misaligned masked access
void report_rejected (float *restrict y, const float *restrict x,
                      const float *restrict a, int n)
{
  for (int i = 0; i < n; ++i)
    if (a[i] > 0)
      y[i] = x[i];
}
