/* Gather-free candidate: original Arm32x64 table and DP arithmetic preserved.
 * Four register-resident16-entry word-half vectors replace indexed loads.
 * Each selected low/high pair reconstructs the original64-bit entry exactly.
 * New source/output still require independent host and card accuracy evidence. */
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
typedef uint32_t pw_u32v __attribute__((vector_size(PW_LANES*4)));
static const pw_u32v pw_table_lo0 __attribute__((aligned(64))) = {
  UINT32_C(0x00000000), UINT32_C(0xd3158574), UINT32_C(0x6cf9890f), UINT32_C(0xd0125b51), UINT32_C(0x3c7d517b), UINT32_C(0x3168b9aa), UINT32_C(0x6e756238), UINT32_C(0xf51fdee1), UINT32_C(0x0a31b715), UINT32_C(0x373aa9cb), UINT32_C(0x4c123422), UINT32_C(0x6061892d), UINT32_C(0xd5362a27), UINT32_C(0x569d4f82), UINT32_C(0xdd485429), UINT32_C(0xb03a5585)
};
static const pw_u32v pw_table_lo1 __attribute__((aligned(64))) = {
  UINT32_C(0x667f3bcd), UINT32_C(0xe8ec5f74), UINT32_C(0x73eb0187), UINT32_C(0x994cce13), UINT32_C(0x422aa0db), UINT32_C(0xb0cdc5e5), UINT32_C(0x82a3f090), UINT32_C(0xb23e255d), UINT32_C(0x995ad3ad), UINT32_C(0xf2fb5e47), UINT32_C(0xdd85529c), UINT32_C(0xdcef9069), UINT32_C(0xdcfba487), UINT32_C(0x337b9b5f), UINT32_C(0xa2a490da), UINT32_C(0x5b6e4540)
};
static const pw_u32v pw_table_hi0 __attribute__((aligned(64))) = {
  UINT32_C(0x3ff00000), UINT32_C(0x3fefd9b0), UINT32_C(0x3fefb558), UINT32_C(0x3fef9301), UINT32_C(0x3fef72b8), UINT32_C(0x3fef5487), UINT32_C(0x3fef387a), UINT32_C(0x3fef1e9d), UINT32_C(0x3fef06fe), UINT32_C(0x3feef1a7), UINT32_C(0x3feedea6), UINT32_C(0x3feece08), UINT32_C(0x3feebfda), UINT32_C(0x3feeb42b), UINT32_C(0x3feeab07), UINT32_C(0x3feea47e)
};
static const pw_u32v pw_table_hi1 __attribute__((aligned(64))) = {
  UINT32_C(0x3feea09e), UINT32_C(0x3fee9f75), UINT32_C(0x3feea114), UINT32_C(0x3feea589), UINT32_C(0x3feeace5), UINT32_C(0x3feeb737), UINT32_C(0x3feec491), UINT32_C(0x3feed503), UINT32_C(0x3feee89f), UINT32_C(0x3feeff76), UINT32_C(0x3fef199b), UINT32_C(0x3fef3720), UINT32_C(0x3fef5818), UINT32_C(0x3fef7c97), UINT32_C(0x3fefa4af), UINT32_C(0x3fefd076)
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
  const pw_u32v index=__builtin_convertvector(ki & 31, pw_u32v);
  const pw_u32v select=-(index >> 4);
  const pw_u32v slot=index & 15;
  const pw_u32v lo0=__builtin_shuffle(pw_table_lo0,slot);
  const pw_u32v lo1=__builtin_shuffle(pw_table_lo1,slot);
  const pw_u32v hi0=__builtin_shuffle(pw_table_hi0,slot);
  const pw_u32v hi1=__builtin_shuffle(pw_table_hi1,slot);
  const pw_u32v lo=(lo0 & ~select) | (lo1 & select);
  const pw_u32v hi=(hi0 & ~select) | (hi1 & select);
  pw_u64v t=__builtin_convertvector(lo,pw_u64v)
    | (__builtin_convertvector(hi,pw_u64v) << 32);
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
