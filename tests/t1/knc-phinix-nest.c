// S8-22: -mphinix (-O3) ran M2 mat16 at x87 speed (12.9x slower than -O2)
// and short 1.27x slower.  mat16: cunrolli fully unrolled the 16-step inner
// loop before the vectorizer, so the outer-loop vector form of -O2 was gone
// and the remaining row loop, peeled for alignment, never paid in 16 rows.
// short: the dynamic cost model peeled up to 15 iterations for alignment, in
// x87, so a 17-element call ran most of its elements in x87.
// options: -mphinix -ffp-contract=fast
// The full-block rows multiply-add a broadcast of x from memory, as at -O2.
// scan-asm-func mat16: ^\s*vfmadd\d+ps\s+-?\d*\(%\w+\)\{1to16\}
// No element of y is stored from x87 (only p[] is staged on the stack).
// scan-asm-func short_affine: \A(?![\s\S]*^\s*fstps\s+-?\d*\(%r(?!sp\))\w+\))

void
mat16 (float *restrict y, const float *restrict x, const float *restrict a,
       unsigned long n)
{
  for (unsigned long base = 0; base < n; base += 16)
    {
      unsigned long count = n - base < 16 ? n - base : 16;
      for (unsigned long r = 0; r < count; ++r)
        {
          float sum = 0;
          for (unsigned j = 0; j < 16; ++j)
            sum = sum + a[j * 16 + r] * x[base + j];
          y[base + r] = sum;
        }
    }
}

void
short_affine (float *restrict y, const float *restrict x,
              const float *restrict p, unsigned long n)
{
  for (unsigned long i = 0; i < n; ++i)
    y[i] = p[0] * x[i] + p[1];
}
