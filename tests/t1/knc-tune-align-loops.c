// S12-31: an inner loop entered by fallthrough runs its alignment padding
// once per outer trip, and the assembler fills 9 to 15 bytes with one nop
// carrying 0x66 and 0x2e prefixes, two decode cycles each (R02 p.56,
// verified in the source; production or pre-production hardware not stated
// there).  Lead card runs 2026-11-15 (exclusive, one core): each such prefix
// after the second costs about 1.5 ns per trip; with the skip bounded at 7
// bytes HPCG's sparse kernels gained 0.3% and 0.5%.
// options: -O2 -march=knc
// scan-asm-func rows: ^\s*\.p2align 4,,7\s*\n\s*\.p2align 3\s*\n\.L\d+:
// scan-asm-not: ^\s*\.p2align 4\s*\n(?:\s*\.p2align 3\s*\n)?\.L\d+:

void
rows (double *restrict y, const double *restrict values,
      const int *restrict columns, const double *restrict x,
      const char *restrict counts, int n)
{
  for (int i = 0; i < n; i++)
    {
      double sum = 0.0;
      int count = counts[i];
      for (int j = 0; j < count; j++)
        sum += values[j] * x[columns[j]];
      values += count;
      columns += count;
      y[i] = sum;
    }
}
