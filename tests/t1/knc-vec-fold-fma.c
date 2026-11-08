// S8-06 (E5-17): IMCI folds an aligned full-line memory operand into
// vaddp/vmulp/vfmadd, and a scalar into vfmadd as {1to16}/{1to8}
// (Intel 327364-001, Table 4.2), so no separate vmovaps load is needed.
// options: -O2 -ftree-vectorize -march=knc -ffp-contract=fast
// scan-asm-func add_f32: \bvaddps\s+-?\w*\(
// scan-asm-func mul_f64: \bvmulpd\s+-?\w*\(
// scan-asm-func fma_f32: \bvfn?m(?:add|sub)\d{3}ps\s+-?\w*\([^)]*\),
// scan-asm-func bcast_f32: \bvfmadd\d{3}ps\s+-?\w*\([^)]*\)\{1to16\}
// scan-asm-func bcast_f64: \bvfmadd\d{3}pd\s+-?\w*\([^)]*\)\{1to8\}
#define A(p) __builtin_assume_aligned (p, 64)

void
add_f32 (float *restrict c, const float *restrict a, const float *restrict b,
         int n)
{
  c = A (c); a = A (a); b = A (b);
  for (int i = 0; i < n; i++)
    c[i] = a[i] + b[i];
}

void
mul_f64 (double *restrict c, const double *restrict a,
         const double *restrict b, int n)
{
  c = A (c); a = A (a); b = A (b);
  for (int i = 0; i < n; i++)
    c[i] = a[i] * b[i];
}

/* y = p[0] * x + p[1]: the M2 affine shape.  x is the only streamed load.  */
void
fma_f32 (float *restrict y, const float *restrict x, const float *restrict p,
         int n)
{
  y = A (y); x = A (x);
  for (int i = 0; i < n; i++)
    y[i] = p[0] * x[i] + p[1];
}

/* A matrix column times one scalar per step: the M2 mat16 shape.  */
void
bcast_f32 (float *restrict y, const float *restrict a, const float *restrict x,
           int n)
{
  y = A (y); a = A (a);
  for (int j = 0; j < n; j++)
    for (int r = 0; r < 16; r++)
      y[r] += a[j * 16 + r] * x[j];
}

void
bcast_f64 (double *restrict y, const double *restrict a,
           const double *restrict x, int n)
{
  y = A (y); a = A (a);
  for (int j = 0; j < n; j++)
    for (int r = 0; r < 8; r++)
      y[r] += a[j * 8 + r] * x[j];
}
