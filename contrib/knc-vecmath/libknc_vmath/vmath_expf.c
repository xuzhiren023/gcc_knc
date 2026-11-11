/* libknc_vmath: expf on 16 lanes, the copied pointer-form core and its by-value entry point (ADR-0011, ADR-0014 point 3). */
#include "knc_vmath.h"
#define phi_host_expf_e16 __knc_vmath_core_expf_16
#include "../native/translation/math_algorithms/e_width_experiment/e_expf.c"
#include "vmath_entry.h"
KNC_VMATH_ENTRY1(expf, 16, __knc_vmath_v16sf, uint32_t)
