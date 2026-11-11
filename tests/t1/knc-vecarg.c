// S10-01 / ADR-0014 point 1: 64-byte vectors pass in zmm0-zmm7, sharing the
// sequence with scalar float and double, then on the stack; results in zmm0.
// options: -O2 -march=knc
// scan-asm-func vecarg_add: \A\s*vaddps\s+%zmm[01],\s*%zmm[01],\s*%zmm0\s*\n\s*ret\b
// Mixed: i edi, f zmm0, a zmm1, d zmm2, b zmm3, j rsi, c zmm4.
// scan-asm-func vecarg_mixed_a: \bvmovapd\s+%zmm1,\s*%zmm0\b
// scan-asm-func vecarg_mixed_d: \bvmov\w+\s+%zmm2,\s*%zmm0\b
// scan-asm-func vecarg_mixed_b: \bvmovapd\s+%zmm3,\s*%zmm0\b
// scan-asm-func vecarg_mixed_j: \bmovq\s+%rsi,\s*%rax\b
// scan-asm-func vecarg_mixed_c: \bvmovapd\s+%zmm4,\s*%zmm0\b
// scan-asm-func vecarg_int: \bvmovdqa64\s+%zmm1,\s*%zmm0\b
// The ninth and tenth vectors are at entry RSP + 8 and + 72. The aligned
// load is the callee relying on a 64-byte aligned slot.
// scan-asm-func vecarg_ninth: \A\s*vmovaps\s+8\(%rsp\),\s*%zmm0\b
// scan-asm-func vecarg_tenth: \A\s*vmovaps\s+72\(%rsp\),\s*%zmm0\b
// The caller aligns RSP and stores them at RSP and RSP + 64 before the call.
// scan-asm-func vecarg_call: \bandq\s+\$-64,\s*%rsp\b
// scan-asm-func vecarg_call: \bvmovaps\s+%zmm\d+,\s*\(%rsp\)[\s\S]*\bcall\s+vecarg_ext\b
// scan-asm-func vecarg_call: \bvmovaps\s+%zmm\d+,\s*64\(%rsp\)[\s\S]*\bcall\s+vecarg_ext\b
// scan-asm-func vecarg_call: \bvmovaps\s+\(%rdi\),\s*%zmm0\b
// scan-asm-func vecarg_call: \bvmovaps\s+448\(%rdi\),\s*%zmm7\b
typedef float v16sf __attribute__((vector_size(64)));
typedef double v8df __attribute__((vector_size(64)));
typedef long long v8di __attribute__((vector_size(64)));

v16sf vecarg_add(v16sf a, v16sf b) { return a + b; }

#define MIXED int i, float f, v8df a, double d, v8df b, long j, v8df c
v8df vecarg_mixed_a(MIXED) { return a; }
double vecarg_mixed_d(MIXED) { return d; }
v8df vecarg_mixed_b(MIXED) { return b; }
long vecarg_mixed_j(MIXED) { return j; }
v8df vecarg_mixed_c(MIXED) { return c; }
v8di vecarg_int(v16sf a, v8di b) { return b; }

#define TEN v16sf a0, v16sf a1, v16sf a2, v16sf a3, v16sf a4, v16sf a5, \
  v16sf a6, v16sf a7, v16sf a8, v16sf a9
v16sf vecarg_ninth(TEN) { return a8; }
v16sf vecarg_tenth(TEN) { return a9; }
extern v16sf vecarg_ext(TEN);
v16sf vecarg_call(const v16sf *p)
{ return vecarg_ext(p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9]); }
