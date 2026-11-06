/* Binary DP b/d wrappers; target register calling convention remains open. */
#include "knc_mvec_abi.h"
#define POW_NARROW(NAME,TYPE,LANES) \
TYPE NAME(TYPE x,TYPE y) { \
  knc_mvec_f64x8 wx=(knc_mvec_f64x8){0}+1,wy=(knc_mvec_f64x8){0}; \
  for(unsigned i=0;i<(LANES);++i){wx[i]=x[i];wy[i]=y[i];} \
  const knc_mvec_f64x8 wide=__knc_vmath_pow_8(wx,wy); \
  TYPE result;for(unsigned i=0;i<(LANES);++i)result[i]=wide[i];return result; \
}
POW_NARROW(__knc_vmath_pow_2,knc_mvec_f64x2,2)
POW_NARROW(__knc_vmath_pow_4,knc_mvec_f64x4,4)
#undef POW_NARROW
