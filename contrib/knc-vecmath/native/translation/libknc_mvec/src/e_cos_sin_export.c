/* Four observed e-width trig exports; host source wiring only.
 * Complete-domain Sun/musl reducer and numerical source evidence remain in
 * math_algorithms/cos_sin_e. This TU includes the vector kernel exactly once. */
#include "e_export_adapter.h"
#define phi_host_sin_e8 knc_mvec_algorithm_sin_e8
#define phi_host_cos_e8 knc_mvec_algorithm_cos_e8
#define phi_host_sinf_e16 knc_mvec_algorithm_sinf_e16
#define phi_host_cosf_e16 knc_mvec_algorithm_cosf_e16
#include "../../math_algorithms/cos_sin_e/cos_sin_e.c"
#undef phi_host_sin_e8
#undef phi_host_cos_e8
#undef phi_host_sinf_e16
#undef phi_host_cosf_e16
KNC_MVEC_E_EXPORT(__knc_vmath_sin_8,knc_mvec_f64x8,uint64_t,8,knc_mvec_algorithm_sin_e8)
KNC_MVEC_E_EXPORT(__knc_vmath_cos_8,knc_mvec_f64x8,uint64_t,8,knc_mvec_algorithm_cos_e8)
KNC_MVEC_E_EXPORT(__knc_vmath_sinf_16,knc_mvec_f32x16,uint32_t,16,knc_mvec_algorithm_sinf_e16)
KNC_MVEC_E_EXPORT(__knc_vmath_cosf_16,knc_mvec_f32x16,uint32_t,16,knc_mvec_algorithm_cosf_e16)
