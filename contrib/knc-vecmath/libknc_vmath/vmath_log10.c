/* libknc_vmath: log10 on 8 lanes, the copied pointer-form core and its by-value entry points (ADR-0011, ADR-0014 point 3). */
#include "knc_vmath.h"
#define phi_host_log10_e8 __knc_vmath_core_log10_8
#define phi_host_log10f_e16 __knc_vmath_core_log10f_16
#include "../native/translation/math_algorithms/log10_e/e_log10.c"
#include "vmath_entry.h"
KNC_VMATH_ENTRIES1(log10, 8, __knc_vmath_v8df, uint64_t)
