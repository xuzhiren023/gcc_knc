// options: -O3 -march=knc --param=vect-max-peeling-for-alignment=0
// Disable alignment peeling so unannotated inputs stay unaligned in this test.
// No misaligned fold: arithmetic stays, and none of it reads memory.
// scan-asm-func add_f32: \bvaddps\s+%zmm
// scan-asm-func add_f32: \A(?![\s\S]*\bv(?:add|sub|mul)p[sd]\s[^\n]*\()
// scan-asm-func sub_f32: \bvsubps\s+%zmm
// scan-asm-func sub_f32: \A(?![\s\S]*\bv(?:add|sub|mul)p[sd]\s[^\n]*\()
// scan-asm-func mul_f32: \bvmulps\s+%zmm
// scan-asm-func mul_f32: \A(?![\s\S]*\bv(?:add|sub|mul)p[sd]\s[^\n]*\()
// scan-asm-func add_f64: \bvaddpd\s+%zmm
// scan-asm-func add_f64: \A(?![\s\S]*\bv(?:add|sub|mul)p[sd]\s[^\n]*\()
// scan-asm-func sub_f64: \bvsubpd\s+%zmm
// scan-asm-func sub_f64: \A(?![\s\S]*\bv(?:add|sub|mul)p[sd]\s[^\n]*\()
// scan-asm-func mul_f64: \bvmulpd\s+%zmm
// scan-asm-func mul_f64: \A(?![\s\S]*\bv(?:add|sub|mul)p[sd]\s[^\n]*\()
// The 64-byte-aligned b is still folded.
// scan-asm-func add_f32_b64: \bvaddps\s+-?\w*\(
// scan-asm-func sub_f32_b64: \bvsubps\s+-?\w*\(
// scan-asm-func mul_f32_b64: \bvmulps\s+-?\w*\(
// scan-asm-func add_f64_b64: \bvaddpd\s+-?\w*\(
// scan-asm-func sub_f64_b64: \bvsubpd\s+-?\w*\(
// scan-asm-func mul_f64_b64: \bvmulpd\s+-?\w*\(
#include "knc-vec-fold.h"
