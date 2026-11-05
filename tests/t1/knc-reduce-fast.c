// S5-07 / ADR-0008 point 2: reassociation is explicitly enabled here.
// options: -O3 -ffast-math
// scan-asm-func sum_f32: \bvpermf32x4\s+\$78,[\s\S]*\bvaddps\s[\s\S]*\bvpermf32x4\s+\$177,[\s\S]*\bvaddps\s[\s\S]*\bvaddps\s+%zmm\d+\{badc\}[\s\S]*\bvaddps\s+%zmm\d+\{cdab\}
// scan-asm-func sum_f64: \bvpermf32x4\s+\$78,[\s\S]*\bvaddpd\s[\s\S]*\bvaddpd\s+%zmm\d+\{badc\}[\s\S]*\bvaddpd\s+%zmm\d+\{cdab\}
#include "knc-reduce-fp.h"
