/* libknc_vmath: powf on 16 lanes, the copied pointer-form core and its by-value entry point (ADR-0011, ADR-0014 point 3). */
#include "knc_vmath.h"
#define phi_host_powf_e16 __knc_vmath_core_powf_16
#include "../native/translation/math_algorithms/powf_e16/powf_e16.c"
#include "vmath_entry.h"
KNC_VMATH_ENTRY2(powf, 16, __knc_vmath_v16sf, uint32_t)
