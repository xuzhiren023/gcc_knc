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

#endif
