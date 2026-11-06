/* Host-only research interface. No _ZGV ABI or target qualification. */
#ifndef PHI_HOST_LOGF_FULL_H
#define PHI_HOST_LOGF_FULL_H
#include <stdint.h>
/* Every binary32 encoding. Caller: nearest-even, masked exceptions,
 * MXCSR FTZ=DAZ=0. errno is excluded from this experimental contract. */
void phi_host_logf_full4(const uint32_t input[4],uint32_t output[4]);
#endif
