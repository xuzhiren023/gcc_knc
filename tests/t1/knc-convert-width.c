// S5-12, ADR-0008 points 4/5, Intel 327364-001 pp.154-189.
// options: -O2 -ftree-vectorize -fopt-info-vec-optimized
// scan-asm-not: %[xy]mm\d+|\b(?:vcvtdq2ps|vcvttps2dq|vcvttps2udq)\b
// scan-asm-func from_f32: \A(?=(?:[\s\S]*\bvcvtps2pd\b){2})(?!(?:[\s\S]*\bvcvtps2pd\b){3})(?=[\s\S]*\bvpermf32x4\s+\$(?:238|0xee),)(?!(?:[\s\S]*\bvpermf32x4\b){2})
// scan-asm-func to_f32: \A(?=(?:[\s\S]*\bvcvtpd2ps\b){2})(?!(?:[\s\S]*\bvcvtpd2ps\b){3})(?=[\s\S]*\bvpermf32x4\s+\$(?:68|0x44),[^\n]*%k[1-7])(?!(?:[\s\S]*\bvpermf32x4\b){2})
// scan-asm-func from_i32: \A(?=(?:[\s\S]*\bvcvtdq2pd\b){2})(?!(?:[\s\S]*\bvcvtdq2pd\b){3})(?=[\s\S]*\bvpermf32x4\s+\$(?:238|0xee),)(?!(?:[\s\S]*\bvpermf32x4\b){2})
// scan-asm-func from_u32: \A(?=(?:[\s\S]*\bvcvtudq2pd\b){2})(?!(?:[\s\S]*\bvcvtudq2pd\b){3})(?=[\s\S]*\bvpermf32x4\s+\$(?:238|0xee),)(?!(?:[\s\S]*\bvpermf32x4\b){2})
// scan-asm-func to_i32: \A(?=(?:[\s\S]*\bvcvtfxpntpd2dq\s+\$3,){2})(?!(?:[\s\S]*\bvcvtfxpntpd2dq\s+\$3,){3})(?=[\s\S]*\bvpermf32x4\s+\$(?:68|0x44),[^\n]*%k[1-7])(?!(?:[\s\S]*\bvpermf32x4\b){2})
// scan-asm-func to_u32: \A(?=(?:[\s\S]*\bvcvtfxpntpd2udq\s+\$3,){2})(?!(?:[\s\S]*\bvcvtfxpntpd2udq\s+\$3,){3})(?=[\s\S]*\bvpermf32x4\s+\$(?:68|0x44),[^\n]*%k[1-7])(?!(?:[\s\S]*\bvpermf32x4\b){2})
// scan-asm-func mixed: \A(?=(?:[\s\S]*\bvcvtps2pd\b){2})(?!(?:[\s\S]*\bvcvtps2pd\b){3})(?=[\s\S]*\bvpermf32x4\s+\$(?:238|0xee),)(?!(?:[\s\S]*\bvpermf32x4\b){2})
// scan-output: knc-convert-width\.c:22:\d+: optimized: loop vectorized using 64 byte vectors
// scan-output: knc-convert-width\.c:23:\d+: optimized: loop vectorized using 64 byte vectors
// scan-output: knc-convert-width\.c:24:\d+: optimized: loop vectorized using 64 byte vectors
// scan-output: knc-convert-width\.c:25:\d+: optimized: loop vectorized using 64 byte vectors
// scan-output: knc-convert-width\.c:26:\d+: optimized: loop vectorized using 64 byte vectors
// scan-output: knc-convert-width\.c:27:\d+: optimized: loop vectorized using 64 byte vectors
// scan-output: knc-convert-width\.c:28:\d+: optimized: loop vectorized using 64 byte vectors
float f[1024] __attribute__((aligned(64)));
double d[1024] __attribute__((aligned(64)));
int i32[1024] __attribute__((aligned(64)));
unsigned u32[1024] __attribute__((aligned(64)));
void from_f32 (void) { for (int i = 0; i < 1024; ++i) d[i] = f[i]; }
void to_f32 (void) { for (int i = 0; i < 1024; ++i) f[i] = d[i]; }
void from_i32 (void) { for (int i = 0; i < 1024; ++i) d[i] = i32[i]; }
void from_u32 (void) { for (int i = 0; i < 1024; ++i) d[i] = u32[i]; }
void to_i32 (void) { for (int i = 0; i < 1024; ++i) i32[i] = d[i]; }
void to_u32 (void) { for (int i = 0; i < 1024; ++i) u32[i] = d[i]; }
void mixed (void) { for (int i = 0; i < 1024; ++i) d[i] = d[i] * f[i] + 1.0; }
