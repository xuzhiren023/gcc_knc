/* Six observed e-width hyperbolic source exports. Target proof remains open. */
#include "e_export_adapter.h"
#define phi_hyperbolic_e8 knc_mvec_algorithm_hyperbolic_e8
#define phi_hyperbolic_e16 knc_mvec_algorithm_hyperbolic_e16
#include "../../math_algorithms/hyperbolic_e/hyperbolic_e.c"
#undef phi_hyperbolic_e8
#undef phi_hyperbolic_e16

/* These are the inventory's unmasked N exports. The private pointer entry
 * remains software-masked and sanitizes arbitrary inactive lane encodings. */
#define HEXPORT(NAME,VECTOR,WORD,LANES,OP,ALGORITHM) \
VECTOR NAME(VECTOR x){ \
  WORD input[LANES],output[LANES];VECTOR result; \
  _Static_assert(sizeof x==sizeof input&&sizeof result==sizeof output,"vector width"); \
  memcpy(input,&x,sizeof input); \
  if(ALGORITHM(OP,input,(1u<<(LANES))-1u,input,output))__builtin_trap(); \
  memcpy(&result,output,sizeof result);return result; \
}
HEXPORT(__knc_vmath_sinh_8,knc_mvec_f64x8,uint64_t,8,0,knc_mvec_algorithm_hyperbolic_e8)
HEXPORT(__knc_vmath_sinhf_16,knc_mvec_f32x16,uint32_t,16,0,knc_mvec_algorithm_hyperbolic_e16)
HEXPORT(__knc_vmath_cosh_8,knc_mvec_f64x8,uint64_t,8,1,knc_mvec_algorithm_hyperbolic_e8)
HEXPORT(__knc_vmath_coshf_16,knc_mvec_f32x16,uint32_t,16,1,knc_mvec_algorithm_hyperbolic_e16)
HEXPORT(__knc_vmath_tanh_8,knc_mvec_f64x8,uint64_t,8,2,knc_mvec_algorithm_hyperbolic_e8)
HEXPORT(__knc_vmath_tanhf_16,knc_mvec_f32x16,uint32_t,16,2,knc_mvec_algorithm_hyperbolic_e16)
#undef HEXPORT
