// S5-14 / ADR-0008 point 6: two 8-lane accesses per 16 int indices.
// Exactly one high-half permute; both halves must feed indexed accesses.
// options: -O3
// scan-asm-func scatter_i64: \A(?:(?:(?!\bvpscatterdq\b)[\s\S])*\bvpscatterdq\b){2}(?![\s\S]*\bvpscatterdq\b)
// scan-asm-func scatter_i64: \A(?:(?!\bvpermf32x4\b)[\s\S])*\bvpermf32x4\s+\$(?:238|0xee),[^\n]*\n(?![\s\S]*\bvpermf32x4\b)
// scan-asm-func scatter_i64: \A(?=[\s\S]*\bvpermf32x4\s+\$(?:238|0xee),\s*%zmm(?P<lo>\d+),\s*%zmm(?P<hi>\d+))(?=[\s\S]*\bvpscatterdq\s+[^\n]*,\s*%zmm(?P=lo),\s*8\))(?=[\s\S]*\bvpscatterdq\s+[^\n]*,\s*%zmm(?P=hi),\s*8\))
long a[1024] __attribute__((aligned(64)));
int idx[1024] __attribute__((aligned(64)));

void scatter_i64 (long *restrict b)
{
  for (int i = 0; i < 1024; ++i)
    b[idx[i]] = a[i];
}
