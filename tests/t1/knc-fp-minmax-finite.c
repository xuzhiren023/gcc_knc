// options: -O2 -ftree-vectorize -fno-math-errno -ffinite-math-only -fno-signed-zeros
// scan-asm-func maxx_f32: \bvgmaxps\b
// scan-asm-func minx_f32: \bvgminps\b
// scan-asm-func maxx_f64: \bvgmaxpd\b
// scan-asm-func minx_f64: \bvgminpd\b
// scan-asm-func rmaxx_f32: \bvgmaxps\s+%zmm\d+\{cdab\}
// scan-asm-func rminx_f32: \bvgminps\s+%zmm\d+\{cdab\}
// scan-asm-func rmaxx_f64: \bvgmaxpd\s+%zmm\d+\{cdab\}
// scan-asm-func rminx_f64: \bvgminpd\s+%zmm\d+\{cdab\}
#include "knc-fp-minmax.h"
