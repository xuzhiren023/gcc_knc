// S3-04 / ADR-0005: aligned packed storage; no vector register ABI.
// options: -O2 -march=knc
typedef double packed __attribute__((vector_size(64)));
#define PACKED_VALUES 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0
#include "knc-vec-moves.h"
