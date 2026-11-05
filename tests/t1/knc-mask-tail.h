/* S4-05 / ADR-0007 point 7: when every access of a loop is known 64-byte
   aligned and the vectorizer needs no alignment peel, the remainder is one
   masked IMCI epilogue instead of the x87 scalar loop.  while_ult builds
   the mask in a GPR and moves it to a k register; every masked move sits
   behind an empty-mask guard (jkzd for 16 lanes, a byte test for 8, whose
   kmov copy carries bits 15:8).  Trapping FP operations are cond_<op>:
   add, mul, and fma, so the epilogue rounds like an FMA body.
   Shapes from tests/acceptance/s4_masks/loops.c.  */
#define LOOP for (int i = 0; i < n; i++)
#define AL(p) __builtin_assume_aligned (p, 64)

#define ADD_AL(T, S)                                                      \
  void add_al_##S (T *restrict c, const T *restrict a,                    \
                   const T *restrict b, int n)                            \
  {                                                                       \
    T *cc = AL (c); const T *aa = AL (a), *bb = AL (b);                   \
    LOOP cc[i] = aa[i] + bb[i];                                           \
  }
ADD_AL (float, f32) ADD_AL (double, f64) ADD_AL (int, i32)

#define AFFINE_AL(T, S)                                                   \
  void affine_al_##S (T *restrict c, const T *restrict x, T a, T b,       \
                      int n)                                              \
  {                                                                       \
    T *cc = AL (c); const T *xx = AL (x);                                 \
    LOOP cc[i] = a * xx[i] + b;                                           \
  }
AFFINE_AL (float, f32) AFFINE_AL (double, f64)

/* No addend, so the masked multiply is not fused into an FMA.  */
void mul_al_f32 (float *restrict c, const float *restrict a,
                 const float *restrict b, int n)
{
  float *cc = AL (c); const float *aa = AL (a), *bb = AL (b);
  LOOP cc[i] = aa[i] * bb[i];
}

void cst_al_f32 (float *restrict c, const float *restrict a,
                 const float *restrict x, int n)
{
  float *cc = AL (c); const float *aa = AL (a), *xx = AL (x);
  LOOP if (aa[i] > 0) cc[i] = xx[i];
}

/* Unknown alignment: the remainder stays x87.  */
void add_f32 (float *restrict c, const float *restrict a,
              const float *restrict b, int n)
{ LOOP c[i] = a[i] + b[i]; }
