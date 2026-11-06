/* Explicit additive i64-predicate scalar-event powf candidate; no target ABI/accuracy qualification. */
#include "knc_mvec_abi.h"
#include <stdint.h>
#include <string.h>
#if defined(PW_ENABLE_NEGATIVE_CONTROL) || defined(__FAST_MATH__)
#error "production powf export forbids negative controls and fast math"
#endif
#define phi_host_powf_register_i64_scalar_events_e16 knc_mvec_algorithm_powf_register_i64_scalar_events_e16
#include "../../math_algorithms/powf_e16/powf_e16_register_i64_scalar_events.c"
#undef phi_host_powf_register_i64_scalar_events_e16

knc_mvec_f32x16 __knc_vmath_powf_16(knc_mvec_f32x16 x,knc_mvec_f32x16 y) {
  uint32_t xb[16],yb[16],value[16];
  memcpy(xb,&x,64);memcpy(yb,&y,64);
  if(knc_mvec_algorithm_powf_register_i64_scalar_events_e16(xb,yb,65535u,xb,value))__builtin_trap();
  knc_mvec_f32x16 result;memcpy(&result,value,64);return result;
}
