// S8-19: shared loop for knc-tune-tight-loops*.c.  The scalar remainder
// loops are 33 to 64 bytes and entered by fallthrough, so GCC 16's
// pass_align_tight_loops would put .p2align 5 or 6 with no max-skip in
// front of them, and the assembler fills the gap with nops that run on
// every outer trip.

void
mix_rows (int *restrict a, const int *restrict b, int n, int m)
{
  for (int i = 0; i < n; i++)
    {
      int s = a[i];
      for (int j = 0; j < m; j++)
        s = (s ^ b[j]) * 3 + (b[j] >> 2) - j;
      a[i] = s;
    }
}
