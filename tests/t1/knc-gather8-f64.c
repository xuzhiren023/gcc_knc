// S5-14 / ADR-0008 point 6: two 8-lane accesses per 16 int indices.
// Exactly one high-half permute; both halves must feed indexed accesses.
// -fno-unroll-loops: this test pins the 8-lane gather/scatter split, not unrolling (S8-15).
// options: -O3 -fvect-cost-model=unlimited -fno-unroll-loops
// scan-asm-func gather_f64: \A(?:(?:(?!\bvgatherdpd\b)[\s\S])*\bvgatherdpd\b){2}(?![\s\S]*\bvgatherdpd\b)
// scan-asm-func gather_f64: \A(?:(?!\bvpermf32x4\b)[\s\S])*\bvpermf32x4\s+\$(?:238|0xee),[^\n]*\n(?![\s\S]*\bvpermf32x4\b)
// scan-asm-func gather_f64: \A(?=[\s\S]*\bvpermf32x4\s+\$(?:238|0xee),\s*%zmm(?P<lo>\d+),\s*%zmm(?P<hi>\d+))(?=[\s\S]*\bvgatherdpd\s+[^\n]*,\s*%zmm(?P=lo),\s*8\))(?=[\s\S]*\bvgatherdpd\s+[^\n]*,\s*%zmm(?P=hi),\s*8\))
double a[1024] __attribute__((aligned(64)));
int idx[1024] __attribute__((aligned(64)));

void gather_f64 (const double *restrict b)
{
  for (int i = 0; i < 1024; ++i)
    a[i] = b[idx[i]];
}
