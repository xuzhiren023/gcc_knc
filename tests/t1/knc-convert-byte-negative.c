// S5-16: no byte compares or misaligned converted memory accesses.
// options: -O2 -ftree-vectorize
// scan-asm-not: \{[us]int(?:8|16)\}|%[xy]mm\d+
// scan-asm-func byte_compare: \A(?![\s\S]*%zmm\d+)(?=[\s\S]*\bcmpb\b)
// The offset is one element past a 64-byte boundary. There are exactly
// 16 elements: peeling cannot leave a full 16-element converted access.
// Both byte (16-byte alignment) and word (32-byte alignment) memory forms
// must therefore stay scalar; an unaligned loadunpack/packstore is forbidden.
unsigned char u8[1024] __attribute__((aligned(64)));
signed char s8[32] __attribute__((aligned(64)));
unsigned short u16[32] __attribute__((aligned(64)));
short s16[32] __attribute__((aligned(64)));
int i32[1024] __attribute__((aligned(64)));
float f[16] __attribute__((aligned(64)));
void byte_compare (void) { for (int i = 0; i < 1024; ++i) i32[i] = u8[i] > 7; }
void misaligned_u8_load (void) { for (int i = 0; i < 16; ++i) i32[i] = u8[i + 1]; }
void misaligned_s8_load (void) { for (int i = 0; i < 16; ++i) i32[i] = s8[i + 1]; }
void misaligned_u16_load (void) { for (int i = 0; i < 16; ++i) i32[i] = u16[i + 1]; }
void misaligned_u8_float (void) { for (int i = 0; i < 16; ++i) f[i] = u8[i + 1]; }
void misaligned_s16_float (void) { for (int i = 0; i < 16; ++i) f[i] = s16[i + 1]; }
void misaligned_u8_store (void) { for (int i = 0; i < 16; ++i) u8[i + 1] = i32[i] & 255; }
void misaligned_s16_store (void) { for (int i = 0; i < 16; ++i) s16[i + 1] = i32[i]; }
