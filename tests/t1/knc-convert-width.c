// S5-12, ADR-0008 points 4/5, Intel 327364-001 pp.154-189.
// options: -O2 -ftree-vectorize
// scan-asm-not: %[xy]mm\d+|\b(?:vcvtdq2ps|vcvttps2dq|vcvttps2udq)\b
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
