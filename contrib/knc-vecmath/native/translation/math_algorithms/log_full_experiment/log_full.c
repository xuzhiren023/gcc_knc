/* Adapted from Arm optimized-routines v26.01 log.c/log_data.c/math_err.c.
 * Copyright (c) 2018-2025, Arm Limited. SPDX-License-Identifier: MIT
 * Commit649ccc8411e7c4862965710f25c570d854a1483f, exact data/license retained.
 * GCC four-lane adaptation, exact subnormal normalization and branch-lane
 * sanitization. No scalar log delegation, _ZGV exports or target qualification.
 */
#include "log_full.h"
#include "../../../upstream/arm-optimized-routines-v26.01-dp/math/math_config.h"
#include <string.h>
typedef double f64x4 __attribute__((vector_size(32)));
typedef uint64_t u64x4 __attribute__((vector_size(32)));
typedef int64_t i64x4 __attribute__((vector_size(32)));
_Static_assert(LOG_TABLE_BITS==7 && LOG_POLY_ORDER==6 && LOG_POLY1_ORDER==12 && HAVE_FAST_FMA==0,"unsupported upstream configuration");

void phi_host_log_full4(const uint64_t input[4],uint64_t output[4]) {
  uint64_t active[4],norm_input[4]={0x3ff0000000000000,0x3ff0000000000000,0x3ff0000000000000,0x3ff0000000000000};
  uint64_t invalid_input[4]={0,0,0,0},nearbits[4],farbits[4];
  unsigned valid=0,zeros=0,invalid=0,subnormal=0,infinity=0,far=0,ones=0;
  for(unsigned i=0;i<4;++i) {
    const uint64_t bits=input[i],mag=bits&UINT64_C(0x7fffffffffffffff);
    active[i]=UINT64_C(0x3ff0000000000000);
    if(!mag)zeros|=1u<<i;
    else if(mag>UINT64_C(0x7ff0000000000000) || (bits>>63)) {invalid|=1u<<i;invalid_input[i]=bits;}
    else if(bits==UINT64_C(0x7ff0000000000000))infinity|=1u<<i;
    else {
      valid|=1u<<i;active[i]=bits;
      if(bits<UINT64_C(0x0010000000000000)){subnormal|=1u<<i;norm_input[i]=bits;}
      if(bits==UINT64_C(0x3ff0000000000000))ones|=1u<<i;
    }
  }
  if(subnormal) {
    f64x4 n;memcpy(&n,norm_input,sizeof n);
    const f64x4 scaled=n*0x1p52;uint64_t words[4];memcpy(words,&scaled,sizeof words);
    for(unsigned i=0;i<4;++i)if(subnormal&(1u<<i))active[i]=words[i]-(UINT64_C(52)<<52);
  }
  for(unsigned i=0;i<4;++i) {
    const int near=(valid&(1u<<i)) && input[i]-UINT64_C(0x3fee000000000000)<UINT64_C(0x3ff1090000000000)-UINT64_C(0x3fee000000000000);
    nearbits[i]=near?input[i]:UINT64_C(0x3ff0000000000000);
    farbits[i]=active[i];if((valid&(1u<<i)) && !near)far|=1u<<i;
  }
  f64x4 x;memcpy(&x,nearbits,sizeof x);
  f64x4 r=x-1,r2=r*r,r3=r*r2;
  const double *B=__log_data.poly1;
  f64x4 y=r3*(B[1]+r*B[2]+r2*B[3]+r3*(B[4]+r*B[5]+r2*B[6]+r3*(B[7]+r*B[8]+r2*B[9]+r3*B[10])));
  f64x4 w=r*0x1p27;
  const f64x4 rhi=r+w-w,rlo=r-rhi;
  w=rhi*rhi*B[0];f64x4 hi=r+w,lo=r-hi+w;
  lo=lo+B[0]*rlo*(rhi+r);y=y+lo;y=y+hi;
  memcpy(output,&y,sizeof y);
  if(far) {
    /* Do not evaluate the table path on1 when it is discarded: its reduction
     * need not be exact and could spuriously raise inexact for log(1)/qNaN.
     * Inactive lanes duplicate a real far input, whose inexact is required. */
    unsigned donor=0;while(!(far&(1u<<donor)))++donor;
    for(unsigned i=0;i<4;++i)if(!(far&(1u<<i)))farbits[i]=farbits[donor];
    u64x4 ix;memcpy(&ix,farbits,sizeof ix);
    const u64x4 tmp=ix-UINT64_C(0x3fe6000000000000),index=(tmp>>45)&127;
    i64x4 stmp;memcpy(&stmp,&tmp,sizeof tmp);const i64x4 k=stmp>>52;
    const u64x4 iz=ix-(tmp&UINT64_C(0xfff0000000000000));
    f64x4 z;memcpy(&z,&iz,sizeof z);
    const f64x4 invc={__log_data.tab[index[0]].invc,__log_data.tab[index[1]].invc,__log_data.tab[index[2]].invc,__log_data.tab[index[3]].invc};
    const f64x4 logc={__log_data.tab[index[0]].logc,__log_data.tab[index[1]].logc,__log_data.tab[index[2]].logc,__log_data.tab[index[3]].logc};
    const f64x4 chi={__log_data.tab2[index[0]].chi,__log_data.tab2[index[1]].chi,__log_data.tab2[index[2]].chi,__log_data.tab2[index[3]].chi};
    const f64x4 clo={__log_data.tab2[index[0]].clo,__log_data.tab2[index[1]].clo,__log_data.tab2[index[2]].clo,__log_data.tab2[index[3]].clo};
    r=(z-chi-clo)*invc;const f64x4 kd=__builtin_convertvector(k,f64x4);
    w=kd*__log_data.ln2hi+logc;hi=w+r;lo=w-hi+r+kd*__log_data.ln2lo;
    r2=r*r;const double *A=__log_data.poly;
    y=lo+r2*A[0]+r*r2*(A[1]+r*A[2]+r2*(A[3]+r*A[4]))+hi;
    uint64_t words[4];memcpy(words,&y,sizeof words);
    for(unsigned i=0;i<4;++i)if(far&(1u<<i))output[i]=words[i];
  }
  if(invalid) {
    f64x4 v;memcpy(&v,invalid_input,sizeof v);const f64x4 difference=v-v;
    uint64_t denominator_bits[4];memcpy(denominator_bits,&difference,sizeof denominator_bits);
    for(unsigned i=0;i<4;++i)if(!(invalid&(1u<<i)))denominator_bits[i]=UINT64_C(0x3ff0000000000000);
    f64x4 denominator;memcpy(&denominator,denominator_bits,sizeof denominator);
    const f64x4 q=difference/denominator;uint64_t words[4];memcpy(words,&q,sizeof words);
    for(unsigned i=0;i<4;++i)if(invalid&(1u<<i))output[i]=words[i];
  }
  if(zeros) {
    volatile double negative_one=-1.0;f64x4 numerators={1,1,1,1},denominators={1,1,1,1};
    for(unsigned i=0;i<4;++i)if(zeros&(1u<<i)){numerators[i]=negative_one;denominators[i]=0;}
    const f64x4 q=numerators/denominators;uint64_t words[4];memcpy(words,&q,sizeof words);
    for(unsigned i=0;i<4;++i)if(zeros&(1u<<i))output[i]=words[i];
  }
  for(unsigned i=0;i<4;++i){if(infinity&(1u<<i))output[i]=UINT64_C(0x7ff0000000000000);if(ones&(1u<<i))output[i]=0;}
}
