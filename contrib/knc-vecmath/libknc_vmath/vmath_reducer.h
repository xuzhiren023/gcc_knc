/* libknc_vmath: the copied argument reduction of sin, cos and tan (musl's __rem_pio2 and its
   helpers, math_algorithms/cos_sin_e/reducer.c) under implementation-namespace names. */
#ifndef KNC_VMATH_REDUCER_H
#define KNC_VMATH_REDUCER_H
#define phi_trig_rem_pio2 __knc_vmath_rem_pio2
#define phi_trig_rem_pio2_large __knc_vmath_rem_pio2_large
#define phi_trig_scalbn __knc_vmath_scalbn
#define phi_trig_floor __knc_vmath_floor
#endif
