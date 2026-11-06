/* New gather-free logf candidate; four register word-half tables.
 * Original FP expressions and exceptional paths unchanged; target unqualified. */
/* Fresh parameterized host e-width adaptation; old source SHA256 a3f11b13b4ecbcc943f9859dce3b210e616f1e611f5add3d20acd1408a385bf3.
 * Private pointer ABI only; software mask is not a GNU masked-vector ABI. */
#define PW_LANES 16
#define PW_ALL ((1u<<PW_LANES)-1u)
/* Adapted from Arm optimized-routines v26.01 logf.c, logf_data.c and
 * math_errf.c at commit 649ccc8411e7c4862965710f25c570d854a1483f.
 * Copyright (c) 2017-2025, Arm Limited. SPDX-License-Identifier: MIT
 * Exact upstream source/license retained under native/upstream/.
 * Adaptation: four-lane GCC vectors, sanitized exceptional lanes, original
 * exact subnormal normalization and N16 degree-four polynomial/data.
 * Host research only; no scalar logf delegation or _ZGV export.
 */
#include "e_algorithms.h"
#include <string.h>
typedef float pw_f32v __attribute__((vector_size(PW_LANES*4)));
typedef double pw_f64v __attribute__((vector_size(PW_LANES*8)));
typedef uint32_t pw_u32v __attribute__((vector_size(PW_LANES*4)));
typedef int32_t pw_i32v __attribute__((vector_size(PW_LANES*4)));
static const pw_u32v pw_logf_invc_lo __attribute__((aligned(64))) = {
  UINT32_C(0x79f8f3be), UINT32_C(0x4aaf883d), UINT32_C(0xf0f010b0), UINT32_C(0xb0b80385), UINT32_C(0x0c8864a5), UINT32_C(0x7b0b8ea0), UINT32_C(0x4a1a343f), UINT32_C(0xf08ae5ba), UINT32_C(0x419900a7), UINT32_C(0x00000000), UINT32_C(0xfd9a47ac), UINT32_C(0x1f026aa0), UINT32_C(0x576afce6), UINT32_C(0x63a1aa2d), UINT32_C(0x037841ed), UINT32_C(0xf5534862)
};
static const pw_u32v pw_logf_invc_hi __attribute__((aligned(64))) = {
  UINT32_C(0x3ff661ec), UINT32_C(0x3ff571ed), UINT32_C(0x3ff49539), UINT32_C(0x3ff3c995), UINT32_C(0x3ff30d19), UINT32_C(0x3ff25e22), UINT32_C(0x3ff1bb4a), UINT32_C(0x3ff12358), UINT32_C(0x3ff0953f), UINT32_C(0x3ff00000), UINT32_C(0x3fee608c), UINT32_C(0x3feca4b3), UINT32_C(0x3feb2036), UINT32_C(0x3fe9c2d1), UINT32_C(0x3fe886e6), UINT32_C(0x3fe767dc)
};
static const pw_u32v pw_logf_logc_lo __attribute__((aligned(64))) = {
  UINT32_C(0x808caade), UINT32_C(0xa7c06ddb), UINT32_C(0x7f513a67), UINT32_C(0xa68224e9), UINT32_C(0x0ac07758), UINT32_C(0xc79c8100), UINT32_C(0xce8c0e5e), UINT32_C(0x5a611ccc), UINT32_C(0x38e10c1e), UINT32_C(0x00000000), UINT32_C(0x5df25984), UINT32_C(0xaa362eb4), UINT32_C(0x7720db08), UINT32_C(0x0d224770), UINT32_C(0xc8a07ee1), UINT32_C(0x57b6ee09)
};
static const pw_u32v pw_logf_logc_hi __attribute__((aligned(64))) = {
  UINT32_C(0xbfd57bf7), UINT32_C(0xbfd2bef0), UINT32_C(0xbfd01eae), UINT32_C(0xbfcb31d8), UINT32_C(0xbfc6574f), UINT32_C(0xbfc1aa2b), UINT32_C(0xbfba4e76), UINT32_C(0xbfb1973c), UINT32_C(0xbfa252f4), UINT32_C(0x00000000), UINT32_C(0x3faaa5aa), UINT32_C(0x3fbc5e53), UINT32_C(0x3fc526e5), UINT32_C(0x3fcbc286), UINT32_C(0x3fd1058b), UINT32_C(0x3fd40430)
};

typedef uint64_t pw_u64v __attribute__((vector_size(PW_LANES*8)));
static __attribute__((always_inline)) inline pw_f64v
pw_logf_register_lookup(pw_u32v index,pw_u32v low,pw_u32v high) {
  const pw_u32v lo=__builtin_shuffle(low,index),hi=__builtin_shuffle(high,index);
  const pw_u64v words=__builtin_convertvector(lo,pw_u64v)
    | (__builtin_convertvector(hi,pw_u64v)<<32);
  pw_f64v value;memcpy(&value,&words,sizeof value);return value;
}


static __attribute__((noinline)) void pw_core_logf(const uint32_t input[PW_LANES],uint32_t output[PW_LANES]) {
  uint32_t active[PW_LANES],norm_input[PW_LANES]={0};for(unsigned pw_lane=0;pw_lane<PW_LANES;++pw_lane)norm_input[pw_lane]=0x3f800000;
  uint32_t invalid_input[PW_LANES]={0};
  unsigned zero_mask=0,invalid_mask=0,subnormal_mask=0,infinity_mask=0,one_mask=0;
  for(unsigned i=0;i<PW_LANES;++i) {
    const uint32_t bits=input[i],magnitude=bits&UINT32_C(0x7fffffff);
    active[i]=bits;
    if(magnitude==0) {zero_mask|=1u<<i;active[i]=UINT32_C(0x3f800000);}
    else if(magnitude>UINT32_C(0x7f800000) || (bits>>31)) {
      invalid_mask|=1u<<i;invalid_input[i]=bits;active[i]=UINT32_C(0x3f800000);
    } else if(bits==UINT32_C(0x7f800000)) {
      infinity_mask|=1u<<i;active[i]=UINT32_C(0x3f800000);
    } else if(bits<UINT32_C(0x00800000)) {
      subnormal_mask|=1u<<i;norm_input[i]=bits;
    } else if(bits==UINT32_C(0x3f800000)) one_mask|=1u<<i;
  }
  if(subnormal_mask) {
    pw_f32v n;memcpy(&n,norm_input,sizeof n);
    const pw_f32v scaled=n*0x1p23f;uint32_t words[PW_LANES];memcpy(words,&scaled,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i) if(subnormal_mask&(1u<<i))
      active[i]=words[i]-(23u<<23); /* Original unsigned exponent adjustment. */
  }
  pw_u32v ix;memcpy(&ix,active,sizeof ix);
  const pw_u32v tmp=ix-UINT32_C(0x3f330000),index=(tmp>>19)&15;
  pw_i32v signed_tmp;memcpy(&signed_tmp,&tmp,sizeof tmp);
  const pw_i32v k=signed_tmp>>23;
  const pw_u32v iz=ix-(tmp&UINT32_C(0xff800000));
  pw_f32v zf;memcpy(&zf,&iz,sizeof zf);
  const pw_f64v z=__builtin_convertvector(zf,pw_f64v);
  const pw_f64v invc=pw_logf_register_lookup(index,pw_logf_invc_lo,pw_logf_invc_hi);
  const pw_f64v logc=pw_logf_register_lookup(index,pw_logf_logc_lo,pw_logf_logc_hi);
  const pw_f64v r=z*invc-1;
  const pw_f64v y0=logc+__builtin_convertvector(k,pw_f64v)*0x1.62e42fefa39efp-1;
  const pw_f64v r2=r*r;
  pw_f64v y=0x1.5575b0be00b6ap-2*r+(-0x1.ffffef20a4123p-2);
  y=(-0x1.00ea348b88334p-2)*r2+y;
  y=y*r2+(y0+r);
  const pw_f32v result=__builtin_convertvector(y,pw_f32v);
  memcpy(output,&result,sizeof result);
  if(invalid_mask) {
    /* Original math_errf.c (x-x)/(x-x). Quiet NaNs propagate without invalid;
     * sNaNs and negative-domain inputs raise invalid. The inactive lanes
     * use0/1 so a quiet-NaN-only vector cannot spuriously raise invalid. */
    pw_f32v v;memcpy(&v,invalid_input,sizeof v);
    const pw_f32v difference=v-v;
    uint32_t denom_bits[PW_LANES];memcpy(denom_bits,&difference,sizeof denom_bits);
    for(unsigned i=0;i<PW_LANES;++i) if(!(invalid_mask&(1u<<i)))denom_bits[i]=UINT32_C(0x3f800000);
    pw_f32v denominator;memcpy(&denominator,denom_bits,sizeof denominator);
    const pw_f32v q=difference/denominator;uint32_t words[PW_LANES];memcpy(words,&q,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i) if(invalid_mask&(1u<<i))output[i]=words[i];
  }
  if(zero_mask) {
    /* Original math_errf.c barrier(-1.0f)/0.0f. A volatile numerator keeps
     * actual divide-by-zero arithmetic; inactive lanes use exact1/1. */
    volatile float negative_one=-1.0f;
    pw_f32v numerators=(pw_f32v){0}+1,denominators=(pw_f32v){0}+1;
    for(unsigned i=0;i<PW_LANES;++i) if(zero_mask&(1u<<i)) {numerators[i]=negative_one;denominators[i]=0;}
    const pw_f32v q=numerators/denominators;uint32_t words[PW_LANES];memcpy(words,&q,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i) if(zero_mask&(1u<<i))output[i]=words[i];
  }
  for(unsigned i=0;i<PW_LANES;++i) {
    if(infinity_mask&(1u<<i))output[i]=UINT32_C(0x7f800000);
    if(one_mask&(1u<<i))output[i]=0;
  }
}

/* Bit snapshots support exact input/output or merge/output aliasing only.
 * Every full64B input/merge buffer is readable, even when inactive. */
static int pw_apply_logf(const uint32_t input[PW_LANES],unsigned active,
    const uint32_t merge[PW_LANES],uint32_t output[PW_LANES],int unsafe) {
  if(active&~PW_ALL)return 1;
  uint32_t saved[PW_LANES],pass[PW_LANES],neutral[PW_LANES],value[PW_LANES];
  memcpy(saved,input,64);memcpy(pass,merge,64);
  if(!active && !unsafe){memcpy(output,pass,64);return 0;}
  for(unsigned i=0;i<PW_LANES;++i)neutral[i]=(unsafe || (active&(1u<<i)))?saved[i]:UINT32_C(0x3f800000);
  pw_core_logf(neutral,value);
  for(unsigned i=0;i<PW_LANES;++i)value[i]=(active&(1u<<i))?value[i]:pass[i];
  memcpy(output,value,64);return 0;
}
int phi_host_logf_register_e16(const uint32_t input[PW_LANES],unsigned active,
    const uint32_t merge[PW_LANES],uint32_t output[PW_LANES]) {
  return pw_apply_logf(input,active,merge,output,0);
}
#ifdef PW_ENABLE_NEGATIVE_CONTROL
int phi_host_logf_register_e16_unsafe_negative(const uint32_t input[PW_LANES],unsigned active,
    const uint32_t merge[PW_LANES],uint32_t output[PW_LANES]) {
  return pw_apply_logf(input,active,merge,output,1);
}
#endif
