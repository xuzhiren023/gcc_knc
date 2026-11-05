/* Sprint 5 kernels: compiled by the compiler under test with vectorization
   on (see README.md for the builds).  Plain C, no target code.  */
#include "ops.h"

#define R __restrict
/* The driver skips checks that FTZ/DAZ (crtfastmath) or reciprocal
   approximation legitimately change.  */
#ifdef __FAST_MATH__
const int s5_ops_fast_math = 1;
#else
const int s5_ops_fast_math = 0;
#endif
/* -DNEGATIVE_CONTROL moves every division and square-root result one ulp
   up, so the driver's correct-rounding checks must fail.  */
#ifdef NEGATIVE_CONTROL
#define UPF(x) __builtin_nextafterf ((x), __builtin_inff ())
#define UPD(x) __builtin_nextafter ((x), __builtin_inf ())
#else
#define UPF(x) (x)
#define UPD(x) (x)
#endif

void cvt_i32_f32 (float *R c, const int *R a, int n)
{ for (int i = 0; i < n; i++) c[i] = (float) a[i]; }
void cvt_u32_f32 (float *R c, const unsigned *R a, int n)
{ for (int i = 0; i < n; i++) c[i] = (float) a[i]; }
void cvt_f32_i32 (int *R c, const float *R a, int n)
{ for (int i = 0; i < n; i++) c[i] = (int) a[i]; }
void cvt_f32_f64 (double *R c, const float *R a, int n)
{ for (int i = 0; i < n; i++) c[i] = a[i]; }
void cvt_f64_f32 (float *R c, const double *R a, int n)
{ for (int i = 0; i < n; i++) c[i] = (float) a[i]; }
void cvt_i32_f64 (double *R c, const int *R a, int n)
{ for (int i = 0; i < n; i++) c[i] = a[i]; }
void cvt_f64_i32 (int *R c, const double *R a, int n)
{ for (int i = 0; i < n; i++) c[i] = (int) a[i]; }
void cvt_i64_f64 (double *R c, const long *R a, int n)
{ for (int i = 0; i < n; i++) c[i] = (double) a[i]; }
void mix_f32_f64 (double *R c, const float *R a, const double *R b, int n)
{ for (int i = 0; i < n; i++) c[i] = a[i] * b[i]; }

void rev_f32 (float *R c, const float *R a, int n)
{ for (int i = 0; i < n; i++) c[i] = a[n - 1 - i]; }
void rev_f64 (double *R c, const double *R a, int n)
{ for (int i = 0; i < n; i++) c[i] = a[n - 1 - i]; }
void rev_i32 (int *R c, const int *R a, int n)
{ for (int i = 0; i < n; i++) c[i] = a[n - 1 - i]; }
void cmul_f32 (float *R c, const float *R a, const float *R b, int n)
{
  for (int i = 0; i < n; i++)
    {
      c[2 * i] = a[2 * i] * b[2 * i] - a[2 * i + 1] * b[2 * i + 1];
      c[2 * i + 1] = a[2 * i] * b[2 * i + 1] + a[2 * i + 1] * b[2 * i];
    }
}
void deint_f32 (float *R re, float *R im, const float *R z, int n)
{ for (int i = 0; i < n; i++) { re[i] = z[2 * i]; im[i] = z[2 * i + 1]; } }
void inter_f32 (float *R z, const float *R re, const float *R im, int n)
{ for (int i = 0; i < n; i++) { z[2 * i] = re[i]; z[2 * i + 1] = im[i]; } }

int sum_i32 (const int *a, int n)
{ int s = 0; for (int i = 0; i < n; i++) s += a[i]; return s; }
long sum_i64 (const long *a, int n)
{ long s = 0; for (int i = 0; i < n; i++) s += a[i]; return s; }
int min_i32 (const int *a, int n)
{ int m = __INT_MAX__; for (int i = 0; i < n; i++) m = a[i] < m ? a[i] : m; return m; }
int max_i32 (const int *a, int n)
{ int m = -__INT_MAX__ - 1; for (int i = 0; i < n; i++) m = a[i] > m ? a[i] : m; return m; }
unsigned max_u32 (const unsigned *a, int n)
{ unsigned m = 0; for (int i = 0; i < n; i++) m = a[i] > m ? a[i] : m; return m; }
int and_i32 (const int *a, int n)
{ int s = -1; for (int i = 0; i < n; i++) s &= a[i]; return s; }
int or_i32 (const int *a, int n)
{ int s = 0; for (int i = 0; i < n; i++) s |= a[i]; return s; }
int xor_i32 (const int *a, int n)
{ int s = 0; for (int i = 0; i < n; i++) s ^= a[i]; return s; }
float sum_f32 (const float *a, int n)
{ float s = 0; for (int i = 0; i < n; i++) s += a[i]; return s; }
double sum_f64 (const double *a, int n)
{ double s = 0; for (int i = 0; i < n; i++) s += a[i]; return s; }
float dot_f32 (const float *a, const float *b, int n)
{ float s = 0; for (int i = 0; i < n; i++) s += a[i] * b[i]; return s; }
float maxf_f32 (const float *a, int n)
{ float m = -__builtin_inff (); for (int i = 0; i < n; i++) m = a[i] > m ? a[i] : m; return m; }

void gat_f32 (float *R c, const float *R b, const int *R idx, int n)
{ for (int i = 0; i < n; i++) c[i] = b[idx[i]]; }
void gat_f64 (double *R c, const double *R b, const int *R idx, int n)
{ for (int i = 0; i < n; i++) c[i] = b[idx[i]]; }
void gat_i32 (int *R c, const int *R b, const int *R idx, int n)
{ for (int i = 0; i < n; i++) c[i] = b[idx[i]]; }
void gat_i64 (long *R c, const long *R b, const int *R idx, int n)
{ for (int i = 0; i < n; i++) c[i] = b[idx[i]]; }
void mgat_f32 (float *R c, const int *R m, const float *R b, const int *R idx, int n)
{ for (int i = 0; i < n; i++) if (m[i]) c[i] = b[idx[i]]; }
void mgat_f64 (double *R c, const int *R m, const double *R b, const int *R idx, int n)
{ for (int i = 0; i < n; i++) if (m[i]) c[i] = b[idx[i]]; }
void sca_f32 (float *R c, const float *R b, const int *R idx, int n)
{ for (int i = 0; i < n; i++) c[idx[i]] = b[i]; }
void sca_f64 (double *R c, const double *R b, const int *R idx, int n)
{ for (int i = 0; i < n; i++) c[idx[i]] = b[i]; }
void msca_f32 (float *R c, const int *R m, const float *R b, const int *R idx, int n)
{ for (int i = 0; i < n; i++) if (m[i]) c[idx[i]] = b[i]; }

void div_f32 (float *R c, const float *R a, const float *R b, int n)
{ for (int i = 0; i < n; i++) c[i] = UPF (a[i] / b[i]); }
void sqrt_f32 (float *R c, const float *R a, int n)
{ for (int i = 0; i < n; i++) c[i] = UPF (__builtin_sqrtf (a[i])); }
void div_f64 (double *R c, const double *R a, const double *R b, int n)
{ for (int i = 0; i < n; i++) c[i] = UPD (a[i] / b[i]); }
void sqrt_f64 (double *R c, const double *R a, int n)
{ for (int i = 0; i < n; i++) c[i] = UPD (__builtin_sqrt (a[i])); }

#define S5_SHUF_DEF(NAME, T, IT, ...)                                           void shuf_##NAME (T *r, const T *a, const T *b)                               { *r = __builtin_shuffle (*a, *b, (IT) { __VA_ARGS__ }); }
S5_SHUFFLES (S5_SHUF_DEF)
