/* New gather-free DP8 log candidate; original FP expressions unchanged. */
/* Fresh parameterized host e-width adaptation; old source SHA256 67c29bad8761baa04e5c17a40a1854dabd6acc29768c210295e12d6ac98ba446.
 * Private pointer ABI only; software mask is not a GNU masked-vector ABI. */
#define PW_LANES 8
#define PW_ALL ((1u<<PW_LANES)-1u)
/* Adapted from Arm optimized-routines v26.01 log.c/log_data.c/math_err.c.
 * Copyright (c) 2018-2025, Arm Limited. SPDX-License-Identifier: MIT
 * Commit649ccc8411e7c4862965710f25c570d854a1483f, exact data/license retained.
 * GCC four-lane adaptation, exact subnormal normalization and branch-lane
 * sanitization. No scalar log delegation, _ZGV exports or target qualification.
 */
#include "e_algorithms.h"
#include "math_config.h"
#include <string.h>
typedef double pw_f64v __attribute__((vector_size(PW_LANES*8)));
typedef uint64_t pw_u64v __attribute__((vector_size(PW_LANES*8)));
typedef int64_t pw_i64v __attribute__((vector_size(PW_LANES*8)));
_Static_assert(LOG_TABLE_BITS==7 && LOG_POLY_ORDER==6 && LOG_POLY1_ORDER==12 && HAVE_FAST_FMA==0,"unsupported upstream configuration");
#include "e_log_register_table.h"

static __attribute__((noinline)) void pw_core_log(const uint64_t input[PW_LANES],uint64_t output[PW_LANES]) {
  uint64_t active[PW_LANES],norm_input[PW_LANES]={0};for(unsigned pw_lane=0;pw_lane<PW_LANES;++pw_lane)norm_input[pw_lane]=0x3ff0000000000000;
  uint64_t invalid_input[PW_LANES]={0,0,0,0},nearbits[PW_LANES],farbits[PW_LANES];
  unsigned valid=0,zeros=0,invalid=0,subnormal=0,infinity=0,far=0,ones=0;
  for(unsigned i=0;i<PW_LANES;++i) {
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
    pw_f64v n;memcpy(&n,norm_input,sizeof n);
    const pw_f64v scaled=n*0x1p52;uint64_t words[PW_LANES];memcpy(words,&scaled,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i)if(subnormal&(1u<<i))active[i]=words[i]-(UINT64_C(52)<<52);
  }
  for(unsigned i=0;i<PW_LANES;++i) {
    const int near=(valid&(1u<<i)) && input[i]-UINT64_C(0x3fee000000000000)<UINT64_C(0x3ff1090000000000)-UINT64_C(0x3fee000000000000);
    nearbits[i]=near?input[i]:UINT64_C(0x3ff0000000000000);
    farbits[i]=active[i];if((valid&(1u<<i)) && !near)far|=1u<<i;
  }
  pw_f64v x;memcpy(&x,nearbits,sizeof x);
  pw_f64v r=x-1,r2=r*r,r3=r*r2;
  const double *B=__log_data.poly1;
  pw_f64v y=r3*(B[1]+r*B[2]+r2*B[3]+r3*(B[4]+r*B[5]+r2*B[6]+r3*(B[7]+r*B[8]+r2*B[9]+r3*B[10])));
  pw_f64v w=r*0x1p27;
  const pw_f64v rhi=r+w-w,rlo=r-rhi;
  w=rhi*rhi*B[0];pw_f64v hi=r+w,lo=r-hi+w;
  lo=lo+B[0]*rlo*(rhi+r);y=y+lo;y=y+hi;
  memcpy(output,&y,sizeof y);
  if(far) {
    /* Do not evaluate the table path on1 when it is discarded: its reduction
     * need not be exact and could spuriously raise inexact for log(1)/qNaN.
     * Inactive lanes duplicate a real far input, whose inexact is required. */
    unsigned donor=0;while(!(far&(1u<<donor)))++donor;
    for(unsigned i=0;i<PW_LANES;++i)if(!(far&(1u<<i)))farbits[i]=farbits[donor];
    pw_u64v ix;memcpy(&ix,farbits,sizeof ix);
    const pw_u64v tmp=ix-UINT64_C(0x3fe6000000000000),index=(tmp>>45)&127;
    pw_i64v stmp;memcpy(&stmp,&tmp,sizeof tmp);const pw_i64v k=stmp>>52;
    const pw_u64v iz=ix-(tmp&UINT64_C(0xfff0000000000000));
    pw_f64v z;memcpy(&z,&iz,sizeof z);
    pw_f64v invc,logc,chi,clo;
    pw_log_register_lookup(index,&invc,&logc,&chi,&clo);
    r=(z-chi-clo)*invc;const pw_f64v kd=__builtin_convertvector(k,pw_f64v);
    w=kd*__log_data.ln2hi+logc;hi=w+r;lo=w-hi+r+kd*__log_data.ln2lo;
    r2=r*r;const double *A=__log_data.poly;
    y=lo+r2*A[0]+r*r2*(A[1]+r*A[2]+r2*(A[3]+r*A[4]))+hi;
    uint64_t words[PW_LANES];memcpy(words,&y,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i)if(far&(1u<<i))output[i]=words[i];
  }
  if(invalid) {
    pw_f64v v;memcpy(&v,invalid_input,sizeof v);const pw_f64v difference=v-v;
    uint64_t denominator_bits[PW_LANES];memcpy(denominator_bits,&difference,sizeof denominator_bits);
    for(unsigned i=0;i<PW_LANES;++i)if(!(invalid&(1u<<i)))denominator_bits[i]=UINT64_C(0x3ff0000000000000);
    pw_f64v denominator;memcpy(&denominator,denominator_bits,sizeof denominator);
    const pw_f64v q=difference/denominator;uint64_t words[PW_LANES];memcpy(words,&q,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i)if(invalid&(1u<<i))output[i]=words[i];
  }
  if(zeros) {
    volatile double negative_one=-1.0;pw_f64v numerators=(pw_f64v){0}+1,denominators=(pw_f64v){0}+1;
    for(unsigned i=0;i<PW_LANES;++i)if(zeros&(1u<<i)){numerators[i]=negative_one;denominators[i]=0;}
    const pw_f64v q=numerators/denominators;uint64_t words[PW_LANES];memcpy(words,&q,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i)if(zeros&(1u<<i))output[i]=words[i];
  }
  for(unsigned i=0;i<PW_LANES;++i){if(infinity&(1u<<i))output[i]=UINT64_C(0x7ff0000000000000);if(ones&(1u<<i))output[i]=0;}
}

/* Bit snapshots support exact input/output or merge/output aliasing only.
 * Every full64B input/merge buffer is readable, even when inactive. */
static int pw_apply_log(const uint64_t input[PW_LANES],unsigned active,
    const uint64_t merge[PW_LANES],uint64_t output[PW_LANES],int unsafe) {
  if(active&~PW_ALL)return 1;
  uint64_t saved[PW_LANES],pass[PW_LANES],neutral[PW_LANES],value[PW_LANES];
  memcpy(saved,input,64);memcpy(pass,merge,64);
  if(!active && !unsafe){memcpy(output,pass,64);return 0;}
  for(unsigned i=0;i<PW_LANES;++i)neutral[i]=(unsafe || (active&(1u<<i)))?saved[i]:UINT64_C(0x3ff0000000000000);
  pw_core_log(neutral,value);
  for(unsigned i=0;i<PW_LANES;++i)value[i]=(active&(1u<<i))?value[i]:pass[i];
  memcpy(output,value,64);return 0;
}
int phi_host_log_register_e8(const uint64_t input[PW_LANES],unsigned active,
    const uint64_t merge[PW_LANES],uint64_t output[PW_LANES]) {
  return pw_apply_log(input,active,merge,output,0);
}
#ifdef PW_ENABLE_NEGATIVE_CONTROL
int phi_host_log_register_e8_unsafe_negative(const uint64_t input[PW_LANES],unsigned active,
    const uint64_t merge[PW_LANES],uint64_t output[PW_LANES]) {
  return pw_apply_log(input,active,merge,output,1);
}
#endif
