// S8-04 (E5-11 part 2): a loop-invariant scalar that the vectorizer
// broadcasts is loaded once with vbroadcastss/vbroadcastsd from its own
// address (IMCI m32/m64 broadcast, Intel 327364-001), not through x87 and a
// stack slot.  The M2 matrix kernels load x[j] inside the vector loop and
// broadcast it; before S8-04 that cost flds, fstps, a dependent
// vbroadcastss reload, vpermf32x4 and a swizzle per FMA (five instructions
// and a store-to-load round trip), where the hand-written IMCI has one.
// The CONSTRUCTOR repeats the scalar sixteen times, so expand cannot fold
// the load and the register broadcast must be one combinable vec_duplicate.
// The positive scans accept the broadcast as one vbroadcastss/sd or folded
// into the arithmetic as a {1to16}/{1to8} memory operand (S8-06, which
// closed this ticket's fix, owner 2026-11-09), from any displacement or
// index on a non-stack base;
// the loop scans forbid only the bridge (an x87 store to a stack slot, a
// broadcast from the stack, vpermf32x4), not x87 itself: the remainder for
// count < 16 is legitimate scalar x87 code and stays.
// options: -O2 -ftree-vectorize -ffp-contract=fast
// scan-asm-func mat8_f32: ^[ \t]*(?:vbroadcastss[ \t]+[^,(]*\((?!%rsp)%r\w+[^)]*\), %zmm\d+|v\w+[ \t]+[^,(]*\((?!%rsp)%r\w+[^)]*\)\{1to16\})
// scan-asm-loop-not mat8_f32: ^[ \t]*(?:fstp?[sl][ \t]+[^\n]*\(%rsp\)|vbroadcasts[sd][ \t]+[^\n]*\(%rsp\)|vpermf32x4\b)
// scan-asm-func mat16_f32: ^[ \t]*(?:vbroadcastss[ \t]+[^,(]*\((?!%rsp)%r\w+[^)]*\), %zmm\d+|v\w+[ \t]+[^,(]*\((?!%rsp)%r\w+[^)]*\)\{1to16\})
// scan-asm-loop-not mat16_f32: ^[ \t]*(?:fstp?[sl][ \t]+[^\n]*\(%rsp\)|vbroadcasts[sd][ \t]+[^\n]*\(%rsp\)|vpermf32x4\b)
// scan-asm-func mat8_f64: ^[ \t]*(?:vbroadcastsd[ \t]+[^,(]*\((?!%rsp)%r\w+[^)]*\), %zmm\d+|v\w+[ \t]+[^,(]*\((?!%rsp)%r\w+[^)]*\)\{1to8\})
// scan-asm-loop-not mat8_f64: ^[ \t]*(?:fstp?[sl][ \t]+[^\n]*\(%rsp\)|vbroadcasts[sd][ \t]+[^\n]*\(%rsp\)|vpermf32x4\b)
// scan-asm-not: %(?:xmm|ymm)\d
#define R __restrict
/* The M2 fixture's shape: column-major fixed matrix with leading dimension
   16 times a stream of input vectors; the row loop over count is the
   vector loop, the j loop stays inside it and broadcasts x[j].  */
#define MATRIX(T, S, D)                                                   \
  void mat##D##_##S (T *R y, const T *R x, const T *R a, unsigned long n)  \
  {                                                                       \
    for (unsigned long base = 0; base < n; base += D)                     \
      {                                                                   \
        unsigned long count = n - base < D ? n - base : D;                \
        for (unsigned long r = 0; r < count; ++r)                         \
          {                                                               \
            T sum = 0;                                                    \
            for (unsigned j = 0; j < D; ++j)                              \
              sum = sum + a[j * 16 + r] * x[(base / D) * 16 + j];         \
            y[base + r] = sum;                                            \
          }                                                               \
      }                                                                   \
  }
MATRIX (float, f32, 8)
MATRIX (float, f32, 16)
MATRIX (double, f64, 8)
