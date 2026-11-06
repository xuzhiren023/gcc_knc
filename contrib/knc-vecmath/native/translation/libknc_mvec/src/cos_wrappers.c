/* Only the observed b2-DP cosine signature is added. */
#include "knc_mvec_abi.h"
knc_mvec_f64x2 __knc_vmath_cos_2(knc_mvec_f64x2 x) {
  knc_mvec_f64x8 wide={0};
  for(unsigned i=0;i<2;++i)wide[i]=x[i];
  const knc_mvec_f64x8 value=__knc_vmath_cos_8(wide);
  knc_mvec_f64x2 result;for(unsigned i=0;i<2;++i)result[i]=value[i];return result;
}
