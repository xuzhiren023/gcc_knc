/* libknc_vmath: log10f on 16 lanes, the copied pointer-form core and its by-value entry points (ADR-0011, ADR-0014 point 3). */
#include "knc_vmath.h"
#define phi_host_log10_e8 __knc_vmath_core_log10_8
#define phi_host_log10f_e16 __knc_vmath_core_log10f_16
#include "../native/translation/math_algorithms/log10_e/e_log10f.c"
#include "vmath_entry.h"
KNC_VMATH_ENTRIES1(log10f, 16, __knc_vmath_v16sf, uint32_t)
