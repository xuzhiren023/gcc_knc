/* Additive volatile scalar-event SP16 log candidate; no target qualification. */
#include "e_export_adapter.h"
#define phi_host_logf_register_e16 knc_mvec_algorithm_logf_register_e16
#include "../../math_algorithms/e_width_experiment/e_logf_register_scalar_events_volatile.c"
#undef phi_host_logf_register_e16
KNC_MVEC_E_EXPORT(__knc_vmath_logf_16, knc_mvec_f32x16, uint32_t, 16,
                  knc_mvec_algorithm_logf_register_e16)
