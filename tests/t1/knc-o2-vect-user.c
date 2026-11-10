// S8-09 (E5-18): an explicit -fvect-cost-model= or -fno-version-loops-for-strides
// still wins over the -march=knc -O2 defaults.
// options: -O2 -fvect-cost-model=very-cheap -fno-version-loops-for-strides
// scan-asm-not: \bv(?:fmadd\w*|mul|add)p[sd]\s
void axpy_f32 (float *y, const float *x, float a, int n)
{ for (int i = 0; i < n; ++i) y[i] += a * x[i]; }
void scale_f64 (double *restrict y, const double *restrict x, double a, long s, int n)
{ for (int i = 0; i < n; ++i) y[i * s] = a * x[i * s]; }
