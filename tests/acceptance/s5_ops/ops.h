/* Sprint 5 acceptance: kernels in loops.c (compiler under test, vectorizing),
   references and checks in driver.c (-O0, never vectorized).  */
#ifndef S5_OPS_H
#define S5_OPS_H

/* Conversions (E4-05).  */
void cvt_i32_f32 (float *c, const int *a, int n);
void cvt_u32_f32 (float *c, const unsigned *a, int n);
void cvt_f32_i32 (int *c, const float *a, int n);
void cvt_f32_f64 (double *c, const float *a, int n);
void cvt_f64_f32 (float *c, const double *a, int n);
void cvt_i32_f64 (double *c, const int *a, int n);
void cvt_f64_i32 (int *c, const double *a, int n);
void cvt_i64_f64 (double *c, const long *a, int n);
void mix_f32_f64 (double *c, const float *a, const double *b, int n);

/* Permutes (E4-06): reversal, interleaved complex data, even/odd split.  */
void rev_f32 (float *c, const float *a, int n);
void rev_f64 (double *c, const double *a, int n);
void rev_i32 (int *c, const int *a, int n);
void cmul_f32 (float *c, const float *a, const float *b, int n);  /* n complex */
void deint_f32 (float *re, float *im, const float *z, int n);
void inter_f32 (float *z, const float *re, const float *im, int n);

/* Reductions (E4-06).  */
int sum_i32 (const int *a, int n);
long sum_i64 (const long *a, int n);
int min_i32 (const int *a, int n);
int max_i32 (const int *a, int n);
unsigned max_u32 (const unsigned *a, int n);
int and_i32 (const int *a, int n);
int or_i32 (const int *a, int n);
int xor_i32 (const int *a, int n);
float sum_f32 (const float *a, int n);
double sum_f64 (const double *a, int n);
float dot_f32 (const float *a, const float *b, int n);
float maxf_f32 (const float *a, int n);   /* m = a[i] > m ? a[i] : m */

/* Gather and scatter (E4-02).  Masked forms never evaluate b[idx[i]] or
   c[idx[i]] where m[i] is 0; the driver points those indices into a
   PROT_NONE page.  */
void gat_f32 (float *c, const float *b, const int *idx, int n);
void gat_f64 (double *c, const double *b, const int *idx, int n);
void gat_i32 (int *c, const int *b, const int *idx, int n);
void gat_i64 (long *c, const long *b, const int *idx, int n);
void mgat_f32 (float *c, const int *m, const float *b, const int *idx, int n);
void mgat_f64 (double *c, const int *m, const double *b, const int *idx, int n);
void sca_f32 (float *c, const float *b, const int *idx, int n);
void sca_f64 (double *c, const double *b, const int *idx, int n);
void msca_f32 (float *c, const int *m, const float *b, const int *idx, int n);

/* Division and square root (E4-03): correctly rounded or not vectorized.  */
void div_f32 (float *c, const float *a, const float *b, int n);
void sqrt_f32 (float *c, const float *a, int n);
void div_f64 (double *c, const double *a, const double *b, int n);
void sqrt_f64 (double *c, const double *a, int n);

/* Constant shuffles (S5-06's recipes): each is r = shuffle (a, b, sel) with
   the selector listed here, so the driver checks every lane.  */
typedef float s5_v16sf __attribute__ ((vector_size (64)));
typedef int s5_v16si __attribute__ ((vector_size (64)));
typedef double s5_v8df __attribute__ ((vector_size (64)));
typedef long s5_v8di __attribute__ ((vector_size (64)));
#define S5_SHUFFLES(X)                                                          X (id_f32, s5_v16sf, s5_v16si, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)   X (swz_cdab_f32, s5_v16sf, s5_v16si, 1, 0, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10, 13, 12, 15, 14)   X (swz_dacb_i32, s5_v16si, s5_v16si, 1, 2, 0, 3, 5, 6, 4, 7, 9, 10, 8, 11, 13, 14, 12, 15)   X (swz_bbbb_f64, s5_v8df, s5_v8di, 1, 1, 1, 1, 5, 5, 5, 5)                  X (swz_badc_i64, s5_v8di, s5_v8di, 2, 3, 0, 1, 6, 7, 4, 5)                  X (pf_f32, s5_v16sf, s5_v16si, 8, 9, 10, 11, 0, 1, 2, 3, 12, 13, 14, 15, 4, 5, 6, 7)   X (pf_f64, s5_v8df, s5_v8di, 6, 7, 4, 5, 2, 3, 0, 1)                        X (pshufd_i32, s5_v16si, s5_v16si, 3, 2, 1, 0, 7, 6, 5, 4, 11, 10, 9, 8, 15, 14, 13, 12)   X (pshufd_f64, s5_v8df, s5_v8di, 0, 0, 2, 2, 4, 4, 6, 6)                    X (align_i32, s5_v16si, s5_v16si, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18)   X (align_f64, s5_v8df, s5_v8di, 1, 2, 3, 4, 5, 6, 7, 0)                     X (blend_f32, s5_v16sf, s5_v16si, 0, 17, 2, 19, 4, 21, 6, 23, 8, 25, 10, 27, 12, 29, 14, 31)   X (perm1_f32, s5_v16sf, s5_v16si, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0)   X (perm1_i64, s5_v8di, s5_v8di, 3, 0, 7, 2, 5, 1, 6, 4)                     X (perm2_f32, s5_v16sf, s5_v16si, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30)   X (perm2_i64, s5_v8di, s5_v8di, 0, 2, 4, 6, 8, 10, 12, 14)
#define S5_SHUF_DECL(NAME, T, IT, ...) void shuf_##NAME (T *r, const T *a, const T *b);
S5_SHUFFLES (S5_SHUF_DECL)

/* 1 if loops.c was built with -ffast-math.  */
extern const int s5_ops_fast_math;

#endif
