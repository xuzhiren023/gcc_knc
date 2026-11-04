// S4-02 / ADR-0007 point 1: ten masks are live at once, more than k0-k7
// hold: each selects into s, and again into q once s is complete.  Their
// inputs die at the compare, so LRA cannot rematerialize them: the extra
// masks spill through a GPR (kmov has no memory form) and come back.
// -fno-trapping-math lets if-conversion keep the FP adds unconditional.
// The V8DF masks are QI: nothing reads bits 15:8 of one as data, so no
// 16-bit consumer (kortest, knot, kxnor, kconcat, kextract) appears there.
// options: -O2 -ftree-vectorize -fno-trapping-math
// scan-asm-func live_f32: \bvcmpps\s[^\n]*%k[0-7]\s*$
// scan-asm-func live_f32: \bkmov\s+%k[0-7],\s*%(?:e[a-z]+|r\d+d)\s*$
// scan-asm-func live_f32: \bkmov\s+%(?:e[a-z]+|r\d+d),\s*%k[0-7]\s*$
// scan-asm-func live_f64: \bvcmppd\s[^\n]*%k[0-7]\s*$
// scan-asm-func live_f64: \bkmov\s+%k[0-7],\s*%(?:e[a-z]+|r\d+d)\s*$
// scan-asm-func live_f64: \bkmov\s+%(?:e[a-z]+|r\d+d),\s*%k[0-7]\s*$
// scan-asm-func live_f64: \A(?![\s\S]*\b(?:kortest|knot|kxnor|kconcat[hl]|kextract)\b)
// scan-asm-not: %(?:xmm|ymm)\d

#define C(K) _Bool c##K = a[i + K * n] < w;
#define S(K) (c##K ? w : (T) K)
#define Q(K) (c##K ? s : (T) (10 + K))
#define LIVE(T, NAME)                                                    \
  void NAME (T *restrict p, T *restrict q, const T *restrict a,          \
             const T *restrict x, int n)                                 \
  {                                                                      \
    for (int i = 0; i < n; i++)                                          \
      {                                                                  \
        T w = x[i];                                                      \
        C (0) C (1) C (2) C (3) C (4) C (5) C (6) C (7) C (8) C (9)      \
        T s = S (0) + S (1) + S (2) + S (3) + S (4) + S (5) + S (6)      \
              + S (7) + S (8) + S (9);                                   \
        p[i] = s;                                                        \
        q[i] = Q (9) + Q (8) + Q (7) + Q (6) + Q (5) + Q (4) + Q (3)     \
               + Q (2) + Q (1) + Q (0);                                  \
      }                                                                  \
  }

#define T float
LIVE (float, live_f32)
#undef T
#define T double
LIVE (double, live_f64)
