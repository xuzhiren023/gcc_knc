// S12-31: a compare and its conditional jump issue as one pair on KNC, and
// pairing otherwise needs independent single-cycle instructions (R02 p.56,
// verified in the source; production or pre-production hardware not stated
// there).  An x87 instruction scheduled between the two leaves the jump an
// issue slot of its own.  Lead card run 2026-11-15 (window 5, exclusive,
// one core): the same seven instructions with the accumulate after the
// compare took 394.9 ns per 27-product row, 350.1 and 349.3 ns with the
// compare next to the jump; HPCG's sparse kernels gained 8% and 6-7%.
// options: -O2 -march=knc
// scan-asm-func row_products: \s+fmull?\s[^\n]*\n(?:\s+[a-z][^\n]*\n){1,3}?\s+cmp[a-z]?\s[^\n]*\n\s+j[a-z]+\s+\.L
// scan-asm-loop-not row_products: \bcmp[a-z]?\s[^\n]*\n\s+f[a-z0-9]+\s[^\n]*\n\s+j
// scan-asm-func row_sweep: \s+fmull?\s[^\n]*\n(?:\s+[a-z][^\n]*\n){1,3}?\s+cmp[a-z]?\s[^\n]*\n\s+j[a-z]+\s+\.L
// scan-asm-loop-not row_sweep: \bcmp[a-z]?\s[^\n]*\n\s+f[a-z0-9]+\s[^\n]*\n\s+j

double
row_products (const double *restrict values, const int *restrict columns,
              const double *restrict x, int n)
{
  double sum = 0.0;
  for (int j = 0; j < n; j++)
    sum += values[j] * x[columns[j]];
  return sum;
}

double
row_sweep (const double *restrict values, const int *restrict columns,
           const double *restrict x, double sum, int n)
{
  for (int j = 0; j < n; j++)
    sum -= values[j] * x[columns[j]];
  return sum;
}
