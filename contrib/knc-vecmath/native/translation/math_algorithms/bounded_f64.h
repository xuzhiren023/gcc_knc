/* Experimental Windows arithmetic only; no KNC ABI exports. */
#ifndef PHI_BOUNDED_F64_H
#define PHI_BOUNDED_F64_H
#include <stdint.h>
/* Caller establishes nearest-even/MXCSR FTZ=DAZ=0. All lanes checked before
 * any output write. Failure is domain rejection, not special-value handling. */
int phi_exp_bounded4(const uint64_t in[4],uint64_t out[4]); /* finite [-500,500] */
int phi_log_bounded4(const uint64_t in[4],uint64_t out[4]); /* positive normals */
#endif
