/* Alternative source-only DP8 exp candidate; no target qualification. */
#include "e_export_adapter.h"
#define phi_host_exp_register_e8 knc_mvec_algorithm_exp_register_e8
#include "../../math_algorithms/e_width_experiment/e_exp_register.c"
#undef phi_host_exp_register_e8

KNC_MVEC_E_EXPORT(__knc_vmath_exp_8, knc_mvec_f64x8, uint64_t, 8,
                  knc_mvec_algorithm_exp_register_e8)
