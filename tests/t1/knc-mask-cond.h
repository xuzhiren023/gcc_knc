/* S4-03 / ADR-0007 points 3 and 7: conditional loops, ?:, fabs, min and
   max on the packed modes, at -O2 -ftree-vectorize and -O3 (no fast-math).
   Globals are 64-byte aligned by the vectorizer, so their conditional
   loads and stores may be aligned masked moves behind an empty-mask guard.
   Restrict pointers of unknown alignment stay scalar until S4-05.  */
#define LOOP for (int i = 0; i < n; i++)
#define PTR(T) T *restrict

/* x[i] and y[i] are conditional loads, so they need maskload: the 64-byte
   alignment makes them aligned masked moves.  */
#define A64(P) __builtin_assume_aligned (P, 64)
#define SEL(T, S)                                                         \
  void sel_##S (PTR (T) c, PTR (const T) a, PTR (const T) b,              \
                PTR (const T) x, PTR (const T) y, int n)                  \
  {                                                                       \
    T *cc = A64 (c);                                                      \
    const T *aa = A64 (a), *bb = A64 (b), *xx = A64 (x), *yy = A64 (y);   \
    LOOP cc[i] = aa[i] > bb[i] ? xx[i] : yy[i];                           \
  }
SEL (float, f32) SEL (double, f64) SEL (int, i32)

#define MINX(T, S)                                                        \
  void minx_##S (PTR (T) c, PTR (const T) a, PTR (const T) b, int n)      \
  { LOOP c[i] = a[i] < b[i] ? a[i] : b[i]; }
MINX (float, f32) MINX (double, f64)

#define MINMAX(T, S)                                                      \
  void min_##S (PTR (T) c, PTR (const T) a, PTR (const T) b, int n)       \
  { LOOP c[i] = a[i] < b[i] ? a[i] : b[i]; }                              \
  void max_##S (PTR (T) c, PTR (const T) a, PTR (const T) b, int n)       \
  { LOOP c[i] = a[i] > b[i] ? a[i] : b[i]; }
MINMAX (int, i32) MINMAX (unsigned, u32)

void abs_f32 (PTR (float) c, PTR (const float) a, int n)
{ LOOP c[i] = __builtin_fabsf (a[i]); }
void abs_f64 (PTR (double) c, PTR (const double) a, int n)
{ LOOP c[i] = __builtin_fabs (a[i]); }
void fmin_f32 (PTR (float) c, PTR (const float) a, PTR (const float) b, int n)
{ LOOP c[i] = __builtin_fminf (a[i], b[i]); }
void fmax_f64 (PTR (double) c, PTR (const double) a, PTR (const double) b,
               int n)
{ LOOP c[i] = __builtin_fmax (a[i], b[i]); }

#define G 1024
#define CST(T, S)                                                         \
  T a_##S[G], c_##S[G], x_##S[G];                                         \
  void cst_##S (int n) { LOOP if (a_##S[i] > 0) c_##S[i] = x_##S[i]; }
CST (float, f32) CST (double, f64) CST (int, i32)

void cst_ptr_f32 (PTR (float) c, PTR (const float) a, PTR (const float) x,
                  int n)
{ LOOP if (a[i] > 0) c[i] = x[i]; }

int m_i32[G];
void cadd_f32 (int n) { LOOP if (m_i32[i]) c_f32[i] += x_f32[i]; }
void cadd_i32 (int n) { LOOP if (m_i32[i]) c_i32[i] += x_i32[i]; }
