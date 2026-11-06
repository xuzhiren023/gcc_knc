/* Experimental host arithmetic only; no target ABI or exception contract. */
#ifndef PHI_LOGF_BOUNDED_H
#define PHI_LOGF_BOUNDED_H
#include <stdint.h>
/* Positive normal binary32 only; failure leaves out unchanged.
 * Caller establishes nearest-even, MXCSR FTZ=DAZ=0. */
int phi_logf_bounded4(const uint32_t in[4], uint32_t out[4]);
#endif
