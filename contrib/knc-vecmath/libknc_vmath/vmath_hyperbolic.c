/* libknc_vmath: sinh, cosh and tanh on 8 lanes and sinhf, coshf and tanhf on 16: the copied pointer-form cores, which take the function as an operation number, and their by-value entry points (ADR-0011, ADR-0014 point 3). */
#include "knc_vmath.h"
#define phi_hyperbolic_e8 __knc_vmath_core_hyperbolic_8
#define phi_hyperbolic_e16 __knc_vmath_core_hyperbolic_16
#include "../native/translation/math_algorithms/hyperbolic_e/hyperbolic_e.c"
#include "vmath_entry.h"
#define HYPERBOLIC(name, lanes, vector, word, operation) \
  static int __knc_vmath_core_##name##_##lanes(const word in[lanes], unsigned active, \
                                               const word merge[lanes], word out[lanes]) \
  { \
    return __knc_vmath_core_hyperbolic_##lanes(operation, in, active, merge, out); \
  } \
  KNC_VMATH_ENTRIES1(name, lanes, vector, word)
HYPERBOLIC(sinh, 8, __knc_vmath_v8df, uint64_t, 0)
HYPERBOLIC(cosh, 8, __knc_vmath_v8df, uint64_t, 1)
HYPERBOLIC(tanh, 8, __knc_vmath_v8df, uint64_t, 2)
HYPERBOLIC(sinhf, 16, __knc_vmath_v16sf, uint32_t, 0)
HYPERBOLIC(coshf, 16, __knc_vmath_v16sf, uint32_t, 1)
HYPERBOLIC(tanhf, 16, __knc_vmath_v16sf, uint32_t, 2)
