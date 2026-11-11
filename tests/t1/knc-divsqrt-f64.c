/* S10-09 / ADR-0003 point 4: the correctly rounded sequences of
   docs/research/knc-div-sqrt.md section 3 let ordinary FP64 division and
   square root vectorize without fast-math.  Fixed whole-vector bounds
   isolate divv8df3 and sqrtv8df2; a variable bound needs cond_divv8df for
   the masked tail, and that whole function must be free of x87 division
   (an x87 FP64 quotient is rounded twice).  No loop needs an alignment
   peel.  The estimates are the FP32 ones, on the narrowed significand.  */
// options: -O2 -march=knc -fno-math-errno
// scan-asm-func div_f64: \bvrcp23ps\b[^\n]*%zmm\d+
// scan-asm-func div_f64: \bvfmadd(?:132|213|231)pd\b[^\n]*%zmm\d+\{%k[1-7]\}
// scan-asm-loop-not div_f64: \bfdiv\w*\b
// scan-asm-func div_masked_f64: \bvrcp23ps\b[^\n]*%zmm\d+
// scan-asm-func div_masked_f64: \bvfmadd(?:132|213|231)pd\b[^\n]*%zmm\d+\{%k[1-7]\}
// scan-asm-func div_masked_f64: \bvmovapd\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func div_masked_f64: \bvmovapd\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func div_masked_f64: \A(?![\s\S]*\bf(?:div\w*|ld\w*|st\w*)\b)
// scan-asm-func sqrt_f64: \bvrsqrt23ps\b[^\n]*%zmm\d+
// scan-asm-func sqrt_f64: \bvfmadd(?:132|213|231)pd\b[^\n]*%zmm\d+\{%k[1-7]\}
// scan-asm-func sqrt_f64: \bvfixupnanpd\b[^\n]*%zmm\d+
// scan-asm-loop-not sqrt_f64: \bfsqrt\b
// scan-asm-not: %(?:xmm|ymm)\d|\bcall\b

void
div_f64 (double *restrict c, const double *restrict a,
	 const double *restrict b)
{
  c = __builtin_assume_aligned (c, 64);
  a = __builtin_assume_aligned (a, 64);
  b = __builtin_assume_aligned (b, 64);
  for (int i = 0; i < 1024; ++i)
    c[i] = a[i] / b[i];
}

void
div_masked_f64 (double *restrict c, const double *restrict a,
		const double *restrict b, int n)
{
  c = __builtin_assume_aligned (c, 64);
  a = __builtin_assume_aligned (a, 64);
  b = __builtin_assume_aligned (b, 64);
  for (int i = 0; i < n; ++i)
    c[i] = a[i] / b[i];
}

void
sqrt_f64 (double *restrict c, const double *restrict a)
{
  c = __builtin_assume_aligned (c, 64);
  a = __builtin_assume_aligned (a, 64);
  for (int i = 0; i < 1024; ++i)
    c[i] = __builtin_sqrt (a[i]);
}
