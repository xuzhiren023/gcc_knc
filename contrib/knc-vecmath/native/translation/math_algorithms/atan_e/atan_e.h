#ifndef PHI_ATAN_E_H
#define PHI_ATAN_E_H
#include <stdint.h>
int phi_host_atanf_e16(const uint32_t input[16],unsigned mask,const uint32_t merge[16],uint32_t output[16]);
int phi_host_atan2f_e16(const uint32_t y[16],const uint32_t x[16],unsigned mask,const uint32_t merge[16],uint32_t output[16]);
int phi_host_atan2_e8(const uint64_t y[8],const uint64_t x[8],unsigned mask,const uint64_t merge[8],uint64_t output[8]);
#endif
