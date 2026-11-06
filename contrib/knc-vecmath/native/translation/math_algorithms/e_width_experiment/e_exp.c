/* Fresh parameterized host e-width adaptation; old source SHA256 33be43e36792b9ecce7a47a496fadf09fa90f4443798a9b902be45a24d086255.
 * Private pointer ABI only; software mask is not a GNU masked-vector ABI. */
#define PW_LANES 8
#define PW_ALL ((1u<<PW_LANES)-1u)
/* Four-lane adaptation of Arm optimized-routines v26.01 exp.c/math_err.c.
 * Copyright (c) 2018-2025, Arm Limited. SPDX-License-Identifier: MIT
 * Commit649ccc8411e7c4862965710f25c570d854a1483f; exact data/license retained.
 * Preserve the upstream tiny-input and compensated large-result branches.
 * Host-only research, no scalar exp delegation or target _ZGV exports.
 */
#include "e_algorithms.h"
#include "math_config.h"
#include <string.h>
typedef double pw_f64v __attribute__((vector_size(PW_LANES*8)));
typedef uint64_t pw_u64v __attribute__((vector_size(PW_LANES*8)));
_Static_assert(EXP_TABLE_BITS==7 && EXP_POLY_ORDER==5 && EXP_USE_TOINT_NARROW==0 && EXP_POLY_WIDE==0,"unsupported upstream configuration");

static __attribute__((noinline)) void pw_core_exp(const uint64_t input[PW_LANES],uint64_t output[PW_LANES]) {
  uint64_t active[PW_LANES],small_input[PW_LANES]={0,0,0,0},nan_input[PW_LANES]={0};
  unsigned tiny=0,large_pos=0,large_neg=0,over=0,under=0,nan=0,posinf=0,neginf=0;
  for(unsigned i=0;i<PW_LANES;++i) {
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
  pw_f64v x;memcpy(&x,active,sizeof x);
  pw_f64v z=x*__exp_data.invln2N,kd=z+__exp_data.shift;
  pw_u64v ki;memcpy(&ki,&kd,sizeof ki);kd=kd-__exp_data.shift;
  const pw_f64v r=x+kd*__exp_data.negln2hiN+kd*__exp_data.negln2loN;
  const pw_u64v index=2*(ki&127);
  pw_u64v tailbits;for(unsigned pw_lane=0;pw_lane<PW_LANES;++pw_lane)tailbits[pw_lane]=__exp_data.tab[index[pw_lane]];
  pw_u64v sbits;for(unsigned pw_lane=0;pw_lane<PW_LANES;++pw_lane)sbits[pw_lane]=__exp_data.tab[index[pw_lane]+1];
  sbits=sbits+(ki<<45);
  pw_f64v tail;memcpy(&tail,&tailbits,sizeof tail);
  const pw_f64v r2=r*r;
  const pw_f64v tmp=tail+r+r2*(__exp_data.poly[0]+r*__exp_data.poly[1])+r2*r2*(__exp_data.poly[2]+r*__exp_data.poly[3]);
  pw_u64v normal_bits=sbits;
  for(unsigned i=0;i<PW_LANES;++i)if((large_pos|large_neg)&(1u<<i))normal_bits[i]=UINT64_C(0x3ff0000000000000);
  pw_f64v scale;memcpy(&scale,&normal_bits,sizeof scale);
  const pw_f64v normal=scale+scale*tmp;memcpy(output,&normal,sizeof normal);
  if(large_pos) {
    pw_u64v bits=(pw_u64v){0}+(0x3ff0000000000000);
    pw_f64v t=(pw_f64v){0}+(0);
    for(unsigned i=0;i<PW_LANES;++i)if(large_pos&(1u<<i)){bits[i]=sbits[i]-(UINT64_C(1009)<<52);t[i]=tmp[i];}
    pw_f64v s;memcpy(&s,&bits,sizeof s);
    const pw_f64v y=0x1p1009*(s+s*t);uint64_t words[PW_LANES];memcpy(words,&y,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i)if(large_pos&(1u<<i))output[i]=words[i];
  }
  if(large_neg) {
    pw_u64v bits=(pw_u64v){0}+(0x3ff0000000000000);
    pw_f64v t=(pw_f64v){0}+(0);
    for(unsigned i=0;i<PW_LANES;++i)if(large_neg&(1u<<i)){bits[i]=sbits[i]+(UINT64_C(1022)<<52);t[i]=tmp[i];}
    pw_f64v s;memcpy(&s,&bits,sizeof s);pw_f64v y=s+s*t;
    unsigned subnormal=0;
    for(unsigned i=0;i<PW_LANES;++i)if((large_neg&(1u<<i)) && y[i]<1.0)subnormal|=1u<<i;
    if(subnormal) {
      pw_f64v lo=s-y+s*t;
      const pw_f64v hi=1.0+y;
      lo=1.0-hi+y+lo;
      const pw_f64v rounded=(hi+lo)-1.0;
      for(unsigned i=0;i<PW_LANES;++i)if(subnormal&(1u<<i))y[i]=rounded[i];
      /* Original explicit underflow effect, not a folded constant. */
      volatile double factor=0x1p-1022;
      volatile double force_underflow=factor*factor;(void)force_underflow;
    }
    const pw_f64v result=0x1p-1022*y;uint64_t words[PW_LANES];memcpy(words,&result,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i)if(large_neg&(1u<<i))output[i]=words[i];
  }
  if(tiny) {
    /* Crucially, original tiny inputs never reach the polynomial above. */
    pw_f64v s;memcpy(&s,small_input,sizeof s);const pw_f64v result=1.0+s;
    uint64_t words[PW_LANES];memcpy(words,&result,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i)if(tiny&(1u<<i))output[i]=words[i];
  }
  if(nan) {
    pw_f64v s;memcpy(&s,nan_input,sizeof s);const pw_f64v result=1.0+s;
    uint64_t words[PW_LANES];memcpy(words,&result,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i)if(nan&(1u<<i))output[i]=words[i];
  }
  if(over || under) {
    volatile double overflow_factor=0x1p769,underflow_factor=0x1p-767;
    pw_f64v factors=(pw_f64v){0}+(1);
    for(unsigned i=0;i<PW_LANES;++i) {
      if(over&(1u<<i))factors[i]=overflow_factor;
      if(under&(1u<<i))factors[i]=underflow_factor;
    }
    const pw_f64v result=factors*factors;uint64_t words[PW_LANES];memcpy(words,&result,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i)if((over|under)&(1u<<i))output[i]=words[i];
  }
  for(unsigned i=0;i<PW_LANES;++i) {
    if(posinf&(1u<<i))output[i]=UINT64_C(0x7ff0000000000000);
    if(neginf&(1u<<i))output[i]=0;
  }
}

/* Bit snapshots support exact input/output or merge/output aliasing only.
 * Every full64B input/merge buffer is readable, even when inactive. */
static int pw_apply_exp(const uint64_t input[PW_LANES],unsigned active,
    const uint64_t merge[PW_LANES],uint64_t output[PW_LANES],int unsafe) {
  if(active&~PW_ALL)return 1;
  uint64_t saved[PW_LANES],pass[PW_LANES],neutral[PW_LANES],value[PW_LANES];
  memcpy(saved,input,64);memcpy(pass,merge,64);
  if(!active && !unsafe){memcpy(output,pass,64);return 0;}
  for(unsigned i=0;i<PW_LANES;++i)neutral[i]=(unsafe || (active&(1u<<i)))?saved[i]:0;
  pw_core_exp(neutral,value);
  for(unsigned i=0;i<PW_LANES;++i)value[i]=(active&(1u<<i))?value[i]:pass[i];
  memcpy(output,value,64);return 0;
}
int phi_host_exp_e8(const uint64_t input[PW_LANES],unsigned active,
    const uint64_t merge[PW_LANES],uint64_t output[PW_LANES]) {
  return pw_apply_exp(input,active,merge,output,0);
}
#ifdef PW_ENABLE_NEGATIVE_CONTROL
int phi_host_exp_e8_unsafe_negative(const uint64_t input[PW_LANES],unsigned active,
    const uint64_t merge[PW_LANES],uint64_t output[PW_LANES]) {
  return pw_apply_exp(input,active,merge,output,1);
}
#endif
