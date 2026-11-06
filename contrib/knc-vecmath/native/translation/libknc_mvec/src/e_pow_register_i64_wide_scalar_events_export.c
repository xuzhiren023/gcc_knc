/* Explicit scalar-DP-event variant. Event/trap/result/ABI qualification is pending. */
/* Explicit full64B integer-storage DP pow variant; no inherited target/accuracy qualification. */
#include "knc_mvec_abi.h"
#include <stdint.h>
#include <string.h>
#if defined(PW_ENABLE_NEGATIVE_CONTROL) || defined(__FAST_MATH__)
#error "production pow export forbids negative controls and fast math"
#endif
#define phi_host_pow_register_i64_wide_scalar_events_e8 knc_mvec_algorithm_pow_register_i64_wide_scalar_events_e8
#include "../../math_algorithms/pow_e8/pow_e8_register_i64_wide_scalar_events.c"
#undef phi_host_pow_register_i64_wide_scalar_events_e8
knc_mvec_f64x8 __knc_vmath_pow_8(knc_mvec_f64x8 x,knc_mvec_f64x8 y) {
  uint64_t xb[8],yb[8],out[8];memcpy(xb,&x,64);memcpy(yb,&y,64);
  if(knc_mvec_algorithm_pow_register_i64_wide_scalar_events_e8(xb,yb,255u,xb,out))__builtin_trap();
  knc_mvec_f64x8 result;memcpy(&result,out,64);return result;
}
