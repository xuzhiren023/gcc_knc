/* libknc_vmath: atanf and atan2f on 16 lanes and atan2 on 8: the copied pointer-form cores (the compensated revision, atan_e_v2.c) and their by-value entry points (ADR-0011, ADR-0014 point 3). The copy has no 8-lane atan. */
#include "knc_vmath.h"
#define phi_host_atanf_e16 __knc_vmath_core_atanf_16
#define phi_host_atan2f_e16 __knc_vmath_core_atan2f_16
#define phi_host_atan2_e8 __knc_vmath_core_atan2_8
#include "../native/translation/math_algorithms/atan_e/atan_e_v2.c"
#include "vmath_entry.h"
KNC_VMATH_ENTRIES1(atanf, 16, __knc_vmath_v16sf, uint32_t)
KNC_VMATH_ENTRIES2(atan2f, 16, __knc_vmath_v16sf, uint32_t)
KNC_VMATH_ENTRIES2(atan2, 8, __knc_vmath_v8df, uint64_t)
