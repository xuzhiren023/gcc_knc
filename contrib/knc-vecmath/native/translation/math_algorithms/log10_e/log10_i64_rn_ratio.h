#ifndef PHI_LOG10_I64_RN_RATIO_H
#define PHI_LOG10_I64_RN_RATIO_H
#include <stdint.h>
/* RN-only numerical algorithm; not a general DP division instruction rule. */
int phi_host_log10_i64_rn_ratio_e8(const uint64_t input[8],unsigned mask,const uint64_t merge[8],uint64_t output[8]);
#endif
