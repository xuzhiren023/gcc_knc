/* Four-lane adaptation of Arm optimized-routines v26.01 exp.c/math_err.c.
 * Copyright (c) 2018-2025, Arm Limited. SPDX-License-Identifier: MIT
 * Commit649ccc8411e7c4862965710f25c570d854a1483f; exact data/license retained.
 * Preserve the upstream tiny-input and compensated large-result branches.
 * Host-only research, no scalar exp delegation or target _ZGV exports.
 */
#include "exp_full.h"
#include "../../../upstream/arm-optimized-routines-v26.01-dp/math/math_config.h"
#include <string.h>
typedef double f64x4 __attribute__((vector_size(32)));
typedef uint64_t u64x4 __attribute__((vector_size(32)));
_Static_assert(EXP_TABLE_BITS==7 && EXP_POLY_ORDER==5 && EXP_USE_TOINT_NARROW==0 && EXP_POLY_WIDE==0,"unsupported upstream configuration");

void phi_host_exp_full4(const uint64_t input[4],uint64_t output[4]) {
  uint64_t active[4],small_input[4]={0,0,0,0},nan_input[4]={0,0,0,0};
  unsigned tiny=0,large_pos=0,large_neg=0,over=0,under=0,nan=0,posinf=0,neginf=0;
  for(unsigned i=0;i<4;++i) {
    const uint64_t bits=input[i],mag=bits&UINT64_C(0x7fffffffffffffff);active[i]=bits;
    if(mag>=UINT64_C(0x7ff0000000000000)) {
      active[i]=0;
      if(mag>UINT64_C(0x7ff0000000000000)) {nan|=1u<<i;nan_input[i]=bits;}
      else if(bits>>63)neginf|=1u<<i;else posinf|=1u<<i;
    } else if(mag<UINT64_C(0x3c90000000000000)) {
      tiny|=1u<<i;small_input[i]=bits;active[i]=0;
    } else if(mag>=UINT64_C(0x4090000000000000)) {
      active[i]=0;if(bits>>63)under|=1u<<i;else over|=1u<<i;
    } else if(mag>=UINT64_C(0x4080000000000000)) {
      if(bits>>63)large_neg|=1u<<i;else large_pos|=1u<<i;
    }
  }
  f64x4 x;memcpy(&x,active,sizeof x);
  f64x4 z=x*__exp_data.invln2N,kd=z+__exp_data.shift;
  u64x4 ki;memcpy(&ki,&kd,sizeof ki);kd=kd-__exp_data.shift;
  const f64x4 r=x+kd*__exp_data.negln2hiN+kd*__exp_data.negln2loN;
  const u64x4 index=2*(ki&127);
  const u64x4 tailbits={__exp_data.tab[index[0]],__exp_data.tab[index[1]],__exp_data.tab[index[2]],__exp_data.tab[index[3]]};
  u64x4 sbits={__exp_data.tab[index[0]+1],__exp_data.tab[index[1]+1],__exp_data.tab[index[2]+1],__exp_data.tab[index[3]+1]};
  sbits=sbits+(ki<<45);
  f64x4 tail;memcpy(&tail,&tailbits,sizeof tail);
  const f64x4 r2=r*r;
  const f64x4 tmp=tail+r+r2*(__exp_data.poly[0]+r*__exp_data.poly[1])+r2*r2*(__exp_data.poly[2]+r*__exp_data.poly[3]);
  u64x4 normal_bits=sbits;
  for(unsigned i=0;i<4;++i)if((large_pos|large_neg)&(1u<<i))normal_bits[i]=UINT64_C(0x3ff0000000000000);
  f64x4 scale;memcpy(&scale,&normal_bits,sizeof scale);
  const f64x4 normal=scale+scale*tmp;memcpy(output,&normal,sizeof normal);
  if(large_pos) {
    u64x4 bits={0x3ff0000000000000,0x3ff0000000000000,0x3ff0000000000000,0x3ff0000000000000};
    f64x4 t={0,0,0,0};
    for(unsigned i=0;i<4;++i)if(large_pos&(1u<<i)){bits[i]=sbits[i]-(UINT64_C(1009)<<52);t[i]=tmp[i];}
    f64x4 s;memcpy(&s,&bits,sizeof s);
    const f64x4 y=0x1p1009*(s+s*t);uint64_t words[4];memcpy(words,&y,sizeof words);
    for(unsigned i=0;i<4;++i)if(large_pos&(1u<<i))output[i]=words[i];
  }
  if(large_neg) {
    u64x4 bits={0x3ff0000000000000,0x3ff0000000000000,0x3ff0000000000000,0x3ff0000000000000};
    f64x4 t={0,0,0,0};
    for(unsigned i=0;i<4;++i)if(large_neg&(1u<<i)){bits[i]=sbits[i]+(UINT64_C(1022)<<52);t[i]=tmp[i];}
    f64x4 s;memcpy(&s,&bits,sizeof s);f64x4 y=s+s*t;
    unsigned subnormal=0;
    for(unsigned i=0;i<4;++i)if((large_neg&(1u<<i)) && y[i]<1.0)subnormal|=1u<<i;
    if(subnormal) {
      f64x4 lo=s-y+s*t;
      const f64x4 hi=1.0+y;
      lo=1.0-hi+y+lo;
      const f64x4 rounded=(hi+lo)-1.0;
      for(unsigned i=0;i<4;++i)if(subnormal&(1u<<i))y[i]=rounded[i];
      /* Original explicit underflow effect, not a folded constant. */
      volatile double factor=0x1p-1022;
      volatile double force_underflow=factor*factor;(void)force_underflow;
    }
    const f64x4 result=0x1p-1022*y;uint64_t words[4];memcpy(words,&result,sizeof words);
    for(unsigned i=0;i<4;++i)if(large_neg&(1u<<i))output[i]=words[i];
  }
  if(tiny) {
    /* Crucially, original tiny inputs never reach the polynomial above. */
    f64x4 s;memcpy(&s,small_input,sizeof s);const f64x4 result=1.0+s;
    uint64_t words[4];memcpy(words,&result,sizeof words);
    for(unsigned i=0;i<4;++i)if(tiny&(1u<<i))output[i]=words[i];
  }
  if(nan) {
    f64x4 s;memcpy(&s,nan_input,sizeof s);const f64x4 result=1.0+s;
    uint64_t words[4];memcpy(words,&result,sizeof words);
    for(unsigned i=0;i<4;++i)if(nan&(1u<<i))output[i]=words[i];
  }
  if(over || under) {
    volatile double overflow_factor=0x1p769,underflow_factor=0x1p-767;
    f64x4 factors={1,1,1,1};
    for(unsigned i=0;i<4;++i) {
      if(over&(1u<<i))factors[i]=overflow_factor;
      if(under&(1u<<i))factors[i]=underflow_factor;
    }
    const f64x4 result=factors*factors;uint64_t words[4];memcpy(words,&result,sizeof words);
    for(unsigned i=0;i<4;++i)if((over|under)&(1u<<i))output[i]=words[i];
  }
  for(unsigned i=0;i<4;++i) {
    if(posinf&(1u<<i))output[i]=UINT64_C(0x7ff0000000000000);
    if(neginf&(1u<<i))output[i]=0;
  }
}
