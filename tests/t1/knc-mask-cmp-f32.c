// S4-02 / ADR-0007 points 1 and 5: each C comparison of floats vectorizes to
// vcmpps into a k register with KNC's 3-bit predicate (eq 0, lt 1, le 2,
// unord 3, neq 4, ord 7).  > and >= are lt and le with the operands swapped,
// so they signal on a NaN as C does.  !(a < b) keeps the signaling lt and
// inverts the select.  isless is the quiet UNGE inverted, which stays scalar
// until the card shows masked-off NaN lanes raise nothing (point 5).
// options: -O2 -ftree-vectorize
// scan-asm-func cmp_eq: \bvcmpps\s+\$0,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_ne: \bvcmpps\s+\$4,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_lt: \bvcmpps\s+\$1,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_le: \bvcmpps\s+\$2,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_gt: \bvcmpps\s+\$1,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_ge: \bvcmpps\s+\$2,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_un: \bvcmpps\s+\$3,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_ord: \bvcmpps\s+\$7,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_nlt: \bvcmpps\s+\$1,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_qlt: \A(?![\s\S]*%zmm)
// scan-asm-not: %(?:xmm|ymm)\d

#define CMP(NAME, EXPR)                                                  \
  void cmp_##NAME (int *restrict m, const float *restrict a,             \
                   const float *restrict b, int n)                       \
  {                                                                      \
    for (int i = 0; i < n; i++)                                          \
      m[i] = (EXPR);                                                     \
  }

CMP (eq, a[i] == b[i])
CMP (ne, a[i] != b[i])
CMP (lt, a[i] < b[i])
CMP (le, a[i] <= b[i])
CMP (gt, a[i] > b[i])
CMP (ge, a[i] >= b[i])
CMP (un, __builtin_isunordered (a[i], b[i]))
CMP (ord, !__builtin_isunordered (a[i], b[i]))
CMP (nlt, !(a[i] < b[i]))
CMP (qlt, __builtin_isless (a[i], b[i]))
