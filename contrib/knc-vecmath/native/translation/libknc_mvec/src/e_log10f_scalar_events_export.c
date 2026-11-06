/* G5 v2 candidate; production archive is unchanged. */
#include "e_export_adapter.h"
#define phi_host_log10f_e16 knc_mvec_algorithm_log10f_e16
#include "../../math_algorithms/log10_e/e_log10f_scalar_events.c"
#undef phi_host_log10f_e16
KNC_MVEC_E_EXPORT(__knc_vmath_log10f_16,knc_mvec_f32x16,uint32_t,16,knc_mvec_algorithm_log10f_e16)
