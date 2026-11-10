// S8-09 (E5-18): -O2 -march=knc vectorizes loops that the generic -O2
// cost model (very-cheap) leaves scalar: pointers without restrict need a
// runtime alias check, a reduction needs an epilogue, and a runtime stride
// needs a stride-1 version (Fortran assumed-shape arrays lower the same way).
// options: -O2 -fopt-info-vec-optimized -fopt-info-loop-optimized
// scan-output: :13:\d+: optimized:  loop versioned for vectorization because of possible aliasing
// scan-output: :16:\d+: optimized:  loop versioned for vectorization because of possible aliasing
// scan-output: :19:\d+: optimized:  loop versioned for vectorization because of possible aliasing
// scan-output: :25:\d+: optimized: versioned this loop for when certain strides are 1
// scan-output: :25:\d+: optimized: loop vectorized using 64 byte vectors
// scan-asm-func axpy_f32: \bv(?:fmadd\w*|mul|add)ps\s[^\n]*%zmm\d+
void axpy_f32 (float *y, const float *x, float a, int n)
{ for (int i = 0; i < n; ++i) y[i] += a * x[i]; }
// scan-asm-func axpy_f64: \bv(?:fmadd\w*|mul|add)pd\s[^\n]*%zmm\d+
void axpy_f64 (double *y, const double *x, double a, int n)
{ for (int i = 0; i < n; ++i) y[i] += a * x[i]; }
// scan-asm-func add_i32: \bvpaddd\s[^\n]*%zmm\d+
void add_i32 (int *a, const int *b, const int *c, int n)
{ for (int i = 0; i < n; ++i) a[i] = b[i] + c[i]; }
// scan-asm-func sum_i32: \bvpaddd\s[^\n]*%zmm\d+
int sum_i32 (const int *x, int n)
{ int s = 0; for (int i = 0; i < n; ++i) s += x[i]; return s; }
// scan-asm-func scale_f64: \bvmulpd\s[^\n]*%zmm\d+
void scale_f64 (double *restrict y, const double *restrict x, double a, long s, int n)
{ for (int i = 0; i < n; ++i) y[i * s] = a * x[i * s]; }
