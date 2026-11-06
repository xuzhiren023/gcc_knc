/* Experimental host arithmetic only. No vector ABI exports or KNC qualification. */
#ifndef PHI_BOUNDED_F32_H
#define PHI_BOUNDED_F32_H
#include <stdint.h>
/* All four lanes must be in the stated domain. Failure leaves out unchanged.
 * Caller must establish nearest-even, MXCSR FTZ=DAZ=0. The host harness checks
 * this state. These interfaces are not production mathematical functions. */
int phi_expf_bounded4(const uint32_t in[4], uint32_t out[4]); /* [-80,80] */
#endif
