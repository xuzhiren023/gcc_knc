/* Unqualified e-width logf export; arithmetic is the preserved sampled source. */
#include "e_export_adapter.h"
#define phi_host_logf_e16 knc_mvec_algorithm_logf_e16
#include "../../math_algorithms/e_width_experiment/e_logf.c"
#undef phi_host_logf_e16

KNC_MVEC_E_EXPORT(__knc_vmath_logf_16, knc_mvec_f32x16, uint32_t, 16,
                  knc_mvec_algorithm_logf_e16)
