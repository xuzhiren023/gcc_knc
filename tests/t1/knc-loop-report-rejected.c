// S6-04 / ADR-0007 point 7: a shape the masked tail cannot take rejects the
// masked choice.  Since S8-02 (ADR-0009 amendment 1 point 9) unknown
// alignment is no longer such a shape (it takes a gather or scatter), so the
// rejected case is a backward access.
// options: -O3 -fopt-info-vec-missed
// scan-output: KNC.*reject.*backward masked access
void report_rejected (float *restrict y, const float *restrict x, int n)
{
  for (int i = 0; i < n; ++i)
    y[i] = x[n - 1 - i];
}
