/* Additive N5 scalar-bookkeeping revision3 source wiring; unqualified successor. */
/* Three observed atan-family exports, using compensated source revision3.
 * Source wiring only; target ABI/masks/numerics/runtime remain unqualified. */
#include "e_export_adapter.h"
#define phi_host_atanf_e16 knc_mvec_algorithm_atanf_e16
#define phi_host_atan2f_e16 knc_mvec_algorithm_atan2f_e16
#define phi_host_atan2_e8 knc_mvec_algorithm_atan2_e8
#include "../../math_algorithms/atan_e/atan_e_v3_scalar_bookkeeping.c"
#undef phi_host_atanf_e16
#undef phi_host_atan2f_e16
#undef phi_host_atan2_e8
KNC_MVEC_E_EXPORT(__knc_vmath_atanf_16,knc_mvec_f32x16,uint32_t,16,knc_mvec_algorithm_atanf_e16)
#define ATAN_BINARY_EXPORT(NAME,VECTOR,WORD,LANES,ALGORITHM) \
VECTOR NAME(VECTOR y,VECTOR x){ \
  WORD a[LANES],b[LANES],output[LANES];VECTOR result; \
  _Static_assert(sizeof y==64&&sizeof x==64&&sizeof output==64,"binary export width mismatch"); \
  memcpy(a,&y,64);memcpy(b,&x,64); \
  if(ALGORITHM(a,b,(1u<<(LANES))-1u,a,output))__builtin_trap(); \
  memcpy(&result,output,64);return result; \
}
ATAN_BINARY_EXPORT(__knc_vmath_atan2f_16,knc_mvec_f32x16,uint32_t,16,knc_mvec_algorithm_atan2f_e16)
ATAN_BINARY_EXPORT(__knc_vmath_atan2_8,knc_mvec_f64x8,uint64_t,8,knc_mvec_algorithm_atan2_e8)
#undef ATAN_BINARY_EXPORT
