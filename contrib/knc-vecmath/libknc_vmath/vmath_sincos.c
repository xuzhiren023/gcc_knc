/* libknc_vmath: sin and cos on 8 lanes, sinf and cosf on 16: the copied pointer-form cores and their by-value entry points (ADR-0011, ADR-0014 point 3). */
#include "knc_vmath.h"
#include "vmath_reducer.h"
#define phi_host_sin_e8 __knc_vmath_core_sin_8
#define phi_host_cos_e8 __knc_vmath_core_cos_8
#define phi_host_sinf_e16 __knc_vmath_core_sinf_16
#define phi_host_cosf_e16 __knc_vmath_core_cosf_16
#include "../native/translation/math_algorithms/cos_sin_e/cos_sin_e.c"
#include "vmath_entry.h"
KNC_VMATH_ENTRIES1(sin, 8, __knc_vmath_v8df, uint64_t)
KNC_VMATH_ENTRIES1(cos, 8, __knc_vmath_v8df, uint64_t)
KNC_VMATH_ENTRIES1(sinf, 16, __knc_vmath_v16sf, uint32_t)
KNC_VMATH_ENTRIES1(cosf, 16, __knc_vmath_v16sf, uint32_t)
