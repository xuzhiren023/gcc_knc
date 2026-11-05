/* S5-10: tools/s5_10_checks.py compiles this case under actual command-line
   options, since function attributes do not reset builtin errno properties. */
#ifdef S5_SQRT_TEST
float sqrt_a[1024] __attribute__((aligned(64)));
float sqrt_c[1024] __attribute__((aligned(64)));
void sqrt_loop (void)
{
  for (int i = 0; i < 1024; ++i)
    sqrt_c[i] = __builtin_sqrtf (sqrt_a[i]);
}
#else
// S3-07 / ADR-0005 point 5: default -O2 must discover 64-byte FP modes.
// Fixed whole-vector trip counts also exercise the default very-cheap model.
// No vector types, explicit vectorization flags, or fast-math are used.
// options: -O2 -ffp-contract=off
// scan-asm-func affine_default_f32: \bvmulps\b[^\n]*%zmm\d+
// scan-asm-func affine_default_f32: \bvaddps\b[^\n]*%zmm\d+
// scan-asm-func affine_default_f64: \bvmulpd\b[^\n]*%zmm\d+
// scan-asm-func affine_default_f64: \bvaddpd\b[^\n]*%zmm\d+
// scan-asm-not: %(?:xmm|ymm)\d|\bv(?:f[mn]|fnm)\w*(?:ps|pd)\b

void
affine_default_f32(float *restrict y, const float *restrict x, float a, float b)
{
  for (unsigned int i = 0; i < 64; ++i)
    y[i] = a * x[i] + b;
}

void
affine_default_f64(double *restrict y, const double *restrict x, double a, double b)
{
  for (unsigned int i = 0; i < 64; ++i)
    y[i] = a * x[i] + b;
}

#endif
