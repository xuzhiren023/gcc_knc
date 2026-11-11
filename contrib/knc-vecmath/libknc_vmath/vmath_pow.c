/* libknc_vmath: pow on 8 lanes, the copied pointer-form core and its by-value entry point (ADR-0011, ADR-0014 point 3). */
#include "knc_vmath.h"
#define phi_host_pow_e8 __knc_vmath_core_pow_8
#include "../native/translation/math_algorithms/pow_e8/pow_e8.c"
#include "vmath_entry.h"
KNC_VMATH_ENTRY2(pow, 8, __knc_vmath_v8df, uint64_t)
