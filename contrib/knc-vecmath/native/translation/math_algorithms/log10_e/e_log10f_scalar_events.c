/* Additive G5 v2 candidate: only exceptional events differ from e_log10f.c.
 * Scalar volatile event pattern reused from qualified logf; no target claim. */
/* New log10f adaptation, scaling the DOUBLE polynomial before SP rounding.
 * Official Arm log10f.c commit649ccc8411e7c4862965710f25c570d854a1483f.
 * Shared reduction/special machinery follows the retained e_logf.c;
 * Private pointer ABI only; software mask is not a GNU masked-vector ABI. */
#define PW_LANES 16
#define PW_ALL ((1u<<PW_LANES)-1u)
/* Adapted from Arm optimized-routines v26.01 log10f.c, logf_data.c and
 * math_errf.c at commit 649ccc8411e7c4862965710f25c570d854a1483f.
 * Copyright (c) 2017-2025, Arm Limited. SPDX-License-Identifier: MIT
 * Exact upstream source/license retained under native/upstream/.
 * Adaptation:16-lane GCC vectors, sanitized exceptional lanes, original
 * exact subnormal normalization and N16 degree-four polynomial/data.
 * Host research only; no rounded-SP logf delegation or target _ZGV proof.
 */
#include "log10_e.h"
#include <string.h>
typedef float pw_f32v __attribute__((vector_size(PW_LANES*4)));
typedef double pw_f64v __attribute__((vector_size(PW_LANES*8)));
typedef uint32_t pw_u32v __attribute__((vector_size(PW_LANES*4)));
typedef int32_t pw_i32v __attribute__((vector_size(PW_LANES*4)));
static const struct {double invc,logc;} table[16]={
  {0x1.661ec79f8f3bep+0,-0x1.57bf7808caadep-2},
  {0x1.571ed4aaf883dp+0,-0x1.2bef0a7c06ddbp-2},
  {0x1.49539f0f010bp+0,-0x1.01eae7f513a67p-2},
  {0x1.3c995b0b80385p+0,-0x1.b31d8a68224e9p-3},
  {0x1.30d190c8864a5p+0,-0x1.6574f0ac07758p-3},
  {0x1.25e227b0b8eap+0,-0x1.1aa2bc79c81p-3},
  {0x1.1bb4a4a1a343fp+0,-0x1.a4e76ce8c0e5ep-4},
  {0x1.12358f08ae5bap+0,-0x1.1973c5a611cccp-4},
  {0x1.0953f419900a7p+0,-0x1.252f438e10c1ep-5},
  {0x1p+0,0x0p+0},
  {0x1.e608cfd9a47acp-1,0x1.aa5aa5df25984p-5},
  {0x1.ca4b31f026aap-1,0x1.c5e53aa362eb4p-4},
  {0x1.b2036576afce6p-1,0x1.526e57720db08p-3},
  {0x1.9c2d163a1aa2dp-1,0x1.bc2860d22477p-3},
  {0x1.886e6037841edp-1,0x1.1058bc8a07ee1p-2},
  {0x1.767dcf5534862p-1,0x1.4043057b6ee09p-2}
};

static __attribute__((noinline)) void pw_core_log10f(const uint32_t input[PW_LANES],uint32_t output[PW_LANES]) {
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
  pw_f64v invc;for(unsigned pw_lane=0;pw_lane<PW_LANES;++pw_lane)invc[pw_lane]=table[index[pw_lane]].invc;
  pw_f64v logc;for(unsigned pw_lane=0;pw_lane<PW_LANES;++pw_lane)logc[pw_lane]=table[index[pw_lane]].logc;
  const pw_f64v r=z*invc-1;
  const pw_f64v y0=logc+__builtin_convertvector(k,pw_f64v)*0x1.62e42fefa39efp-1;
  const pw_f64v r2=r*r;
  pw_f64v y=0x1.5575b0be00b6ap-2*r+(-0x1.ffffef20a4123p-2);
  y=(-0x1.00ea348b88334p-2)*r2+y;
  y=y*r2+(y0+r);
  const pw_f32v result=__builtin_convertvector(y*0x1.bcb7b1526e50ep-2,pw_f32v);
  memcpy(output,&result,sizeof result);
  if(invalid_mask) {
    /* Preserve the original vector subtraction as an observable FP event:
     * sNaN quieting and negative-subnormal effects follow caller controls.
     * This replaces only exceptional output/event selection; the finite
     * expressions, tables and subnormal normalization above are unchanged. */
    pw_f32v v;memcpy(&v,invalid_input,sizeof v);
    volatile pw_f32v subtraction_event=v-v;
    (void)subtraction_event;
    /* Volatile scalar words prevent exceptional payload selection from
     * becoming a generic byte-SIMD operation. No FP control is changed. */
    volatile unsigned domain_negative=0;
    volatile uint32_t *exception_output=output;
    for(unsigned i=0;i<PW_LANES;++i) if(invalid_mask&(1u<<i)) {
      volatile uint32_t input_word=invalid_input[i];
      const uint32_t bits=input_word,magnitude=bits&UINT32_C(0x7fffffff);
      if(magnitude>UINT32_C(0x7f800000))
        exception_output[i]=bits|UINT32_C(0x00400000);
      else {
        /* This invalid-mask branch contains only negative non-NaN inputs;
         * both signs of zero were classified into zero_mask first. */
        exception_output[i]=UINT32_C(0xffc00000);
        domain_negative=1;
      }
    }
    if(domain_negative) {
      /* Require actual scalar invalid arithmetic only for domain errors.
       * A quiet-NaN-only block never evaluates scalar zero/zero. */
      volatile float numerator=0.0f,denominator=0.0f;
      volatile float invalid_event=numerator/denominator;
      (void)invalid_event;
    }
  }
  if(zero_mask) {
    /* Both signs of zero return -infinity; actual scalar -1/+0 supplies ZD. */
    volatile float negative_one=-1.0f,positive_zero=0.0f;
    volatile float pole_event=negative_one/positive_zero;
    (void)pole_event;
    volatile uint32_t *exception_output=output;
    for(unsigned i=0;i<PW_LANES;++i) if(zero_mask&(1u<<i))
      exception_output[i]=UINT32_C(0xff800000);
  }
  for(unsigned i=0;i<PW_LANES;++i) {
    if(infinity_mask&(1u<<i))output[i]=UINT32_C(0x7f800000);
    if(one_mask&(1u<<i))output[i]=0;
  }
}

/* Bit snapshots support exact input/output or merge/output aliasing only.
 * Every full64B input/merge buffer is readable, even when inactive. */
static int pw_apply_log10f(const uint32_t input[PW_LANES],unsigned active,
    const uint32_t merge[PW_LANES],uint32_t output[PW_LANES],int unsafe) {
  if(active&~PW_ALL)return 1;
  uint32_t saved[PW_LANES],pass[PW_LANES],neutral[PW_LANES],value[PW_LANES];
  memcpy(saved,input,64);memcpy(pass,merge,64);
  if(!active && !unsafe){memcpy(output,pass,64);return 0;}
  for(unsigned i=0;i<PW_LANES;++i)neutral[i]=(unsafe || (active&(1u<<i)))?saved[i]:UINT32_C(0x3f800000);
  pw_core_log10f(neutral,value);
  for(unsigned i=0;i<PW_LANES;++i)value[i]=(active&(1u<<i))?value[i]:pass[i];
  memcpy(output,value,64);return 0;
}
int phi_host_log10f_e16(const uint32_t input[PW_LANES],unsigned active,
    const uint32_t merge[PW_LANES],uint32_t output[PW_LANES]) {
  return pw_apply_log10f(input,active,merge,output,0);
}
#ifdef PW_ENABLE_NEGATIVE_CONTROL
int phi_host_log10f_e16_unsafe_negative(const uint32_t input[PW_LANES],unsigned active,
    const uint32_t merge[PW_LANES],uint32_t output[PW_LANES]) {
  return pw_apply_log10f(input,active,merge,output,1);
}
#endif
