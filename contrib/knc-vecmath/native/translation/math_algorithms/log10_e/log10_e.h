#ifndef PHI_LOG10_E_H
#define PHI_LOG10_E_H
#include <stdint.h>
int phi_host_log10f_e16(const uint32_t input[16],unsigned mask,const uint32_t merge[16],uint32_t output[16]);
int phi_host_log10_e8(const uint64_t input[8],unsigned mask,const uint64_t merge[8],uint64_t output[8]);
#endif
