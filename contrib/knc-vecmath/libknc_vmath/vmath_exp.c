/* libknc_vmath: exp on 8 lanes, the copied pointer-form core (ADR-0011, ADR-0014 point 3). */
#include "knc_vmath.h"
#define phi_host_exp_e8 __knc_vmath_core_exp_8
#include "../native/translation/math_algorithms/e_width_experiment/e_exp.c"
