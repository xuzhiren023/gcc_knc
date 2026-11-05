// S5-08, ADR-0008 points 4 and 5; Intel 327364 pp.157-179.
// options: -O2 -ftree-vectorize -ftrapping-math
// scan-asm-func from_i32: \bvcvtfxpntdq2ps\s+\$(?:0x)?0,
// scan-asm-func from_u32: \bvcvtfxpntudq2ps\s+\$(?:0x)?0,
// scan-asm-func to_i32: \bvcvtfxpntps2dq\s+\$(?:0x)?3,
// scan-asm-func to_u32: \bvcvtfxpntps2udq\s+\$(?:0x)?3,
// scan-asm-not: \b(?:fnstcw|fistp\w*|vcvtdq2ps|vcvttps2dq|vcvttps2udq)\b|%[xy]mm\d+

float f[1024] __attribute__((aligned(64)));
int i32[1024] __attribute__((aligned(64)));
unsigned u32[1024] __attribute__((aligned(64)));
void from_i32 (void) { for (int i = 0; i < 1024; ++i) f[i] = i32[i]; }
void from_u32 (void) { for (int i = 0; i < 1024; ++i) f[i] = u32[i]; }
void to_i32 (void) { for (int i = 0; i < 1024; ++i) i32[i] = f[i]; }
void to_u32 (void) { for (int i = 0; i < 1024; ++i) u32[i] = f[i]; }
