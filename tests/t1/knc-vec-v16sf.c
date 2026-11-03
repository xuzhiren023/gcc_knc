// S3-04 / ADR-0005: aligned packed storage; no vector register ABI.
// options: -O2 -march=knc
typedef float packed __attribute__((vector_size(64)));
#define PACKED_FP 1
#define PACKED_REPEAT(x) x,x,x,x,x,x,x,x,x,x,x,x,x,x,x,x
#define PACKED_SQRT(x) __builtin_sqrtf(x)
#define PACKED_VALUES 1.0f, 2.0f, 3.0f, 4.0f, 5.0f, 6.0f, 7.0f, 8.0f, 9.0f, 10.0f, 11.0f, 12.0f, 13.0f, 14.0f, 15.0f, 16.0f
#include "knc-vec-moves.h"
