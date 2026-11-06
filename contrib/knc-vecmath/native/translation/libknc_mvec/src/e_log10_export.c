/* Source-only compensated DP log10 export. No target ABI/numeric claim. */
#include "e_export_adapter.h"
#define phi_host_log10_e8 knc_mvec_algorithm_log10_e8
#include "../../math_algorithms/log10_e/e_log10.c"
#undef phi_host_log10_e8
KNC_MVEC_E_EXPORT(__knc_vmath_log10_8,knc_mvec_f64x8,uint64_t,8,knc_mvec_algorithm_log10_e8)
