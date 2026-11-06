/* Unqualified e-width log export; arithmetic is the preserved sampled source. */
#include "e_export_adapter.h"
#define phi_host_log_e8 knc_mvec_algorithm_log_e8
#include "../../math_algorithms/e_width_experiment/e_log.c"
#undef phi_host_log_e8

KNC_MVEC_E_EXPORT(__knc_vmath_log_8, knc_mvec_f64x8, uint64_t, 8,
                  knc_mvec_algorithm_log_e8)
