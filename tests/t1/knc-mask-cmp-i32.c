// S4-02 / ADR-0007: int compares vectorize to vpcmpd and unsigned ones to
// vpcmpud, into a k register (eq 0, lt 1, le 2, neq 4, nlt 5, nle 6).
// k1om has no vpcmpq, so a compare of longs stays scalar (V8DI off).
// options: -O2 -ftree-vectorize
// scan-asm-func cmp_eq_i32: \bvpcmpd\s+\$0,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_ne_i32: \bvpcmpd\s+\$4,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_lt_i32: \bvpcmpd\s+\$1,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_le_i32: \bvpcmpd\s+\$2,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_gt_i32: \bvpcmpd\s+\$6,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_ge_i32: \bvpcmpd\s+\$5,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_lt_u32: \bvpcmpud\s+\$1,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_le_u32: \bvpcmpud\s+\$2,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_gt_u32: \bvpcmpud\s+\$6,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_ge_u32: \bvpcmpud\s+\$5,[^\n]*%k[0-7]\s*$
// scan-asm-func cmp_lt_i64: \A(?![\s\S]*%zmm)
// scan-asm-not: %(?:xmm|ymm)\d

#define CMP(T, S, NAME, OP)                                              \
  void cmp_##NAME##_##S (T *restrict m, const T *restrict a,             \
                         const T *restrict b, int n)                     \
  {                                                                      \
    for (int i = 0; i < n; i++)                                          \
      m[i] = a[i] OP b[i];                                               \
  }

CMP (int, i32, eq, ==) CMP (int, i32, ne, !=)
CMP (int, i32, lt, <) CMP (int, i32, le, <=)
CMP (int, i32, gt, >) CMP (int, i32, ge, >=)
CMP (unsigned, u32, lt, <) CMP (unsigned, u32, le, <=)
CMP (unsigned, u32, gt, >) CMP (unsigned, u32, ge, >=)
CMP (long, i64, lt, <)
