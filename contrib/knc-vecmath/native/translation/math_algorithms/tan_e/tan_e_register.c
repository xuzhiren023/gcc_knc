/* DP8 GCC-vector adaptation of official musl v1.2.5 __tan.c.
 * ====================================================
 * Copyright 2004 Sun Microsystems, Inc. All Rights Reserved.
 * Permission to use, copy, modify, and distribute this software is freely
 * granted, provided that this notice is preserved.
 * ====================================================
 * Changes: eight DP vector lanes, complete-domain per-lane reduction through
 * the unchanged cos_sin_e reducer, sanitized transform/reciprocal lanes and
 * full64-byte private pointer ABI. SP16 uses two DP8 groups, one final rounding.
 * Retain compensated reduced tail, pi/4 transform and reciprocal correction.
 * No scalar tangent/sine/cosine delegation; no target/G5/performance claim. */
#include "tan_e.h"
#include <string.h>
#ifdef __FAST_MATH__
#error "tan_e requires strict FP"
#endif
typedef double dv __attribute__((vector_size(64)));
typedef uint64_t uv __attribute__((vector_size(64)));
typedef float fv __attribute__((vector_size(64)));
int phi_trig_rem_pio2(double,double *);
static uint64_t dbits(double x){uint64_t b;memcpy(&b,&x,8);return b;}
static double dvalue(uint64_t b){double x;memcpy(&x,&b,8);return x;}
static uv tobits(dv x){uv b;memcpy(&b,&x,64);return b;}
static dv frombits(uv b){dv x;memcpy(&x,&b,64);return x;}
static const double T[]={3.33333333333334091986e-01,1.33333333333201242699e-01,5.39682539762260521377e-02,2.18694882948595424599e-02,8.86323982359930005737e-03,3.59207910759131235356e-03,1.45620945432529025516e-03,5.88041240820264096874e-04,2.46463134818469906812e-04,7.81794442939557092300e-05,7.14072491382608190305e-05,-1.85586374855275456654e-05,2.59073051863633712884e-05};
static __attribute__((noinline)) void finite_core(const double input[8],double output[8]) {
  const double pio4=7.85398163397448278999e-01,pio4lo=3.06161699786838301793e-17;
  dv x,y,tx,ty,s;unsigned odd[8],big[8],small[8];uint64_t sign[8];uv bm;
  for(unsigned i=0;i<8;++i) {
    uint64_t mag=dbits(input[i])&UINT64_C(0x7fffffffffffffff);
    small[i]=mag<UINT64_C(0x3e40000000000000);odd[i]=0;x[i]=small[i]?0:input[i];y[i]=0;
    if(mag>UINT64_C(0x3fe921fb54442d18)){double parts[2];odd[i]=(unsigned)phi_trig_rem_pio2(input[i],parts)&1;x[i]=parts[0];y[i]=parts[1];}
    uint64_t xb=dbits(x[i]);big[i]=(xb&UINT64_C(0x7fffffffffffffff))>=UINT64_C(0x3fe5942800000000);
    sign[i]=big[i]?(xb&UINT64_C(0x8000000000000000)):0;
    x[i]=dvalue(xb^sign[i]);y[i]=dvalue(dbits(y[i])^sign[i]);bm[i]=big[i]?UINT64_MAX:0;
    /* Exact neutral subtractions prevent inactive/non-big lanes from raising
     * inexact in an unused pi/4 transformation. */
    tx[i]=big[i]?x[i]:pio4;ty[i]=big[i]?y[i]:pio4lo;s[i]=odd[i]?-1:1;
  }
  const dv transformed=(pio4-tx)+(pio4lo-ty);
  x=frombits((tobits(x)&~bm)|(tobits(transformed)&bm));y=frombits(tobits(y)&~bm);
  const dv z=x*x,w2=z*z;
  dv r=T[1]+w2*(T[3]+w2*(T[5]+w2*(T[7]+w2*(T[9]+w2*T[11]))));
  const dv v=z*(T[2]+w2*(T[4]+w2*(T[6]+w2*(T[8]+w2*(T[10]+w2*T[12]))))),cube=z*x;
  r=y+z*(cube*(r+v)+y)+cube*T[0];const dv w=x+r;
  dv two={2.0,2.0,2.0,2.0,2.0,2.0,2.0,2.0};
  /* Empty register constraint materializes the unchanged coefficient.
   * The opaque full vector cannot fold back into an m64{1to8} FMA. */
  __asm__ __volatile__("" : "+v"(two));
  const dv transformed_result=s-two*(x+(r-w*w/(w+s)));
  const dv w0=frombits(tobits(w)&UINT64_C(0xffffffff00000000));
  const dv tail=r-(w0-x);dv denominator;
  for(unsigned i=0;i<8;++i)denominator[i]=odd[i]&&!big[i]?w[i]:1;
  const dv a=-1/denominator,a0=frombits(tobits(a)&UINT64_C(0xffffffff00000000));
  const dv reciprocal=a0+a*(1+a0*w0+a0*tail);
  for(unsigned i=0;i<8;++i) {
    if(small[i]){output[i]=input[i];continue;}
    output[i]=big[i]?dvalue(dbits(transformed_result[i])^sign[i]):odd[i]?reciprocal[i]:w[i];
  }
}
int phi_host_tan_e8(const uint64_t input[8],unsigned mask,const uint64_t merge[8],uint64_t output[8]) {
  if(mask&~255u)return 1;uint64_t saved[8],pass[8],out[8];double values[8],result[8];unsigned exceptional=0;
  memcpy(saved,input,64);memcpy(pass,merge,64);if(!mask){memcpy(output,pass,64);return 0;}
  for(unsigned i=0;i<8;++i){uint64_t mag=saved[i]&UINT64_C(0x7fffffffffffffff);if((mask&(1u<<i))&&mag>=UINT64_C(0x7ff0000000000000))exceptional|=1u<<i;values[i]=((mask&(1u<<i))&&!(exceptional&(1u<<i)))?dvalue(saved[i]):0;}
  finite_core(values,result);memcpy(out,result,64);
  if(exceptional){dv a={0};for(unsigned i=0;i<8;++i)if(exceptional&(1u<<i))a[i]=dvalue(saved[i]);const dv nan=a-a;uint64_t bits[8];memcpy(bits,&nan,64);for(unsigned i=0;i<8;++i)if(exceptional&(1u<<i))out[i]=bits[i];}
  for(unsigned i=0;i<8;++i)if(!(mask&(1u<<i)))out[i]=pass[i];memcpy(output,out,64);return 0;
}
int phi_host_tanf_e16(const uint32_t input[16],unsigned mask,const uint32_t merge[16],uint32_t output[16]) {
  if(mask&~65535u)return 1;uint32_t saved[16],pass[16],out[16];unsigned exceptional=0;memcpy(saved,input,64);memcpy(pass,merge,64);if(!mask){memcpy(output,pass,64);return 0;}
  for(unsigned group=0;group<2;++group){double values[8],result[8];for(unsigned i=0;i<8;++i){unsigned lane=group*8+i;uint32_t mag=saved[lane]&UINT32_C(0x7fffffff);float x=0;if((mask&(1u<<lane))&&mag>=UINT32_C(0x7f800000))exceptional|=1u<<lane;if((mask&(1u<<lane))&&!(exceptional&(1u<<lane)))memcpy(&x,&saved[lane],4);values[i]=(double)x;}finite_core(values,result);for(unsigned i=0;i<8;++i){float value=(float)result[i];memcpy(&out[group*8+i],&value,4);}}
  if(exceptional){fv a={0};for(unsigned i=0;i<16;++i)if(exceptional&(1u<<i))memcpy(&a[i],&saved[i],4);const fv nan=a-a;uint32_t bits[16];memcpy(bits,&nan,64);for(unsigned i=0;i<16;++i)if(exceptional&(1u<<i))out[i]=bits[i];}
  for(unsigned i=0;i<16;++i)if(!(mask&(1u<<i)))out[i]=pass[i];memcpy(output,out,64);return 0;
}
