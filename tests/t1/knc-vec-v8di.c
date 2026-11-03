// S3-04 / ADR-0005: aligned packed storage; no vector register ABI.
// options: -O2 -march=knc
// scan-asm-func packed_copy: \bvmovdqa64\b
// scan-asm-not: %(?:xmm|ymm)\d|\bvmovups\b|\{z\}
typedef long long packed __attribute__((vector_size(64)));
#define PACKED_VALUES 1LL, 2LL, 3LL, 4LL, 5LL, 6LL, 7LL, 8LL
#include "knc-vec-moves.h"
