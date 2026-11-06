/* Private host research ABI; not the GNU masked vector ABI. */
#ifndef PHI_POWF_E16_H
#define PHI_POWF_E16_H
#include <stdint.h>
int phi_host_powf_e16(const uint32_t x[16], const uint32_t y[16], unsigned active,
                     const uint32_t merge[16], uint32_t output[16]);
#endif
