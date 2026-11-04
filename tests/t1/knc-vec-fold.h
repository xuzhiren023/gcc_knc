/* S4-09: IMCI vaddp/vsubp/vmulp fault on a memory operand that is not
   64-byte aligned (Intel 327364-001; S3-03 card probe).  Only b is
   folded, so each misaligned body must keep its arithmetic register-only,
   and b's 64-byte control must still fold.  */
#define LOOP(NAME, T, OP)                                                  \
  void NAME (T *restrict c, const T *restrict a, const T *restrict b,      \
             int n)                                                        \
  {                                                                        \
    for (int i = 0; i < n; i++)                                            \
      c[i] = a[i] OP b[i];                                                 \
  }                                                                        \
  void NAME##_b64 (T *restrict c, const T *restrict a, const T *restrict b,\
                   int n)                                                  \
  {                                                                        \
    b = __builtin_assume_aligned (b, 64);                                  \
    for (int i = 0; i < n; i++)                                            \
      c[i] = a[i] OP b[i];                                                 \
  }

LOOP (add_f32, float, +)
LOOP (sub_f32, float, -)
LOOP (mul_f32, float, *)
LOOP (add_f64, double, +)
LOOP (sub_f64, double, -)
LOOP (mul_f64, double, *)
