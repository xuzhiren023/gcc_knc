/* libknc_vmath: logf on 16 lanes, the copied pointer-form core (ADR-0011, ADR-0014 point 3). */
#include "knc_vmath.h"
#define phi_host_logf_e16 __knc_vmath_core_logf_16
#include "../native/translation/math_algorithms/e_width_experiment/e_logf.c"
