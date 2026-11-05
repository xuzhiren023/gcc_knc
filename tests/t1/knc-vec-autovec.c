// S3-07 / ADR-0005 point 5: default -O2 must discover 64-byte FP modes.
// Fixed whole-vector trip counts also exercise the default very-cheap model.
// No vector types, explicit vectorization flags, or fast-math are used.
// options: -O2 -ffp-contract=off
// scan-asm-func affine_default_f32: \bvmulps\b[^\n]*%zmm\d+
// scan-asm-func affine_default_f32: \bvaddps\b[^\n]*%zmm\d+
// scan-asm-func affine_default_f64: \bvmulpd\b[^\n]*%zmm\d+
// scan-asm-func affine_default_f64: \bvaddpd\b[^\n]*%zmm\d+
// scan-asm-not: %(?:xmm|ymm)\d
// scan-asm-loop-not affine_default_f32: \bv(?:f[mn]|fnm)\w*(?:ps|pd)\b
// scan-asm-loop-not affine_default_f64: \bv(?:f[mn]|fnm)\w*(?:ps|pd)\b

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

// S5-10: strict square root needs only permission to omit errno.
// scan-asm-func sqrt_vector: \bvrsqrt23ps\b[^\n]*%zmm
// scan-asm-func sqrt_vector: \bvfmadd\w*ps\b
// scan-asm-loop-not sqrt_vector: \bfsqrt\b
// scan-asm-func sqrt_errno: \bfsqrt\b
// scan-asm-loop-not sqrt_errno: \bvrsqrt23ps\b
float sqrt_a[1024] __attribute__((aligned(64)));
float sqrt_c[1024] __attribute__((aligned(64)));
__attribute__((optimize("O2", "tree-vectorize", "no-math-errno")))
void sqrt_vector (void)
{
  for (int i = 0; i < 1024; ++i)
    sqrt_c[i] = __builtin_sqrtf (sqrt_a[i]);
}
void sqrt_errno (void)
{
  for (int i = 0; i < 1024; ++i)
    sqrt_c[i] = __builtin_sqrtf (sqrt_a[i]);
}
