/* Additive RN-only DP log10 algorithm; no inherited target qualification. */
#include "e_export_adapter.h"
#define phi_host_log10_i64_rn_ratio_e8 knc_mvec_algorithm_log10_i64_rn_ratio_e8
#include "../../math_algorithms/log10_e/e_log10_i64_rn_ratio.c"
#undef phi_host_log10_i64_rn_ratio_e8
KNC_MVEC_E_EXPORT(__knc_vmath_log10_8,knc_mvec_f64x8,uint64_t,8,knc_mvec_algorithm_log10_i64_rn_ratio_e8)
