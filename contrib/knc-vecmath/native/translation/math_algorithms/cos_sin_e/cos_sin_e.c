/* GCC DP8-vector adaptation of musl v1.2.5 __sin.c and __cos.c.
 * ====================================================
 * Copyright (C) 1993 by Sun Microsystems, Inc. All rights reserved.
 * Developed at SunSoft, a Sun Microsystems, Inc. business.
 * Permission to use, copy, modify, and distribute this software is freely
 * granted, provided that this notice is preserved.
 * ====================================================
 * Changes: scalar complete-domain official reduction, 8-DP vector polynomial,
 * lane classification/sanitization, integer quadrant selection and private
 * 64-byte raw pointer ABI. SP16 evaluates two DP8 groups and rounds once.
 * Source experiment only: target vector ABI/ISA/performance remain unqualified.
 */
#include "cos_sin_e.h"
#include <string.h>
#ifdef __FAST_MATH__
#error "cos_sin_e requires strict FP"
#endif
typedef double dv __attribute__((vector_size(64)));
typedef float fv __attribute__((vector_size(64)));
int phi_trig_rem_pio2(double,double *);
static uint64_t dbits(double x){uint64_t b;memcpy(&b,&x,8);return b;}
static double dvalue(uint64_t b){double x;memcpy(&x,&b,8);return x;}

/* S10-11: round the reduced-tail reconstruction separately from the polynomial.
 * Keep this boundary out of line so inlining cannot restore caller contraction. */
#pragma GCC push_options
#pragma GCC optimize ("fp-contract=off")
static __attribute__((noinline)) void compensated_sincos(dv x,dv y,dv z,dv sr,dv cr,dv *s,dv *c) {
  const dv v=z*x;
  *s=x-((z*(.5*y-v*sr)-y)-v*(-1.66666666666666324348e-01));
  const dv hz=.5*z,cw=1-hz;
  *c=cw+(((1-cw)-hz)+(z*cr-x*y));
}
#pragma GCC pop_options

/* All actual polynomial arithmetic is GCC-vector arithmetic. Per-lane range
 * reduction supplies high/low parts and quadrant, never a trig result. */
static __attribute__((noinline)) void finite_core(const double input[8],double output[8],int cosine) {
  dv x,y;unsigned quadrant[8],small[8];
  for(unsigned i=0;i<8;++i) {
    uint64_t mag=dbits(input[i])&UINT64_C(0x7fffffffffffffff);
    small[i]=mag<UINT64_C(0x3e40000000000000); /* <2^-27 */
    quadrant[i]=0;x[i]=small[i]?0:input[i];y[i]=0;
    if(mag>UINT64_C(0x3fe921fb54442d18)) {
      double reduced[2];quadrant[i]=(unsigned)phi_trig_rem_pio2(input[i],reduced)&3;
      x[i]=reduced[0];y[i]=reduced[1];
    }
  }
  const dv z=x*x,w=z*z;
  const dv sr=8.33333333332248946124e-03+z*(-1.98412698298579493134e-04+z*2.75573137070700676789e-06)
       +z*w*(-2.50507602534068634195e-08+z*1.58969099521155010221e-10);
  const dv cr=z*(4.16666666666666019037e-02+z*(-1.38888888888741095749e-03+z*2.48015872894767294178e-05))
       +w*w*(-2.75573143513906633035e-07+z*(2.08757232129817482790e-09+z*(-1.13596475577881948265e-11)));
  dv s,c;compensated_sincos(x,y,z,sr,cr,&s,&c);
  for(unsigned i=0;i<8;++i) {
    if(small[i]){output[i]=cosine?1:input[i];continue;}
    unsigned q=(quadrant[i]+(unsigned)cosine)&3;
    uint64_t b=dbits((q&1)?c[i]:s[i]);
    if(q&2)b^=UINT64_C(0x8000000000000000);
    output[i]=dvalue(b);
  }
}
static int apply_dp(const uint64_t input[8],unsigned mask,const uint64_t merge[8],uint64_t output[8],int cosine) {
  if(mask&~255u)return 1;
  uint64_t saved[8],pass[8],out[8];double values[8],result[8];unsigned exceptional=0;
  memcpy(saved,input,64);memcpy(pass,merge,64);
  if(!mask){memcpy(output,pass,64);return 0;}
  for(unsigned i=0;i<8;++i) {
    uint64_t mag=saved[i]&UINT64_C(0x7fffffffffffffff);
    if((mask&(1u<<i))&&mag>=UINT64_C(0x7ff0000000000000))exceptional|=1u<<i;
    values[i]=((mask&(1u<<i))&&!(exceptional&(1u<<i)))?dvalue(saved[i]):0;
  }
  finite_core(values,result,cosine);memcpy(out,result,64);
  if(exceptional) {
    dv a={0};for(unsigned i=0;i<8;++i)if(exceptional&(1u<<i))a[i]=dvalue(saved[i]);
    const dv nan=a-a;uint64_t bits[8];memcpy(bits,&nan,64);
    for(unsigned i=0;i<8;++i)if(exceptional&(1u<<i))out[i]=bits[i];
  }
  for(unsigned i=0;i<8;++i)if(!(mask&(1u<<i)))out[i]=pass[i];memcpy(output,out,64);return 0;
}
static int apply_sp(const uint32_t input[16],unsigned mask,const uint32_t merge[16],uint32_t output[16],int cosine) {
  if(mask&~65535u)return 1;
  uint32_t saved[16],pass[16],out[16];unsigned exceptional=0;memcpy(saved,input,64);memcpy(pass,merge,64);
  if(!mask){memcpy(output,pass,64);return 0;}
  for(unsigned group=0;group<2;++group) {
    double values[8],result[8];
    for(unsigned i=0;i<8;++i) {
      unsigned lane=group*8+i;uint32_t mag=saved[lane]&UINT32_C(0x7fffffff);float x=0;
      if((mask&(1u<<lane))&&mag>=UINT32_C(0x7f800000))exceptional|=1u<<lane;
      if((mask&(1u<<lane))&&!(exceptional&(1u<<lane)))memcpy(&x,&saved[lane],4);
      values[i]=(double)x;
    }
    finite_core(values,result,cosine);
    for(unsigned i=0;i<8;++i){float value=(float)result[i];memcpy(&out[group*8+i],&value,4);}
  }
  if(exceptional) {
    fv a={0};for(unsigned i=0;i<16;++i)if(exceptional&(1u<<i))memcpy(&a[i],&saved[i],4);
    const fv nan=a-a;uint32_t bits[16];memcpy(bits,&nan,64);
    for(unsigned i=0;i<16;++i)if(exceptional&(1u<<i))out[i]=bits[i];
  }
  for(unsigned i=0;i<16;++i)if(!(mask&(1u<<i)))out[i]=pass[i];memcpy(output,out,64);return 0;
}
int phi_host_sin_e8(const uint64_t x[8],unsigned m,const uint64_t p[8],uint64_t o[8]){return apply_dp(x,m,p,o,0);}
int phi_host_cos_e8(const uint64_t x[8],unsigned m,const uint64_t p[8],uint64_t o[8]){return apply_dp(x,m,p,o,1);}
int phi_host_sinf_e16(const uint32_t x[16],unsigned m,const uint32_t p[16],uint32_t o[16]){return apply_sp(x,m,p,o,0);}
int phi_host_cosf_e16(const uint32_t x[16],unsigned m,const uint32_t p[16],uint32_t o[16]){return apply_sp(x,m,p,o,1);}
