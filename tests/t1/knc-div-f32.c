/* S5-11 / ADR-0003 point 4: the correctly rounded sequence in
   docs/research/knc-div-sqrt.md section 2 must enable ordinary FP32
   division without fast-math.  Fixed whole-vector bounds isolate divv16sf3;
   aligned, variable bounds require cond_divv16sf for the masked tail.
   Neither loop needs an alignment peel.  The entire masked-tail function
   must be free of x87 division, including small-n and remainder paths. */
// options: -O2 -ftree-vectorize -ffp-contract=off
// scan-asm-func div_f32: \bvrcp23ps\b[^\n]*%zmm\d+
// scan-asm-func div_f32: \bvfmadd(?:132|213|231)ps\b[^\n]*%zmm\d+
// scan-asm-loop-not div_f32: \bfdiv\w*\b
// scan-asm-func div_masked_f32: \bvrcp23ps\b[^\n]*%zmm\d+
// scan-asm-func div_masked_f32: \bvfmadd(?:132|213|231)ps\b[^\n]*%zmm\d+\{%k[1-7]\}
// scan-asm-func div_masked_f32: \bvmovaps\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func div_masked_f32: \bvmovaps\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func div_masked_f32: \A(?![\s\S]*\bf(?:div\w*|ld\w*|st\w*)\b)
// scan-asm-not: %(?:xmm|ymm)\d|\bcall\b

void
div_f32 (float *restrict c, const float *restrict a,
         const float *restrict b)
{
  c = __builtin_assume_aligned (c, 64);
  a = __builtin_assume_aligned (a, 64);
  b = __builtin_assume_aligned (b, 64);
  for (int i = 0; i < 1024; ++i)
    c[i] = a[i] / b[i];
}

void
div_masked_f32 (float *restrict c, const float *restrict a,
                const float *restrict b, int n)
{
  c = __builtin_assume_aligned (c, 64);
  a = __builtin_assume_aligned (a, 64);
  b = __builtin_assume_aligned (b, 64);
  for (int i = 0; i < n; ++i)
    c[i] = a[i] / b[i];
}
