/* Only the observed b4-SP and b2-DP log10 signatures are defined. */
#include "knc_mvec_abi.h"
knc_mvec_f32x4 __knc_vmath_log10f_4(knc_mvec_f32x4 x) {
  knc_mvec_f32x16 wide=(knc_mvec_f32x16){0}+1;
  for(unsigned i=0;i<4;++i)wide[i]=x[i];
  const knc_mvec_f32x16 value=__knc_vmath_log10f_16(wide);
  knc_mvec_f32x4 result;for(unsigned i=0;i<4;++i)result[i]=value[i];return result;
}
knc_mvec_f64x2 __knc_vmath_log10_2(knc_mvec_f64x2 x) {
  knc_mvec_f64x8 wide=(knc_mvec_f64x8){0}+1;
  for(unsigned i=0;i<2;++i)wide[i]=x[i];
  const knc_mvec_f64x8 value=__knc_vmath_log10_8(wide);
  knc_mvec_f64x2 result;for(unsigned i=0;i<2;++i)result[i]=value[i];return result;
}
