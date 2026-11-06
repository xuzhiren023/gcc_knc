/* Host-only research interface. No _ZGV ABI or target qualification. */
#ifndef PHI_HOST_EXPF_FULL_H
#define PHI_HOST_EXPF_FULL_H
#include <stdint.h>
/* Every binary32 encoding is admitted. Caller: nearest-even, all FP
 * exceptions masked, MXCSR FTZ=DAZ=0. errno is outside this experiment.
 * Results/flags are the union of four lane operations; no scalar expf call. */
void phi_host_expf_full4(const uint32_t input[4], uint32_t output[4]);
#endif
