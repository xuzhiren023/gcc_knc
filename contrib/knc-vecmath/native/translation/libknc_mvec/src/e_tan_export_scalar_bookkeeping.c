/* Two observed e-width tangent exports; independent target proof is open. */
#include "e_export_adapter.h"
#define phi_host_tan_e8 knc_mvec_algorithm_tan_e8
#define phi_host_tanf_e16 knc_mvec_algorithm_tanf_e16
#include "../../math_algorithms/tan_e/tan_e_scalar_bookkeeping.c"
#undef phi_host_tan_e8
#undef phi_host_tanf_e16
KNC_MVEC_E_EXPORT(__knc_vmath_tan_8,knc_mvec_f64x8,uint64_t,8,knc_mvec_algorithm_tan_e8)
KNC_MVEC_E_EXPORT(__knc_vmath_tanf_16,knc_mvec_f32x16,uint32_t,16,knc_mvec_algorithm_tanf_e16)
