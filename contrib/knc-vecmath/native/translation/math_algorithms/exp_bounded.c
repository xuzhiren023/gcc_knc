/* Four-lane adaptation of Arm optimized-routines v26.01 math/exp.c.
 * Copyright (c) 2018-2025, Arm Limited.
 * SPDX-License-Identifier: MIT
 * Commit 649ccc8411e7c4862965710f25c570d854a1483f; complete license/originals
 * at native/upstream/arm-optimized-routines-v26.01-dp/. Official unmodified
 * exp_data.c supplies all table entries and coefficients. Bounded [-500,500]
 * avoids the source's large-result specialcase. Tiny lanes use vector 1+x.
 */
#include "bounded_f64.h"
#include "../../upstream/arm-optimized-routines-v26.01-dp/math/math_config.h"
#include <string.h>
typedef double f64x4 __attribute__((vector_size(32)));
typedef uint64_t u64x4 __attribute__((vector_size(32)));
_Static_assert(EXP_TABLE_BITS==7 && EXP_POLY_ORDER==5 && EXP_USE_TOINT_NARROW==0 && EXP_POLY_WIDE==0,"unsupported upstream configuration");

int phi_exp_bounded4(const uint64_t in[4],uint64_t out[4]) {
  uint64_t sanitized[4];u64x4 tiny={0,0,0,0};
  for(unsigned i=0;i<4;++i) {
    uint64_t magnitude=in[i]&UINT64_C(0x7fffffffffffffff);
    if(magnitude>UINT64_C(0x407f400000000000))return 1;
    tiny[i]=magnitude<UINT64_C(0x3c90000000000000)?UINT64_MAX:0;
    sanitized[i]=tiny[i]?0:in[i];
  }
  f64x4 x,original;memcpy(&x,sanitized,sizeof x);memcpy(&original,in,sizeof original);
  f64x4 z=x*__exp_data.invln2N;
  f64x4 kd=z+__exp_data.shift;
  u64x4 ki;memcpy(&ki,&kd,sizeof ki);kd=kd-__exp_data.shift;
  const f64x4 r=x+kd*__exp_data.negln2hiN+kd*__exp_data.negln2loN;
  const u64x4 index=2*(ki&127);
  const u64x4 tailbits={__exp_data.tab[index[0]],__exp_data.tab[index[1]],__exp_data.tab[index[2]],__exp_data.tab[index[3]]};
  u64x4 sbits={__exp_data.tab[index[0]+1],__exp_data.tab[index[1]+1],__exp_data.tab[index[2]+1],__exp_data.tab[index[3]+1]};
  sbits=sbits+(ki<<45);
  f64x4 tail,scale;memcpy(&tail,&tailbits,sizeof tail);memcpy(&scale,&sbits,sizeof scale);
  const f64x4 r2=r*r;
  const f64x4 tmp=tail+r+r2*(__exp_data.poly[0]+r*__exp_data.poly[1])+r2*r2*(__exp_data.poly[2]+r*__exp_data.poly[3]);
  const f64x4 result=scale+scale*tmp;
  const f64x4 small=1+original;
  u64x4 normalbits,smallbits;memcpy(&normalbits,&result,sizeof result);memcpy(&smallbits,&small,sizeof small);
  normalbits=(tiny&smallbits)|(~tiny&normalbits);
  memcpy(out,&normalbits,sizeof normalbits);return 0;
}
