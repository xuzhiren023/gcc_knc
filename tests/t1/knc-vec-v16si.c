// S3-04 / ADR-0005: aligned packed storage; no vector register ABI.
// options: -O2 -march=knc
// scan-asm-func packed_copy: \bvmovdqa32\b
// scan-asm-not: %(?:xmm|ymm)\d|\bvmovups\b|\{z\}
typedef int packed __attribute__((vector_size(64)));
#define PACKED_VALUES 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
#include "knc-vec-moves.h"
