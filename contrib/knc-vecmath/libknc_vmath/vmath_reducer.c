/* libknc_vmath: the argument reduction shared by sin, cos and tan, as copied (ADR-0011). KNC
   evaluates scalar double in the x87 (FLT_EVAL_METHOD 2), which the copy's native_x87/libm.h
   allows for and its plain libm.h refuses; the two share a guard, so the first one included
   stands. */
#include "vmath_reducer.h"
#include "../native/translation/math_algorithms/cos_sin_e/native_x87/libm.h"
#include "../native/translation/math_algorithms/cos_sin_e/reducer.c"
