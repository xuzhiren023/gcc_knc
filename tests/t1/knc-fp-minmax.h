/* S5-15: elementwise operations and horizontal reductions, both FP widths. */
#define CASE(T, S, MIN, MAX) \
void maxx_##S(T *restrict d, const T *restrict a, const T *restrict b) \
{ for (int i=0; i<256; ++i) d[i] = a[i] > b[i] ? a[i] : b[i]; } \
void minx_##S(T *restrict d, const T *restrict a, const T *restrict b) \
{ for (int i=0; i<256; ++i) d[i] = a[i] < b[i] ? a[i] : b[i]; } \
void maxf_##S(T *restrict d, const T *restrict a, const T *restrict b) \
{ for (int i=0; i<256; ++i) d[i] = MAX(a[i], b[i]); } \
void minf_##S(T *restrict d, const T *restrict a, const T *restrict b) \
{ for (int i=0; i<256; ++i) d[i] = MIN(a[i], b[i]); } \
T rmaxx_##S(const T *a, T s) \
{ for (int i=0; i<256; ++i) s = a[i] > s ? a[i] : s; return s; } \
T rminx_##S(const T *a, T s) \
{ for (int i=0; i<256; ++i) s = a[i] < s ? a[i] : s; return s; } \
T rmaxf_##S(const T *a, T s) \
{ for (int i=0; i<256; ++i) s = MAX(a[i], s); return s; } \
T rminf_##S(const T *a, T s) \
{ for (int i=0; i<256; ++i) s = MIN(a[i], s); return s; }
CASE(float, f32, __builtin_fminf, __builtin_fmaxf)
CASE(double, f64, __builtin_fmin, __builtin_fmax)
