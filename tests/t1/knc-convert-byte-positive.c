// S5-16, ADR-0008 point 7; Intel 327364-001 pp.379-384.
// Sixteen source/destination elements per conversion, not byte arithmetic.
// options: -O2 -ftree-vectorize -fopt-info-vec-optimized
// scan-asm-not: %[xy]mm\d+|\bv(?:loadunpack|packstore)\w*[^\n]*\{[us]int(?:8|16)\}
// scan-asm-func i32_u8: \A(?=[\s\S]*\bvmovdqa32\s+[^\n]*\{uint8\}[^\n]*,\s*%zmm\d+)(?!(?:[\s\S]*\{[us]int(?:8|16)\}){2})
// scan-asm-func i32_s8: \A(?=[\s\S]*\bvmovdqa32\s+[^\n]*\{sint8\}[^\n]*,\s*%zmm\d+)(?!(?:[\s\S]*\{[us]int(?:8|16)\}){2})
// scan-asm-func i32_u16: \A(?=[\s\S]*\bvmovdqa32\s+[^\n]*\{uint16\}[^\n]*,\s*%zmm\d+)(?!(?:[\s\S]*\{[us]int(?:8|16)\}){2})
// scan-asm-func f_u8: \A(?=[\s\S]*\bvmovaps\s+[^\n]*\{uint8\}[^\n]*,\s*%zmm\d+)(?!(?:[\s\S]*\{[us]int(?:8|16)\}){2})(?![\s\S]*\bvcvt\w*)
// scan-asm-func f_s16: \A(?=[\s\S]*\bvmovaps\s+[^\n]*\{sint16\}[^\n]*,\s*%zmm\d+)(?!(?:[\s\S]*\{[us]int(?:8|16)\}){2})(?![\s\S]*\bvcvt\w*)
// scan-asm-func u8_i32: \A(?=[\s\S]*\bvpandd\b[\s\S]*\bvmovdqa32\s+%zmm\d+\{uint8\},\s*[^\n]+)(?!(?:[\s\S]*\{[us]int(?:8|16)\}){2})
// scan-asm-func s16_i32: \A(?=[\s\S]*\bvpandd\b[\s\S]*\bvmovdqa32\s+%zmm\d+\{uint16\},\s*[^\n]+)(?!(?:[\s\S]*\{[us]int(?:8|16)\}){2})
// Stable logical line numbers tie each vectorization report to its loop.
// The report names the base mode (V16QI/V16HI for narrow inputs), not the
// 64-byte result. Per the S5-16 lead approval, accept all three base widths;
// the unchanged scans above require one converting zmm access and no xmm/ymm.
// scan-output: knc-convert-byte-positive\.c:101:\d+: optimized: loop vectorized using (?:16|32|64) byte vectors
// scan-output: knc-convert-byte-positive\.c:102:\d+: optimized: loop vectorized using (?:16|32|64) byte vectors
// scan-output: knc-convert-byte-positive\.c:103:\d+: optimized: loop vectorized using (?:16|32|64) byte vectors
// scan-output: knc-convert-byte-positive\.c:104:\d+: optimized: loop vectorized using (?:16|32|64) byte vectors
// scan-output: knc-convert-byte-positive\.c:105:\d+: optimized: loop vectorized using (?:16|32|64) byte vectors
// scan-output: knc-convert-byte-positive\.c:106:\d+: optimized: loop vectorized using (?:16|32|64) byte vectors
// scan-output: knc-convert-byte-positive\.c:107:\d+: optimized: loop vectorized using (?:16|32|64) byte vectors
unsigned char u8[1024] __attribute__((aligned(64)));
signed char s8[1024] __attribute__((aligned(64)));
unsigned short u16[1024] __attribute__((aligned(64)));
short s16[1024] __attribute__((aligned(64)));
int i32[1024] __attribute__((aligned(64)));
float f[1024] __attribute__((aligned(64)));
#line 101 "knc-convert-byte-positive.c"
void i32_u8 (void) { for (int i = 0; i < 1024; ++i) i32[i] = u8[i]; }
void i32_s8 (void) { for (int i = 0; i < 1024; ++i) i32[i] = s8[i]; }
void i32_u16 (void) { for (int i = 0; i < 1024; ++i) i32[i] = u16[i]; }
void f_u8 (void) { for (int i = 0; i < 1024; ++i) f[i] = u8[i]; }
void f_s16 (void) { for (int i = 0; i < 1024; ++i) f[i] = s16[i]; }
void u8_i32 (void) { for (int i = 0; i < 1024; ++i) u8[i] = i32[i] & 255; }
void s16_i32 (void) { for (int i = 0; i < 1024; ++i) s16[i] = i32[i]; }
