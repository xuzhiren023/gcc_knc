/* Additive volatile scalar-event DP8 log candidate; no target qualification. */
#include "e_export_adapter.h"
#define phi_host_log_register_e8 knc_mvec_algorithm_log_register_e8
#include "../../math_algorithms/e_width_experiment/e_log_register_i64_scalar_events_volatile.c"
#undef phi_host_log_register_e8

KNC_MVEC_E_EXPORT(__knc_vmath_log_8, knc_mvec_f64x8, uint64_t, 8,
                  knc_mvec_algorithm_log_register_e8)
