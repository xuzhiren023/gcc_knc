// S4-02 / ADR-0007 point 1: ten masks are live at once (each is used by
// both sums), more than k0-k7 hold.  Their inputs die at the compare, so
// LRA cannot rematerialize them: the extra masks must move to GPRs and back.
// The V8DF masks are QI: nothing reads bits 15:8 of one as data, so no
// 16-bit consumer (kortest, knot, kxnor, kconcat, kextract) appears there.
// options: -O2 -ftree-vectorize
// scan-asm-func live_f32: \bvcmpps\s[^\n]*%k[0-7]\s*$
// scan-asm-func live_f32: \bkmov\s+%k[0-7],\s*%(?:e[a-z]+|r\d+d)\s*$
// scan-asm-func live_f32: \bkmov\s+%(?:e[a-z]+|r\d+d),\s*%k[0-7]\s*$
// scan-asm-func live_f64: \bvcmppd\s[^\n]*%k[0-7]\s*$
// scan-asm-func live_f64: \bkmov\s+%k[0-7],\s*%(?:e[a-z]+|r\d+d)\s*$
// scan-asm-func live_f64: \bkmov\s+%(?:e[a-z]+|r\d+d),\s*%k[0-7]\s*$
// scan-asm-func live_f64: \A(?![\s\S]*\b(?:kortest|knot|kxnor|kconcat[hl]|kextract)\b)
// scan-asm-not: %(?:xmm|ymm)\d

#define C(K) _Bool c##K = a[i + K * n] < w;
#define S(K, B) (c##K ? w : (T) (B + K))
#define LIVE(T, NAME)                                                    \
  void NAME (T *restrict p, T *restrict q, const T *restrict a,          \
             const T *restrict x, int n)                                 \
  {                                                                      \
    for (int i = 0; i < n; i++)                                          \
      {                                                                  \
        T w = x[i];                                                      \
        C (0) C (1) C (2) C (3) C (4) C (5) C (6) C (7) C (8) C (9)      \
        p[i] = S (0, 0) + S (1, 0) + S (2, 0) + S (3, 0) + S (4, 0)      \
               + S (5, 0) + S (6, 0) + S (7, 0) + S (8, 0) + S (9, 0);   \
        q[i] = S (9, 10) + S (8, 10) + S (7, 10) + S (6, 10) + S (5, 10) \
               + S (4, 10) + S (3, 10) + S (2, 10) + S (1, 10)           \
               + S (0, 10);                                              \
      }                                                                  \
  }

#define T float
LIVE (float, live_f32)
#undef T
#define T double
LIVE (double, live_f64)
