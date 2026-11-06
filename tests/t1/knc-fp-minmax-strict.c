// options: -O2 -ftree-vectorize -fno-math-errno
// scan-asm-loop-not maxx_f32: \bvgmax
// scan-asm-loop-not maxx_f64: \bvgmax
// scan-asm-loop-not minx_f32: \bvgmin
// scan-asm-loop-not minx_f64: \bvgmin
// scan-asm-func maxf_f32: \bvgmaxps\b
// scan-asm-func minf_f32: \bvgminps\b
// scan-asm-func maxf_f64: \bvgmaxpd\b
// scan-asm-func minf_f64: \bvgminpd\b
// scan-asm-func rmaxf_f32: \bvgmaxps\s+%zmm\d+\{cdab\}
// scan-asm-func rminf_f32: \bvgminps\s+%zmm\d+\{cdab\}
// scan-asm-func rmaxf_f64: \bvgmaxpd\s+%zmm\d+\{cdab\}
// scan-asm-func rminf_f64: \bvgminpd\s+%zmm\d+\{cdab\}
#include "knc-fp-minmax.h"
