/* Exact musl v1.2.5 reducer/helper bodies, symbol-renamed only.
 * Their upstream Sun and musl notices are retained in the included files and
 * upstream/COPYRIGHT. No scalar trigonometric function is linked or called. */
#include "libm.h"
#ifdef __FAST_MATH__
#error "The Payne-Hanek reducer requires strict floating-point arithmetic"
#endif
#define scalbn phi_trig_scalbn
#define floor phi_trig_floor
#define __rem_pio2 phi_trig_rem_pio2
#define __rem_pio2_large phi_trig_rem_pio2_large
#include "upstream/scalbn.c"
#define toint phi_floor_toint
#include "upstream/floor.c"
#undef toint
#undef EPS
#include "upstream/__rem_pio2_large.c"
#include "upstream/__rem_pio2.c"
