/* Fresh parameterized host e-width adaptation; old source SHA256 b196727ee0e9a3fbcc5567874e613ca96d2f2c4947ec16e4af78950d9595a77b.
 * Private pointer ABI only; software mask is not a GNU masked-vector ABI. */
#define PW_LANES 16
#define PW_ALL ((1u<<PW_LANES)-1u)
/* Adapted from Arm optimized-routines v26.01 expf.c, exp2f_data.c and
 * math_errf.c at commit 649ccc8411e7c4862965710f25c570d854a1483f.
 * Copyright (c) 2017-2025, Arm Limited. SPDX-License-Identifier: MIT
 * Exact upstream files/license retained under native/upstream/.
 * Adaptation: four-lane GCC vectors, integer classification before any
 * arithmetic, masked exceptional paths. Host research only, no _ZGV export.
 * nearest-even, masked exceptions, FTZ/DAZ off; no errno/other-rounding claim.
 */
#include "e_algorithms.h"
#include <string.h>
typedef float pw_f32v __attribute__((vector_size(PW_LANES*4)));
typedef double pw_f64v __attribute__((vector_size(PW_LANES*8)));
typedef uint64_t pw_u64v __attribute__((vector_size(PW_LANES*8)));
static const uint64_t table[32] = {
  0x3ff0000000000000, 0x3fefd9b0d3158574, 0x3fefb5586cf9890f, 0x3fef9301d0125b51,
  0x3fef72b83c7d517b, 0x3fef54873168b9aa, 0x3fef387a6e756238, 0x3fef1e9df51fdee1,
  0x3fef06fe0a31b715, 0x3feef1a7373aa9cb, 0x3feedea64c123422, 0x3feece086061892d,
  0x3feebfdad5362a27, 0x3feeb42b569d4f82, 0x3feeab07dd485429, 0x3feea47eb03a5585,
  0x3feea09e667f3bcd, 0x3fee9f75e8ec5f74, 0x3feea11473eb0187, 0x3feea589994cce13,
  0x3feeace5422aa0db, 0x3feeb737b0cdc5e5, 0x3feec49182a3f090, 0x3feed503b23e255d,
  0x3feee89f995ad3ad, 0x3feeff76f2fb5e47, 0x3fef199bdd85529c, 0x3fef3720dcef9069,
  0x3fef5818dcfba487, 0x3fef7c97337b9b5f, 0x3fefa4afa2a490da, 0x3fefd0765b6e4540
};

static __attribute__((noinline)) void pw_core_expf(const uint32_t input[PW_LANES], uint32_t output[PW_LANES]) {
  uint32_t active_bits[PW_LANES], nan_bits[PW_LANES]={0};
  unsigned nan_mask=0, over_mask=0, under_mask=0, neg_inf_mask=0;
  for (unsigned i=0; i<PW_LANES; ++i) {
    const uint32_t bits=input[i], magnitude=bits&UINT32_C(0x7fffffff);
    active_bits[i]=bits;
    if (magnitude>=UINT32_C(0x7f800000)) {
      active_bits[i]=0;
      if (magnitude>UINT32_C(0x7f800000)) {
        nan_bits[i]=bits; nan_mask|=1u<<i;
      } else if (bits>>31) neg_inf_mask|=1u<<i;
      else over_mask|=1u<<(i+PW_LANES); /* Exact +Inf: no overflow operation. */
    } else if (!(bits>>31) && bits>UINT32_C(0x42b17217)) {
      active_bits[i]=0; over_mask|=1u<<i;
    } else if ((bits>>31) && bits>UINT32_C(0xc2cff1b4)) {
      active_bits[i]=0; under_mask|=1u<<i;
    }
  }
  pw_f32v x; memcpy(&x,active_bits,sizeof x);
  const pw_f64v xd=__builtin_convertvector(x,pw_f64v);
  pw_f64v z=xd*(0x1.71547652b82fep+0*32);
  pw_f64v kd=z+0x1.8p+52;
  pw_u64v ki; memcpy(&ki,&kd,sizeof ki);
  kd=kd-0x1.8p+52;
  const pw_f64v r=z-kd;
  pw_u64v t;for(unsigned pw_lane=0;pw_lane<PW_LANES;++pw_lane)t[pw_lane]=table[ki[pw_lane]&31];
  t=t+(ki<<47);
  pw_f64v scale; memcpy(&scale,&t,sizeof scale);
  z=(0x1.c6af84b912394p-5/32/32/32)*r+(0x1.ebfce50fac4f3p-3/32/32);
  const pw_f64v r2=r*r;
  pw_f64v y=(0x1.62e42ff0c52d6p-1/32)*r+1;
  y=(z*r2+y)*scale;
  const pw_f32v result=__builtin_convertvector(y,pw_f32v);
  memcpy(output,&result,sizeof result);

  if (nan_mask) {
    pw_f32v n; memcpy(&n,nan_bits,sizeof n);
    /* Actual x+x quiets sNaNs/raises invalid; qNaN sign/payload retained on
     * this x86 host. This explicit host policy is independently checked. */
    const pw_f32v q=n+n; uint32_t bits[PW_LANES]; memcpy(bits,&q,sizeof bits);
    for (unsigned i=0;i<PW_LANES;++i) if(nan_mask&(1u<<i)) output[i]=bits[i];
  }
  if (over_mask&PW_ALL) {
    /* Arm math_errf.c xflowf uses an optimization barrier and y*y with
     * y=2^97. A volatile load supplies the barrier here; no folded Inf. */
    volatile float factor=0x1p97f;
    pw_f32v factors=(pw_f32v){0}+(1);
    for(unsigned i=0;i<PW_LANES;++i) if(over_mask&(1u<<i)) factors[i]=factor;
    const pw_f32v q=factors*factors;uint32_t bits[PW_LANES];memcpy(bits,&q,sizeof bits);
    for(unsigned i=0;i<PW_LANES;++i) if(over_mask&(1u<<i)) output[i]=bits[i];
  }
  if (under_mask) {
    volatile float factor=0x1p-95f;
    pw_f32v factors=(pw_f32v){0}+(1);
    for(unsigned i=0;i<PW_LANES;++i) if(under_mask&(1u<<i)) factors[i]=factor;
    const pw_f32v q=factors*factors;uint32_t bits[PW_LANES];memcpy(bits,&q,sizeof bits);
    for(unsigned i=0;i<PW_LANES;++i) if(under_mask&(1u<<i)) output[i]=bits[i];
  }
  for(unsigned i=0;i<PW_LANES;++i) {
    if(neg_inf_mask&(1u<<i)) output[i]=0;
    if(over_mask&(1u<<(i+PW_LANES))) output[i]=UINT32_C(0x7f800000);
  }
}

/* Bit snapshots support exact input/output or merge/output aliasing only.
 * Every full64B input/merge buffer is readable, even when inactive. */
static int pw_apply_expf(const uint32_t input[PW_LANES],unsigned active,
    const uint32_t merge[PW_LANES],uint32_t output[PW_LANES],int unsafe) {
  if(active&~PW_ALL)return 1;
  uint32_t saved[PW_LANES],pass[PW_LANES],neutral[PW_LANES],value[PW_LANES];
  memcpy(saved,input,64);memcpy(pass,merge,64);
  if(!active && !unsafe){memcpy(output,pass,64);return 0;}
  for(unsigned i=0;i<PW_LANES;++i)neutral[i]=(unsafe || (active&(1u<<i)))?saved[i]:0;
  pw_core_expf(neutral,value);
  for(unsigned i=0;i<PW_LANES;++i)value[i]=(active&(1u<<i))?value[i]:pass[i];
  memcpy(output,value,64);return 0;
}
int phi_host_expf_e16(const uint32_t input[PW_LANES],unsigned active,
    const uint32_t merge[PW_LANES],uint32_t output[PW_LANES]) {
  return pw_apply_expf(input,active,merge,output,0);
}
#ifdef PW_ENABLE_NEGATIVE_CONTROL
int phi_host_expf_e16_unsafe_negative(const uint32_t input[PW_LANES],unsigned active,
    const uint32_t merge[PW_LANES],uint32_t output[PW_LANES]) {
  return pw_apply_expf(input,active,merge,output,1);
}
#endif
