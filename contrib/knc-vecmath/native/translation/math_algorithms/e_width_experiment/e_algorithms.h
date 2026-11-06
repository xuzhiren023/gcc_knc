/* Private Windows host pointer interfaces. No GNU vector ABI/export. */
#ifndef PHI_HOST_E_ALGORITHMS_H
#define PHI_HOST_E_ALGORITHMS_H
#include <stdint.h>
#define PW_DECLARE(OP,TYPE,LANES) \
int phi_host_##OP##_e##LANES(const TYPE input[LANES],unsigned active,const TYPE merge[LANES],TYPE output[LANES]);
PW_DECLARE(expf,uint32_t,16)
PW_DECLARE(logf,uint32_t,16)
PW_DECLARE(exp,uint64_t,8)
PW_DECLARE(log,uint64_t,8)
#ifdef PW_ENABLE_NEGATIVE_CONTROL
#define PW_NEGATIVE(OP,TYPE,LANES) \
int phi_host_##OP##_e##LANES##_unsafe_negative(const TYPE input[LANES],unsigned active,const TYPE merge[LANES],TYPE output[LANES]);
PW_NEGATIVE(expf,uint32_t,16)
PW_NEGATIVE(logf,uint32_t,16)
PW_NEGATIVE(exp,uint64_t,8)
PW_NEGATIVE(log,uint64_t,8)
#undef PW_NEGATIVE
#endif
#undef PW_DECLARE
#endif
