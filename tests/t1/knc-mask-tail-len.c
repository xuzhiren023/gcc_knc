// S8-02 / E4-04 (ADR-0009 amendment 1 point 9; C6 in
// docs/research/knc-characterization.md): every loop remainder and every
// trip count below the vector length is masked vector code, chosen by
// what C6 measured at the default density (4 threads per core).
// - Known 64-byte alignment: one aligned masked move per access (S4-05).
// - Unknown alignment: a gather or scatter per access with the lane index
//   iota and the element size as scale.  It touches only the lines that
//   hold active elements, so never a line outside the object.  Never a
//   masked unpack/pack pair, never the S4-14 split (vpermd), never a
//   scalar peel.  The full-vector body keeps its unpack/pack pairs.
// - A trip count or remainder below the vector length is a whole-loop or
//   epilogue mask from while_ult (kmov from a GPR), not an x87 loop.
// - x87 stays only where C6 shows it wins: a known remainder or trip count
//   of 1 when aligned (13.2 against 7.1 ticks), of 1 to 3 for the gather
//   form (gather beats x87 from n = 4 at 4 threads).  A constant trip
//   count of 2 never reaches the vectorizer: cunrolli (generic, before
//   vectorization at -O2) unrolls it into two scalar statements, so
//   fix_al_f32_2 is two x87 adds and the aligned masked form starts at a
//   constant 3; a runtime remainder of 2 is masked (fix_al_f32_18).
// - No scalar peel to alignment (C6: it loses to the gather tail at every
//   length), at -O2 and -O3 alike.
// options: -O2 -ftree-vectorize
// scan-asm-func add_f32: \bkmov\s+%(?:e\w+|r\d+d),\s*%k[1-7]
// scan-asm-func add_f32: \bvgatherdps\s+[^\n]*\{%k[1-7]\}
// scan-asm-func add_f32: \bvscatterdps\s+%zmm\d+,\s*[^\n]*\{%k[1-7]\}
// scan-asm-func add_f32: \bjknzd\s
// scan-asm-func add_f32: \bvaddps\s[^\n]*\{%k[1-7]\}
// scan-asm-func add_f32: \bvloadunpacklps\s
// scan-asm-func add_f32: \A(?![\s\S]*\bfld)
// scan-asm-func add_f32: \A(?![\s\S]*\bvpermd\s)
// scan-asm-func add_f32: \A(?![\s\S]*\bv(?:loadunpack|packstore)\w*\s[^\n]*\{%k)
// scan-asm-func add_f64: \bvgatherdpd\s+[^\n]*\{%k[1-7]\}
// scan-asm-func add_f64: \bvscatterdpd\s+%zmm\d+,\s*[^\n]*\{%k[1-7]\}
// scan-asm-func add_f64: \bvaddpd\s[^\n]*\{%k[1-7]\}
// scan-asm-func add_f64: \A(?![\s\S]*\bfld)
// scan-asm-func add_f64: \A(?![\s\S]*\bvpermd\s)
// scan-asm-func add_i32: \bvpgatherdd\s+[^\n]*\{%k[1-7]\}
// scan-asm-func add_i32: \bvpscatterdd\s+%zmm\d+,\s*[^\n]*\{%k[1-7]\}
// scan-asm-func add_i32: \A(?![\s\S]*\baddl\s+\()
// scan-asm-func add_i32: \A(?![\s\S]*\bmovl\s+%e\w+,\s*\([^\n]*,4\))
// scan-asm-func affine_f32: \bvgatherdps\s+[^\n]*\{%k[1-7]\}
// scan-asm-func affine_f32: \bvscatterdps\s+%zmm\d+,\s*[^\n]*\{%k[1-7]\}
// scan-asm-func affine_f32: \bvfmadd\w+\s[^\n]*\{%k[1-7]\}
// scan-asm-func affine_f32: \A(?![\s\S]*\bv(?:mul|add)ps\s)
// scan-asm-func affine_f32: \A(?![\s\S]*\bf(?:add|mul)[sl]?\s)
// scan-asm-func small_f32: \bvgatherdps\s+[^\n]*\{%k[1-7]\}
// scan-asm-func small_f32: \bvscatterdps\s+%zmm\d+,\s*[^\n]*\{%k[1-7]\}
// scan-asm-func small_f32: \A(?![\s\S]*\bfld)
// scan-asm-func small_f32: \A(?![\s\S]*\bvloadunpack)
// scan-asm-func small_al_f32: \bvmovaps\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func small_al_f32: \bvaddps\s[^\n]*\{%k[1-7]\}
// scan-asm-func small_al_f32: \bvmovaps\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func small_al_f32: \A(?![\s\S]*\bfld)
// scan-asm-func small_al_f32: \A(?![\s\S]*\bvmovaps\s+[^\n]*\),\s*%zmm\d+\s*$)
// scan-asm-func fix_al_f32_1: \bflds\s
// scan-asm-func fix_al_f32_1: \A(?![\s\S]*\{%k[1-7]\})
// scan-asm-func fix_al_f32_2: \bflds\s
// scan-asm-func fix_al_f32_2: \A(?![\s\S]*\{%k[1-7]\})
// scan-asm-func fix_al_f32_2: \A(?![\s\S]*\bj\w+\s)
// scan-asm-func fix_al_f32_3: \bvmovaps\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func fix_al_f32_3: \bvaddps\s[^\n]*\{%k[1-7]\}
// scan-asm-func fix_al_f32_3: \bvmovaps\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func fix_al_f32_3: \A(?![\s\S]*\bfld)
// scan-asm-func fix_al_f32_5: \bvmovaps\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func fix_al_f32_5: \bvmovaps\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func fix_al_f32_5: \A(?![\s\S]*\bfld)
// scan-asm-func fix_al_f32_15: \bvmovaps\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func fix_al_f32_15: \A(?![\s\S]*\bfld)
// scan-asm-func fix_al_f32_16: \bvmovaps\s+[^\n]*\),\s*%zmm\d+\s*$
// scan-asm-func fix_al_f32_16: \A(?![\s\S]*\{%k[1-7]\})
// scan-asm-func fix_al_f32_16: \A(?![\s\S]*\bfld)
// scan-asm-func fix_al_f32_17: \bvaddps\s+[^\n]*,\s*%zmm\d+\s*$
// scan-asm-func fix_al_f32_17: \bflds\s
// scan-asm-func fix_al_f32_17: \A(?![\s\S]*\{%k[1-7]\})
// scan-asm-func fix_al_f32_18: \bvmovaps\s+[^\n]*\),\s*%zmm\d+\s*$
// scan-asm-func fix_al_f32_18: \bvmovaps\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func fix_al_f32_18: \bvmovaps\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func fix_al_f32_18: \A(?![\s\S]*\bfld)
// scan-asm-func fix_al_f32_31: \bvmovaps\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func fix_al_f32_31: \A(?![\s\S]*\bfld)
// scan-asm-func fix_al_f32_33: \bflds\s
// scan-asm-func fix_al_f32_33: \A(?![\s\S]*\{%k[1-7]\})
// scan-asm-func fix_f32_1: \bflds\s
// scan-asm-func fix_f32_1: \A(?![\s\S]*\{%k[1-7]\})
// scan-asm-func fix_f32_3: \bflds\s
// scan-asm-func fix_f32_3: \A(?![\s\S]*\{%k[1-7]\})
// scan-asm-func fix_f32_4: \bvgatherdps\s+[^\n]*\{%k[1-7]\}
// scan-asm-func fix_f32_4: \bvscatterdps\s+%zmm\d+,\s*[^\n]*\{%k[1-7]\}
// scan-asm-func fix_f32_4: \A(?![\s\S]*\bfld)
// scan-asm-func fix_f32_4: \A(?![\s\S]*\bvloadunpack)
// scan-asm-func fix_f32_5: \bvgatherdps\s+[^\n]*\{%k[1-7]\}
// scan-asm-func fix_f32_5: \bvscatterdps\s+%zmm\d+,\s*[^\n]*\{%k[1-7]\}
// scan-asm-func fix_f32_5: \bvaddps\s[^\n]*\{%k[1-7]\}
// scan-asm-func fix_f32_5: \A(?![\s\S]*\bfld)
// scan-asm-func fix_f32_5: \A(?![\s\S]*\bvpermd\s)
// scan-asm-func fix_f32_15: \bvgatherdps\s+[^\n]*\{%k[1-7]\}
// scan-asm-func fix_f32_15: \A(?![\s\S]*\bfld)
// scan-asm-func fix_f32_16: \bvloadunpacklps\s
// scan-asm-func fix_f32_16: \A(?![\s\S]*\{%k[1-7]\})
// scan-asm-func fix_f32_16: \A(?![\s\S]*\bfld)
// scan-asm-func fix_f32_17: \bflds\s
// scan-asm-func fix_f32_17: \A(?![\s\S]*\{%k[1-7]\})
// scan-asm-func fix_f32_18: \bflds\s
// scan-asm-func fix_f32_18: \A(?![\s\S]*\{%k[1-7]\})
// scan-asm-func fix_f32_20: \bvloadunpacklps\s
// scan-asm-func fix_f32_20: \bvgatherdps\s+[^\n]*\{%k[1-7]\}
// scan-asm-func fix_f32_20: \bvscatterdps\s+%zmm\d+,\s*[^\n]*\{%k[1-7]\}
// scan-asm-func fix_f32_20: \A(?![\s\S]*\bfld)
// scan-asm-func fix_f32_31: \bvgatherdps\s+[^\n]*\{%k[1-7]\}
// scan-asm-func fix_f32_31: \A(?![\s\S]*\bfld)
// scan-asm-func fix_f32_33: \bflds\s
// scan-asm-func fix_f32_33: \A(?![\s\S]*\{%k[1-7]\})
// scan-asm-func fix_f64_3: \bfldl\s
// scan-asm-func fix_f64_3: \A(?![\s\S]*\{%k[1-7]\})
// scan-asm-func fix_f64_5: \bvgatherdpd\s+[^\n]*\{%k[1-7]\}
// scan-asm-func fix_f64_5: \bvscatterdpd\s+%zmm\d+,\s*[^\n]*\{%k[1-7]\}
// scan-asm-func fix_f64_5: \A(?![\s\S]*\bfld)
// scan-asm-func fix_al_f64_5: \bvmovapd\s+[^\n]*\),\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func fix_al_f64_5: \bvaddpd\s[^\n]*\{%k[1-7]\}
// scan-asm-func fix_al_f64_5: \bvmovapd\s+%zmm\d+,\s*[^\n]*\)\{%k[1-7]\}
// scan-asm-func fix_al_f64_5: \A(?![\s\S]*\bjkn?zd)
// scan-asm-func fix_al_f64_5: \A(?![\s\S]*\bfld)
// scan-asm-not: %(?:xmm|ymm)\d
#define LOOP for (int i = 0; i < n; i++)
#define AL(p) __builtin_assume_aligned (p, 64)

/* Runtime length, unknown alignment: unpack/pack body, gather/scatter
   tail.  */
#define ADD(T, S)                                                         \
  void add_##S (T *restrict c, const T *restrict a, const T *restrict b,  \
                int n)                                                    \
  { LOOP c[i] = a[i] + b[i]; }
ADD (float, f32) ADD (double, f64) ADD (int, i32)

void affine_f32 (float *restrict c, const float *restrict x, float a,
                 float b, int n)
{ LOOP c[i] = a * x[i] + b; }

/* A trip count known to stay below the vector length: one masked
   iteration, no full-vector body.  */
void small_f32 (float *restrict c, const float *restrict a,
                const float *restrict b, unsigned n)
{
  n &= 15;
  for (unsigned i = 0; i < n; i++) c[i] = a[i] + b[i];
}
void small_al_f32 (float *restrict c, const float *restrict a,
                   const float *restrict b, unsigned n)
{
  float *cc = AL (c); const float *aa = AL (a), *bb = AL (b);
  n &= 15;
  for (unsigned i = 0; i < n; i++) cc[i] = aa[i] + bb[i];
}

/* Constant lengths 1-33, unknown and known alignment.  */
#define FIX(T, S, N)                                                      \
  void fix_##S##_##N (T *restrict c, const T *restrict a,                 \
                      const T *restrict b)                                \
  { for (int i = 0; i < N; i++) c[i] = a[i] + b[i]; }                     \
  void fix_al_##S##_##N (T *restrict c, const T *restrict a,              \
                         const T *restrict b)                             \
  {                                                                       \
    T *cc = AL (c); const T *aa = AL (a), *bb = AL (b);                   \
    for (int i = 0; i < N; i++) cc[i] = aa[i] + bb[i];                    \
  }
#define FIX8(T, S, N0, N1, N2, N3, N4, N5, N6, N7)                        \
  FIX (T, S, N0) FIX (T, S, N1) FIX (T, S, N2) FIX (T, S, N3)             \
  FIX (T, S, N4) FIX (T, S, N5) FIX (T, S, N6) FIX (T, S, N7)
FIX8 (float, f32, 1, 2, 3, 4, 5, 6, 7, 8)
FIX8 (float, f32, 9, 10, 11, 12, 13, 14, 15, 16)
FIX8 (float, f32, 17, 18, 19, 20, 21, 22, 23, 24)
FIX8 (float, f32, 25, 26, 27, 28, 29, 30, 31, 32)
FIX (float, f32, 33)
FIX (double, f64, 3) FIX (double, f64, 5)
