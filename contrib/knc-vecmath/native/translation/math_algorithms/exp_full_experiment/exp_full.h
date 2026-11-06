/* Windows host research only. No _ZGV exports or target qualification. */
#ifndef PHI_HOST_EXP_FULL_H
#define PHI_HOST_EXP_FULL_H
#include <stdint.h>
/* All binary64 inputs. Caller: nearest-even, all exceptions masked,
 * FTZ=DAZ=0. errno/directed rounding remain outside the contract. */
void phi_host_exp_full4(const uint64_t input[4],uint64_t output[4]);
#endif
