/* Sprint 4 acceptance: kernels in loops.c (compiler under test, vectorizing),
   references and checks in driver.c (-O0, never vectorized).  */
#ifndef S4_MASKS_H
#define S4_MASKS_H

/* Compares: m[i] = a[i] OP b[i].  FP types add "un" (unordered) and "nlt"
   (!(a < b), true for NaN).  */
#define S4_CMP_DECL(T, S)                                                     \
  void cmp_eq_##S (int *m, const T *a, const T *b, int n);                    \
  void cmp_ne_##S (int *m, const T *a, const T *b, int n);                    \
  void cmp_lt_##S (int *m, const T *a, const T *b, int n);                    \
  void cmp_le_##S (int *m, const T *a, const T *b, int n);                    \
  void cmp_gt_##S (int *m, const T *a, const T *b, int n);                    \
  void cmp_ge_##S (int *m, const T *a, const T *b, int n);
#define S4_FP_DECL(T, S)                                                      \
  S4_CMP_DECL (T, S)                                                          \
  void cmp_un_##S (int *m, const T *a, const T *b, int n);                    \
  void cmp_nlt_##S (int *m, const T *a, const T *b, int n);                   \
  void abs_##S (T *c, const T *a, int n);                                     \
  void minx_##S (T *c, const T *a, const T *b, int n);                        \
  void maxx_##S (T *c, const T *a, const T *b, int n);                        \
  void fmin_##S (T *c, const T *a, const T *b, int n);                        \
  void fmax_##S (T *c, const T *a, const T *b, int n);
/* Selects, conditional store, conditional add and plain add (tails).  */
#define S4_SEL_DECL(T, S)                                                     \
  void sel_##S (T *c, const T *a, const T *b, const T *x, const T *y, int n); \
  void cst_##S (T *c, const T *a, const T *x, int n);                         \
  void cadd_##S (T *c, const int *m, const T *x, int n);                      \
  void add_##S (T *c, const T *a, const T *b, int n);                         \
  void sub_##S (T *c, const T *a, const T *b, int n);

S4_FP_DECL (float, f32)
S4_FP_DECL (double, f64)
S4_CMP_DECL (int, i32)
S4_CMP_DECL (unsigned, u32)
S4_CMP_DECL (long, i64)
S4_SEL_DECL (float, f32)
S4_SEL_DECL (double, f64)
S4_SEL_DECL (int, i32)
S4_SEL_DECL (long, i64)

void mul_i32 (int *c, const int *a, const int *b, int n);
void and_i32 (int *c, const int *a, const int *b, int n);
void or_i32 (int *c, const int *a, const int *b, int n);
void xor_i32 (int *c, const int *a, const int *b, int n);
void and_i64 (long *c, const long *a, const long *b, int n);
void or_i64 (long *c, const long *a, const long *b, int n);
void xor_i64 (long *c, const long *a, const long *b, int n);

#endif
