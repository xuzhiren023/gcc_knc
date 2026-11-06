/* Adapted from Arm optimized-routines v26.01 expf.c, exp2f_data.c and
 * math_errf.c at commit 649ccc8411e7c4862965710f25c570d854a1483f.
 * Copyright (c) 2017-2025, Arm Limited. SPDX-License-Identifier: MIT
 * Exact upstream files/license retained under native/upstream/.
 * Adaptation: four-lane GCC vectors, integer classification before any
 * arithmetic, masked exceptional paths. Host research only, no _ZGV export.
 * nearest-even, masked exceptions, FTZ/DAZ off; no errno/other-rounding claim.
 */
#include "expf_full.h"
#include <string.h>
typedef float f32x4 __attribute__((vector_size(16)));
typedef double f64x4 __attribute__((vector_size(32)));
typedef uint64_t u64x4 __attribute__((vector_size(32)));
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

void phi_host_expf_full4(const uint32_t input[4], uint32_t output[4]) {
  uint32_t active_bits[4], nan_bits[4]={0,0,0,0};
  unsigned nan_mask=0, over_mask=0, under_mask=0, neg_inf_mask=0;
  for (unsigned i=0; i<4; ++i) {
    const uint32_t bits=input[i], magnitude=bits&UINT32_C(0x7fffffff);
    active_bits[i]=bits;
    if (magnitude>=UINT32_C(0x7f800000)) {
      active_bits[i]=0;
      if (magnitude>UINT32_C(0x7f800000)) {
        nan_bits[i]=bits; nan_mask|=1u<<i;
      } else if (bits>>31) neg_inf_mask|=1u<<i;
      else over_mask|=1u<<(i+4); /* Exact +Inf: no overflow operation. */
    } else if (!(bits>>31) && bits>UINT32_C(0x42b17217)) {
      active_bits[i]=0; over_mask|=1u<<i;
    } else if ((bits>>31) && bits>UINT32_C(0xc2cff1b4)) {
      active_bits[i]=0; under_mask|=1u<<i;
    }
  }
  f32x4 x; memcpy(&x,active_bits,sizeof x);
  const f64x4 xd=__builtin_convertvector(x,f64x4);
  f64x4 z=xd*(0x1.71547652b82fep+0*32);
  f64x4 kd=z+0x1.8p+52;
  u64x4 ki; memcpy(&ki,&kd,sizeof ki);
  kd=kd-0x1.8p+52;
  const f64x4 r=z-kd;
  u64x4 t={table[ki[0]&31],table[ki[1]&31],table[ki[2]&31],table[ki[3]&31]};
  t=t+(ki<<47);
  f64x4 scale; memcpy(&scale,&t,sizeof scale);
  z=(0x1.c6af84b912394p-5/32/32/32)*r+(0x1.ebfce50fac4f3p-3/32/32);
  const f64x4 r2=r*r;
  f64x4 y=(0x1.62e42ff0c52d6p-1/32)*r+1;
  y=(z*r2+y)*scale;
  const f32x4 result=__builtin_convertvector(y,f32x4);
  memcpy(output,&result,sizeof result);

  if (nan_mask) {
    f32x4 n; memcpy(&n,nan_bits,sizeof n);
    /* Actual x+x quiets sNaNs/raises invalid; qNaN sign/payload retained on
     * this x86 host. This explicit host policy is independently checked. */
    const f32x4 q=n+n; uint32_t bits[4]; memcpy(bits,&q,sizeof bits);
    for (unsigned i=0;i<4;++i) if(nan_mask&(1u<<i)) output[i]=bits[i];
  }
  if (over_mask&15) {
    /* Arm math_errf.c xflowf uses an optimization barrier and y*y with
     * y=2^97. A volatile load supplies the barrier here; no folded Inf. */
    volatile float factor=0x1p97f;
    f32x4 factors={1,1,1,1};
    for(unsigned i=0;i<4;++i) if(over_mask&(1u<<i)) factors[i]=factor;
    const f32x4 q=factors*factors;uint32_t bits[4];memcpy(bits,&q,sizeof bits);
    for(unsigned i=0;i<4;++i) if(over_mask&(1u<<i)) output[i]=bits[i];
  }
  if (under_mask) {
    volatile float factor=0x1p-95f;
    f32x4 factors={1,1,1,1};
    for(unsigned i=0;i<4;++i) if(under_mask&(1u<<i)) factors[i]=factor;
    const f32x4 q=factors*factors;uint32_t bits[4];memcpy(bits,&q,sizeof bits);
    for(unsigned i=0;i<4;++i) if(under_mask&(1u<<i)) output[i]=bits[i];
  }
  for(unsigned i=0;i<4;++i) {
    if(neg_inf_mask&(1u<<i)) output[i]=0;
    if(over_mask&(1u<<(i+4))) output[i]=UINT32_C(0x7f800000);
  }
}
