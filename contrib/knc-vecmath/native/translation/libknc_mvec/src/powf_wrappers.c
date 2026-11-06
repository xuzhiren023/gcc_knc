/* Binary b/d source wrappers, pending target vector-ABI/mask qualification. */
#include "knc_mvec_abi.h"
#define POWF_NARROW(NAME,TYPE,LANES) \
TYPE NAME(TYPE x,TYPE y) { \
  knc_mvec_f32x16 wx=(knc_mvec_f32x16){0}+1,wy=(knc_mvec_f32x16){0}; \
  for(unsigned i=0;i<(LANES);++i){wx[i]=x[i];wy[i]=y[i];} \
  const knc_mvec_f32x16 wide=__knc_vmath_powf_16(wx,wy); \
  TYPE result;for(unsigned i=0;i<(LANES);++i)result[i]=wide[i]; \
  return result; \
}
POWF_NARROW(__knc_vmath_powf_4,knc_mvec_f32x4,4)
POWF_NARROW(__knc_vmath_powf_8,knc_mvec_f32x8,8)
#undef POWF_NARROW
