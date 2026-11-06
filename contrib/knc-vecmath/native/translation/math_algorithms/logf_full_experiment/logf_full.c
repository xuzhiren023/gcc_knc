/* Adapted from Arm optimized-routines v26.01 logf.c, logf_data.c and
 * math_errf.c at commit 649ccc8411e7c4862965710f25c570d854a1483f.
 * Copyright (c) 2017-2025, Arm Limited. SPDX-License-Identifier: MIT
 * Exact upstream source/license retained under native/upstream/.
 * Adaptation: four-lane GCC vectors, sanitized exceptional lanes, original
 * exact subnormal normalization and N16 degree-four polynomial/data.
 * Host research only; no scalar logf delegation or _ZGV export.
 */
#include "logf_full.h"
#include <string.h>
typedef float f32x4 __attribute__((vector_size(16)));
typedef double f64x4 __attribute__((vector_size(32)));
typedef uint32_t u32x4 __attribute__((vector_size(16)));
typedef int32_t i32x4 __attribute__((vector_size(16)));
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

void phi_host_logf_full4(const uint32_t input[4],uint32_t output[4]) {
  uint32_t active[4],norm_input[4]={0x3f800000,0x3f800000,0x3f800000,0x3f800000};
  uint32_t invalid_input[4]={0,0,0,0};
  unsigned zero_mask=0,invalid_mask=0,subnormal_mask=0,infinity_mask=0,one_mask=0;
  for(unsigned i=0;i<4;++i) {
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
    f32x4 n;memcpy(&n,norm_input,sizeof n);
    const f32x4 scaled=n*0x1p23f;uint32_t words[4];memcpy(words,&scaled,sizeof words);
    for(unsigned i=0;i<4;++i) if(subnormal_mask&(1u<<i))
      active[i]=words[i]-(23u<<23); /* Original unsigned exponent adjustment. */
  }
  u32x4 ix;memcpy(&ix,active,sizeof ix);
  const u32x4 tmp=ix-UINT32_C(0x3f330000),index=(tmp>>19)&15;
  i32x4 signed_tmp;memcpy(&signed_tmp,&tmp,sizeof tmp);
  const i32x4 k=signed_tmp>>23;
  const u32x4 iz=ix-(tmp&UINT32_C(0xff800000));
  f32x4 zf;memcpy(&zf,&iz,sizeof zf);
  const f64x4 z=__builtin_convertvector(zf,f64x4);
  const f64x4 invc={table[index[0]].invc,table[index[1]].invc,table[index[2]].invc,table[index[3]].invc};
  const f64x4 logc={table[index[0]].logc,table[index[1]].logc,table[index[2]].logc,table[index[3]].logc};
  const f64x4 r=z*invc-1;
  const f64x4 y0=logc+__builtin_convertvector(k,f64x4)*0x1.62e42fefa39efp-1;
  const f64x4 r2=r*r;
  f64x4 y=0x1.5575b0be00b6ap-2*r+(-0x1.ffffef20a4123p-2);
  y=(-0x1.00ea348b88334p-2)*r2+y;
  y=y*r2+(y0+r);
  const f32x4 result=__builtin_convertvector(y,f32x4);
  memcpy(output,&result,sizeof result);
  if(invalid_mask) {
    /* Original math_errf.c (x-x)/(x-x). Quiet NaNs propagate without invalid;
     * sNaNs and negative-domain inputs raise invalid. The inactive lanes
     * use0/1 so a quiet-NaN-only vector cannot spuriously raise invalid. */
    f32x4 v;memcpy(&v,invalid_input,sizeof v);
    const f32x4 difference=v-v;
    uint32_t denom_bits[4];memcpy(denom_bits,&difference,sizeof denom_bits);
    for(unsigned i=0;i<4;++i) if(!(invalid_mask&(1u<<i)))denom_bits[i]=UINT32_C(0x3f800000);
    f32x4 denominator;memcpy(&denominator,denom_bits,sizeof denominator);
    const f32x4 q=difference/denominator;uint32_t words[4];memcpy(words,&q,sizeof words);
    for(unsigned i=0;i<4;++i) if(invalid_mask&(1u<<i))output[i]=words[i];
  }
  if(zero_mask) {
    /* Original math_errf.c barrier(-1.0f)/0.0f. A volatile numerator keeps
     * actual divide-by-zero arithmetic; inactive lanes use exact1/1. */
    volatile float negative_one=-1.0f;
    f32x4 numerators={1,1,1,1},denominators={1,1,1,1};
    for(unsigned i=0;i<4;++i) if(zero_mask&(1u<<i)) {numerators[i]=negative_one;denominators[i]=0;}
    const f32x4 q=numerators/denominators;uint32_t words[4];memcpy(words,&q,sizeof words);
    for(unsigned i=0;i<4;++i) if(zero_mask&(1u<<i))output[i]=words[i];
  }
  for(unsigned i=0;i<4;++i) {
    if(infinity_mask&(1u<<i))output[i]=UINT32_C(0x7f800000);
    if(one_mask&(1u<<i))output[i]=0;
  }
}
