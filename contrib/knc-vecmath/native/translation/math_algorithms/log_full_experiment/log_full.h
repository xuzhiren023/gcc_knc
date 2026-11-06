/* Windows host research only; no target vector ABI. */
#ifndef PHI_HOST_LOG_FULL_H
#define PHI_HOST_LOG_FULL_H
#include <stdint.h>
/* All binary64 inputs, nearest/masked/FTZDAZoff caller state only. */
void phi_host_log_full4(const uint64_t input[4],uint64_t output[4]);
#endif
