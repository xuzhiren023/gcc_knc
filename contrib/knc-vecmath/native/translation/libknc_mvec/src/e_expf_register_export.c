/* Unqualified e-width expf export; arithmetic is the preserved sampled source. */
#include "e_export_adapter.h"
#define phi_host_expf_e16 knc_mvec_algorithm_expf_e16
#include "../../math_algorithms/e_width_experiment/e_expf_register.c"
#undef phi_host_expf_e16

KNC_MVEC_E_EXPORT(__knc_vmath_expf_16, knc_mvec_f32x16, uint32_t, 16,
                  knc_mvec_algorithm_expf_e16)
