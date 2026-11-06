/* Same source, compiled separately with tree vectorization enabled/disabled.
   No reassociation, contraction, intrinsics or target-specific C extensions. */
#include "kernels.h"
#define CAT_(a,b) a##b
#define CAT(a,b) CAT_(a,b)
#define FN(k) CAT(m2_##k##_, BUILD)
#define ARGS void *restrict yy, const void *restrict xx, \
             const void *restrict pp, unsigned long n
#define AFFINE(k,T) \
void FN(k)(ARGS) { \
  T *restrict y = __builtin_assume_aligned(yy, 64); \
  const T *restrict x = __builtin_assume_aligned(xx, 64); \
  const T *restrict p = pp; \
  for (unsigned long i = 0; i < n; ++i) y[i] = p[0]*x[i]+p[1]; \
}
AFFINE(affine_f32,float)
AFFINE(affine_f64,double)
/* Short calls can begin within a larger aligned working set. */
void FN(short)(ARGS) {
  float *restrict y = yy;
  const float *restrict x = xx, *restrict p = pp;
  for (unsigned long i = 0; i < n; ++i) y[i] = p[0]*x[i]+p[1];
}
void FN(stencil1)(ARGS) {
  float *restrict y = __builtin_assume_aligned(yy,64);
  const float *restrict x = __builtin_assume_aligned(xx,64);
  (void)pp;
  for (unsigned long i = 0; i < n; ++i)
    y[i] = (x[(long)i-1] + x[i]) + x[i+1];
}
void FN(stencil2)(ARGS) {
  float *restrict y = __builtin_assume_aligned(yy,64);
  const float *restrict x = __builtin_assume_aligned(xx,64);
  (void)pp;
  for (unsigned long row = 0; row*WIDTH < n; ++row) {
    unsigned long count = n-row*WIDTH < WIDTH ? n-row*WIDTH : WIDTH;
    const float *restrict q = x+row*PITCH;
    for (unsigned long col = 0; col < count; ++col)
      y[row*WIDTH+col] = (((q[(long)col-PITCH]+q[(long)col-1])
                           +q[col])+q[col+1])+q[col+PITCH];
  }
}
#define MATRIX(D) \
void FN(mat##D)(ARGS) { \
  float *restrict y = yy; \
  const float *restrict x = xx, *restrict a = pp; \
  for (unsigned long base = 0; base < n; base += D) { \
    unsigned long count = n-base < D ? n-base : D; \
    for (unsigned long r = 0; r < count; ++r) { \
      float sum = 0; \
      for (unsigned j = 0; j < D; ++j) sum = sum+a[j*16+r]*x[(base/D)*16+j]; \
      y[base+r] = sum; \
    } \
  } \
}
MATRIX(8)
MATRIX(16)
