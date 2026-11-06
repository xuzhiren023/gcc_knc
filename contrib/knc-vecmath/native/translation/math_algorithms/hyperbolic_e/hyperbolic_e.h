#ifndef PW_HYPERBOLIC_E_H
#define PW_HYPERBOLIC_E_H
#include <stdint.h>
int phi_hyperbolic_e8(unsigned operation,const uint64_t input[8],unsigned active,const uint64_t merge[8],uint64_t output[8]);
int phi_hyperbolic_e16(unsigned operation,const uint32_t input[16],unsigned active,const uint32_t merge[16],uint32_t output[16]);
#endif
