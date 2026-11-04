/* Sprint 4 acceptance kernels.  Build with the compiler under test at
   -O2 -ftree-vectorize or -O3 (no -ffast-math), separately from driver.c.
   -DNEGATIVE_CONTROL breaks cmp_lt_f32 (uses <=): the driver must FAIL.
   -DGUARD_CONTROL makes add_f32 read one element past the end: the card
   run must die on the guard page.  */
#include <math.h>
#include "masks.h"

#define LOOP for (int i = 0; i < n; i++)
#define CMP(T, S, NAME, EXPR)                                                 \
  void cmp_##NAME##_##S (int *restrict m, const T *restrict a,                \
                         const T *restrict b, int n)                          \
  { LOOP m[i] = (EXPR); }
#define CMPS(T, S)                                                            \
  CMP (T, S, eq, a[i] == b[i]) CMP (T, S, ne, a[i] != b[i])                   \
  CMP (T, S, le, a[i] <= b[i]) CMP (T, S, gt, a[i] > b[i])                    \
  CMP (T, S, ge, a[i] >= b[i])

#ifdef NEGATIVE_CONTROL
CMP (float, f32, lt, a[i] <= b[i])
#else
CMP (float, f32, lt, a[i] < b[i])
#endif
CMP (double, f64, lt, a[i] < b[i])
CMP (int, i32, lt, a[i] < b[i])
CMP (unsigned, u32, lt, a[i] < b[i])
CMP (long, i64, lt, a[i] < b[i])
CMPS (float, f32) CMPS (double, f64) CMPS (int, i32) CMPS (unsigned, u32)
CMPS (long, i64)

#define FP(T, S, SUF)                                                         \
  CMP (T, S, un, __builtin_isunordered (a[i], b[i]))                          \
  CMP (T, S, nlt, !(a[i] < b[i]))                                             \
  void abs_##S (T *restrict c, const T *restrict a, int n)                    \
  { LOOP c[i] = fabs##SUF (a[i]); }                                           \
  void minx_##S (T *restrict c, const T *restrict a, const T *restrict b,     \
                 int n)                                                       \
  { LOOP c[i] = a[i] < b[i] ? a[i] : b[i]; }                                  \
  void maxx_##S (T *restrict c, const T *restrict a, const T *restrict b,     \
                 int n)                                                       \
  { LOOP c[i] = a[i] > b[i] ? a[i] : b[i]; }                                  \
  void fmin_##S (T *restrict c, const T *restrict a, const T *restrict b,     \
                 int n)                                                       \
  { LOOP c[i] = fmin##SUF (a[i], b[i]); }                                     \
  void fmax_##S (T *restrict c, const T *restrict a, const T *restrict b,     \
                 int n)                                                       \
  { LOOP c[i] = fmax##SUF (a[i], b[i]); }
FP (float, f32, f)
FP (double, f64, )

#define SEL(T, S)                                                             \
  void sel_##S (T *restrict c, const T *restrict a, const T *restrict b,      \
                const T *restrict x, const T *restrict y, int n)              \
  { LOOP c[i] = a[i] > b[i] ? x[i] : y[i]; }                                  \
  void cst_##S (T *restrict c, const T *restrict a, const T *restrict x,      \
                int n)                                                        \
  { LOOP if (a[i] > 0) c[i] = x[i]; }                                         \
  void cadd_##S (T *restrict c, const int *restrict m, const T *restrict x,   \
                 int n)                                                       \
  { LOOP if (m[i]) c[i] += x[i]; }                                            \
  void sub_##S (T *restrict c, const T *restrict a, const T *restrict b,      \
                int n)                                                        \
  { LOOP c[i] = a[i] - b[i]; }
SEL (float, f32) SEL (double, f64) SEL (int, i32) SEL (long, i64)

#ifdef GUARD_CONTROL
void add_f32 (float *restrict c, const float *restrict a,
              const float *restrict b, int n)
{ LOOP c[i] = a[i] + b[i + 1]; }
#else
void add_f32 (float *restrict c, const float *restrict a,
              const float *restrict b, int n)
{ LOOP c[i] = a[i] + b[i]; }
#endif
#define ADD(T, S)                                                             \
  void add_##S (T *restrict c, const T *restrict a, const T *restrict b,      \
                int n)                                                        \
  { LOOP c[i] = a[i] + b[i]; }
ADD (double, f64) ADD (int, i32) ADD (long, i64)

#define BIN(T, S, NAME, OP)                                                   \
  void NAME##_##S (T *restrict c, const T *restrict a, const T *restrict b,   \
                   int n)                                                     \
  { LOOP c[i] = a[i] OP b[i]; }
BIN (int, i32, mul, *) BIN (int, i32, and, &) BIN (int, i32, or, |)
BIN (int, i32, xor, ^) BIN (long, i64, and, &) BIN (long, i64, or, |)
BIN (long, i64, xor, ^)
