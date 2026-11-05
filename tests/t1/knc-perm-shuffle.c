// S5-06 / ADR-0008 point 1: constant __builtin_shuffle selectors reach each
// recipe of ix86_knc_vectorize_vec_perm_const, cheapest first: identity, a
// register swizzle (32-bit groups of 128 bits, 64-bit groups of 256 bits;
// Intel 327364-001 tables 2.2 and 2.3), vpermf32x4, vpshufd, valignd, a
// blend, one vpermd, and vpermd plus a write-masked vpermd.  8-lane modes
// use dword-pair vpermd indices (VPERMD reads index bits 3:0, p.480).
// options: -O3
// scan-asm-func id_f32: \A(?![\s\S]*\b(?:vpermd|vpermf32x4|vpshufd|valignd|vblendm\w+)\s|[\s\S]*\{[a-d]{4}\})
// scan-asm-func swz_cdab_f32: \bvmovdqa32\s+%zmm\d+\{cdab\},\s*%zmm\d+
// scan-asm-func swz_dacb_i32: \bvmovdqa32\s+%zmm\d+\{dacb\},\s*%zmm\d+
// scan-asm-func swz_bbbb_f64: \bvmovdqa64\s+%zmm\d+\{bbbb\},\s*%zmm\d+
// scan-asm-func swz_badc_i64: \bvmovdqa64\s+%zmm\d+\{badc\},\s*%zmm\d+
// scan-asm-func pf_f32: \bvpermf32x4\s+\$114,\s*%zmm\d+,\s*%zmm\d+
// scan-asm-func pf_f64: \bvpermf32x4\s+\$27,\s*%zmm\d+,\s*%zmm\d+
// scan-asm-func pshufd_i32: \bvpshufd\s+\$27,\s*%zmm\d+,\s*%zmm\d+
// scan-asm-func pshufd_f64: \bvpshufd\s+\$68,\s*%zmm\d+,\s*%zmm\d+
// scan-asm-func align_i32: \bvalignd\s+\$3,\s*%zmm\d+,\s*%zmm\d+,\s*%zmm\d+
// scan-asm-func align_f64: \bvalignd\s+\$2,\s*%zmm(\d+),\s*%zmm\1,\s*%zmm\d+
// scan-asm-func blend_f32: \bvblendmps\s+[^\n]*,\s*%zmm\d+,\s*%zmm\d+\{%k[1-7]\}
// scan-asm-func perm1_f32: \bvpermd\s
// scan-asm-func perm1_f32: \A(?![\s\S]*\{%k)
// scan-asm-func perm1_i64: \bvpermd\s
// scan-asm-func perm2_f32: \bvpermd\s+%zmm\d+,\s*%zmm\d+,\s*%zmm\d+\s*\n[\s\S]*\bvpermd\s+[^\n]*\{%k[1-7]\}
// scan-asm-func perm2_i64: \bvpermd\s+%zmm\d+,\s*%zmm\d+,\s*%zmm\d+\s*\n[\s\S]*\bvpermd\s+[^\n]*\{%k[1-7]\}
// scan-asm: \.long\s+6\n\s*\.long\s+7\n\s*\.long\s+0\n\s*\.long\s+1\n\s*\.long\s+14\n\s*\.long\s+15\n
// scan-asm-not: \bvpermt2|\bvpermq\b|%(?:xmm|ymm)\d
typedef float f32 __attribute__ ((vector_size (64)));
typedef int i32 __attribute__ ((vector_size (64)));
typedef double f64 __attribute__ ((vector_size (64)));
typedef long i64 __attribute__ ((vector_size (64)));

#define ONE(NAME, T, IT, ...)                                             \
  void NAME (T *r, const T *a)                                            \
  { *r = __builtin_shuffle (*a, (IT) { __VA_ARGS__ }); }
#define TWO(NAME, T, IT, ...)                                             \
  void NAME (T *r, const T *a, const T *b)                                \
  { *r = __builtin_shuffle (*a, *b, (IT) { __VA_ARGS__ }); }

ONE (id_f32, f32, i32, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)
ONE (swz_cdab_f32, f32, i32, 1, 0, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10, 13, 12, 15, 14)
ONE (swz_dacb_i32, i32, i32, 1, 2, 0, 3, 5, 6, 4, 7, 9, 10, 8, 11, 13, 14, 12, 15)
ONE (swz_bbbb_f64, f64, i64, 1, 1, 1, 1, 5, 5, 5, 5)
ONE (swz_badc_i64, i64, i64, 2, 3, 0, 1, 6, 7, 4, 5)
ONE (pf_f32, f32, i32, 8, 9, 10, 11, 0, 1, 2, 3, 12, 13, 14, 15, 4, 5, 6, 7)
ONE (pf_f64, f64, i64, 6, 7, 4, 5, 2, 3, 0, 1)
ONE (pshufd_i32, i32, i32, 3, 2, 1, 0, 7, 6, 5, 4, 11, 10, 9, 8, 15, 14, 13, 12)
ONE (pshufd_f64, f64, i64, 0, 0, 2, 2, 4, 4, 6, 6)
TWO (align_i32, i32, i32, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18)
ONE (align_f64, f64, i64, 1, 2, 3, 4, 5, 6, 7, 0)
TWO (blend_f32, f32, i32, 0, 17, 2, 19, 4, 21, 6, 23, 8, 25, 10, 27, 12, 29, 14, 31)
ONE (perm1_f32, f32, i32, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0)
ONE (perm1_i64, i64, i64, 3, 0, 7, 2, 5, 1, 6, 4)
TWO (perm2_f32, f32, i32, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30)
TWO (perm2_i64, i64, i64, 0, 2, 4, 6, 8, 10, 12, 14)
