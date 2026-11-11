/* libknc_vmath: log on 8 lanes, the copied pointer-form core and its by-value entry point (ADR-0011, ADR-0014 point 3). */
#include "knc_vmath.h"
#define phi_host_log_e8 __knc_vmath_core_log_8
#include "../native/translation/math_algorithms/e_width_experiment/e_log.c"
#include "vmath_entry.h"
KNC_VMATH_ENTRY1(log, 8, __knc_vmath_v8df, uint64_t)
