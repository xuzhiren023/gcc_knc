// S12-24: a sign-alternating induction (k = -k) in a loop that also gets a
// vector epilogue.  The main loop starts the induction from a constant, so
// its { k, -k, ... } start vector folds.  The epilogue starts from the
// main loop's result, and its start vector needs a vector negate and an
// interleave in the induction's own vector type.  This port has no integer
// vector negate (V16SI here) and no 8-bit element arithmetic at all (V16QI
// for the unsigned char induction), so the epilogue cannot use that form.
// Reduced from WRF v4.8.0 share/dfi.F (REMEZ, DO 130).  Both loops must
// compile, and the main loops stay vector.
// options: -O3
// scan-asm-func alt_i32_f64: \bvmulpd\s[^\n]*%zmm\d+
// scan-asm-func alt_u8_f32: \bvmulps\s[^\n]*%zmm\d+
void
alt_i32_f64 (double *restrict a, double *restrict y, int n)
{
  int k = 1;
  for (int j = 0; j < n; j++)
    {
      y[j] = k * a[j];
      k = -k;
    }
}

void
alt_u8_f32 (float *restrict a, float *restrict y, int n)
{
  unsigned char k = 1;
  for (int j = 0; j < n; j++)
    {
      y[j] = k * a[j];
      k = -k;
    }
}
