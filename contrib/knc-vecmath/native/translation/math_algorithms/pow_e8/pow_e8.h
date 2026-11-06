#ifndef PHI_POW_E8_H
#define PHI_POW_E8_H
#include <stdint.h>
int phi_host_pow_e8(const uint64_t x[8],const uint64_t y[8],unsigned active,
                    const uint64_t merge[8],uint64_t output[8]);
#endif
