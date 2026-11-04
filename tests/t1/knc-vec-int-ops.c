// S3-09 / ADR-0005 point 3: each V16SI and V8DI integer operation is exactly
// one IMCI instruction, and an integer broadcast reads its scalar from memory.
// k1om has no vpaddq, vpsubq or vpmullq, so V8DI gets logic only.
// options: -O2
// scan-asm-func add_v16si: \A(?![\s\S]*\bvpaddd\b[\s\S]*\bvpaddd\b)[\s\S]*\bvpaddd\s[^\n]*%zmm\d+
// scan-asm-func sub_v16si: \A(?![\s\S]*\bvpsubd\b[\s\S]*\bvpsubd\b)[\s\S]*\bvpsubd\s[^\n]*%zmm\d+
// scan-asm-func mul_v16si: \A(?![\s\S]*\bvpmulld\b[\s\S]*\bvpmulld\b)[\s\S]*\bvpmulld\s[^\n]*%zmm\d+
// scan-asm-func and_v16si: \A(?![\s\S]*\bvpandd\b[\s\S]*\bvpandd\b)[\s\S]*\bvpandd\s[^\n]*%zmm\d+
// scan-asm-func ior_v16si: \A(?![\s\S]*\bvpord\b[\s\S]*\bvpord\b)[\s\S]*\bvpord\s[^\n]*%zmm\d+
// scan-asm-func xor_v16si: \A(?![\s\S]*\bvpxord\b[\s\S]*\bvpxord\b)[\s\S]*\bvpxord\s[^\n]*%zmm\d+
// scan-asm-func and_v8di: \A(?![\s\S]*\bvpandq\b[\s\S]*\bvpandq\b)[\s\S]*\bvpandq\s[^\n]*%zmm\d+
// scan-asm-func ior_v8di: \A(?![\s\S]*\bvporq\b[\s\S]*\bvporq\b)[\s\S]*\bvporq\s[^\n]*%zmm\d+
// scan-asm-func xor_v8di: \A(?![\s\S]*\bvpxorq\b[\s\S]*\bvpxorq\b)[\s\S]*\bvpxorq\s[^\n]*%zmm\d+
// The float-bits idiom must stay integer logic: KNC has no vandps.
// scan-asm-func abs_bits_v16sf: \bvpandd\s[^\n]*%zmm\d+
// scan-asm-func broadcast_v16si: \bvpbroadcastd\s+[-\w.]*\(
// scan-asm-func broadcast_v8di: \bvpbroadcastq\s+[-\w.]*\(
// scan-asm-not: %(?:xmm|ymm)\d|\bvp(?:add|sub|mull)q\b

typedef int v16si __attribute__ ((vector_size (64)));
typedef long long v8di __attribute__ ((vector_size (64)));
typedef float v16sf __attribute__ ((vector_size (64)));

#define BINARY(NAME, T, OP) \
  void NAME (const T *a, const T *b, T *c) { *c = *a OP *b; }

BINARY (add_v16si, v16si, +)
BINARY (sub_v16si, v16si, -)
BINARY (mul_v16si, v16si, *)
BINARY (and_v16si, v16si, &)
BINARY (ior_v16si, v16si, |)
BINARY (xor_v16si, v16si, ^)
BINARY (and_v8di, v8di, &)
BINARY (ior_v8di, v8di, |)
BINARY (xor_v8di, v8di, ^)

void
abs_bits_v16sf (const v16sf *a, const v16sf *b, v16sf *c)
{
  *c = (v16sf) ((v16si) (*a + *b) & 0x7fffffff);
}

void
broadcast_v16si (const int *p, v16si *c)
{
  *c = (v16si) {} + *p;
}

void
broadcast_v8di (const long long *p, v8di *c)
{
  *c = (v8di) {} + *p;
}
