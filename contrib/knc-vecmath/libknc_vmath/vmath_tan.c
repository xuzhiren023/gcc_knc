/* libknc_vmath: tan on 8 lanes and tanf on 16: the copied pointer-form cores and their by-value entry points (ADR-0011, ADR-0014 point 3). */
#include "knc_vmath.h"
#include "vmath_reducer.h"
#define phi_host_tan_e8 __knc_vmath_core_tan_8
#define phi_host_tanf_e16 __knc_vmath_core_tanf_16
#include "../native/translation/math_algorithms/tan_e/tan_e.c"
#include "vmath_entry.h"
KNC_VMATH_ENTRIES1(tan, 8, __knc_vmath_v8df, uint64_t)
KNC_VMATH_ENTRIES1(tanf, 16, __knc_vmath_v16sf, uint32_t)
