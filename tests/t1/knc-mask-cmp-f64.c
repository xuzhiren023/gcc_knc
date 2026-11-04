// S4-02 / ADR-0007 points 1 and 5: each C comparison of doubles vectorizes to
// vcmppd into a k register with KNC's 3-bit predicate (eq 0, lt 1, le 2,
// unord 3, neq 4, ord 7).  > and >= are lt and le with the operands swapped,
// so they signal on a NaN as C does.  !(a < b) keeps the signaling lt and
// inverts the select.  isless is the quiet UNGE inverted, which stays scalar
// until the card shows masked-off NaN lanes raise nothing (point 5).
// The result is long: an int result would need a V8DI to V16SI pack, which
// k1om lacks (no vpmovqd).  So the mask is 8 lanes (QI), the select V8DI.
// options: -O2 -ftree-vectorize
// scan-asm-func cmp_eq: \bvcmppd\s+\$0,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_ne: \bvcmppd\s+\$4,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_lt: \bvcmppd\s+\$1,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_le: \bvcmppd\s+\$2,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_gt: \bvcmppd\s+\$1,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_ge: \bvcmppd\s+\$2,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_un: \bvcmppd\s+\$3,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_ord: \bvcmppd\s+\$7,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_nlt: \bvcmppd\s+\$1,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_qlt: \A(?![\s\S]*%zmm)
// scan-asm-not: %(?:xmm|ymm)\d

#define CMP(NAME, EXPR)                                                  \
  void cmp_##NAME (long *restrict m, const double *restrict a,           \
                   const double *restrict b, int n)                      \
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
