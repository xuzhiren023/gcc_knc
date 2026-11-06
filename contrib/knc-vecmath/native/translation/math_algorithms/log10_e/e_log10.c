/* Eight-DP GCC-vector adaptation of musl v1.2.5 log10.c (Sun/FreeBSD origin).
 * ====================================================
 * Copyright(C)1993 by Sun Microsystems, Inc. All rights reserved.
 * Developed at SunSoft, a Sun Microsystems, Inc. business.
 * Permission to use, copy, modify, and distribute this software is freely
 * granted, provided that this notice is preserved.
 * ====================================================
 * Changes:8 GCC-vector lanes, integer domain classification, inactive-lane
 * sanitization and private pointer ABI. Preserve split log/scaling and
 * compensated exponent addition. No scalar log10/log delegation.
 * Host research only; not a target numerical/ABI qualification. */
#include "log10_e.h"
#include <string.h>
#ifdef __FAST_MATH__
#error "log10_e8 requires strict FP"
#endif
typedef double dv __attribute__((vector_size(64)));
typedef uint64_t uv __attribute__((vector_size(64)));
static __attribute__((noinline)) void core(const uint64_t input[8],uint64_t output[8]) {
  uint64_t active[8],norm[8],invalid_input[8]={0};int shifts[8]={0};
  unsigned zero=0,invalid=0,inf=0,one=0,sub=0;
  for(unsigned i=0;i<8;++i) {
    uint64_t bits=input[i],mag=bits&UINT64_C(0x7fffffffffffffff);active[i]=bits;norm[i]=UINT64_C(0x3ff0000000000000);
    if(!mag){zero|=1u<<i;active[i]=UINT64_C(0x3ff0000000000000);}
    else if(mag>UINT64_C(0x7ff0000000000000)||(bits>>63)){invalid|=1u<<i;invalid_input[i]=bits;active[i]=UINT64_C(0x3ff0000000000000);}
    else if(bits==UINT64_C(0x7ff0000000000000)){inf|=1u<<i;active[i]=UINT64_C(0x3ff0000000000000);}
    else if(bits==UINT64_C(0x3ff0000000000000))one|=1u<<i;
    else if(bits<UINT64_C(0x0010000000000000)){sub|=1u<<i;norm[i]=bits;shifts[i]=-54;}
  }
  if(sub){dv a;memcpy(&a,norm,64);a*=0x1p54;uint64_t scaled[8];memcpy(scaled,&a,64);for(unsigned i=0;i<8;++i)if(sub&(1u<<i))active[i]=scaled[i];}
  dv x,k;
  for(unsigned i=0;i<8;++i) {
    uint32_t hx=(uint32_t)(active[i]>>32);hx+=0x3ff00000u-0x3fe6a09eu;
    k[i]=(double)(shifts[i]+(int)(hx>>20)-1023);
    uint64_t bits=((uint64_t)((hx&0xfffffu)+0x3fe6a09eu)<<32)|(active[i]&UINT64_C(0xffffffff));memcpy(&x[i],&bits,8);
  }
  const dv f=x-1,hfsq=.5*f*f,s=f/(2+f),z=s*s,w=z*z;
  const dv t1=w*(3.999999999940941908e-01+w*(2.222219843214978396e-01+w*1.531383769920937332e-01));
  const dv t2=z*(6.666666666666735130e-01+w*(2.857142874366239149e-01+w*(1.818357216161805012e-01+w*1.479819860511658591e-01)));
  const dv r=t2+t1;dv hi=f-hfsq;uv hb;memcpy(&hb,&hi,64);hb&=UINT64_C(0xffffffff00000000);memcpy(&hi,&hb,64);
  const dv lo=f-hi-hfsq+s*(hfsq+r);
  dv val_hi=hi*4.34294481878168880939e-01;
  const dv y=k*3.01029995663611771306e-01;
  dv val_lo=k*3.69423907715893078616e-13+(lo+hi)*2.50829467116452752298e-11+lo*4.34294481878168880939e-01;
  const dv sum=y+val_hi;val_lo+=(y-sum)+val_hi;val_hi=sum;
  const dv result=val_lo+val_hi;memcpy(output,&result,64);
  if(invalid) {
    dv a;memcpy(&a,invalid_input,64);const dv difference=a-a;uint64_t bits[8];memcpy(bits,&difference,64);
    for(unsigned i=0;i<8;++i)if(!(invalid&(1u<<i)))bits[i]=UINT64_C(0x3ff0000000000000);
    dv denominator;memcpy(&denominator,bits,64);const dv value=difference/denominator;memcpy(bits,&value,64);
    for(unsigned i=0;i<8;++i)if(invalid&(1u<<i))output[i]=bits[i];
  }
  if(zero) {
    volatile double minus_one=-1;dv a=(dv){0}+1,b=(dv){0}+1;
    for(unsigned i=0;i<8;++i)if(zero&(1u<<i)){a[i]=minus_one;b[i]=0;}
    const dv value=a/b;uint64_t bits[8];memcpy(bits,&value,64);for(unsigned i=0;i<8;++i)if(zero&(1u<<i))output[i]=bits[i];
  }
  for(unsigned i=0;i<8;++i){if(inf&(1u<<i))output[i]=UINT64_C(0x7ff0000000000000);if(one&(1u<<i))output[i]=0;}
}
int phi_host_log10_e8(const uint64_t input[8],unsigned mask,const uint64_t merge[8],uint64_t output[8]) {
  if(mask&~255u)return 1;uint64_t saved[8],pass[8],out[8];memcpy(saved,input,64);memcpy(pass,merge,64);
  if(!mask){memcpy(output,pass,64);return 0;}
  for(unsigned i=0;i<8;++i)if(!(mask&(1u<<i)))saved[i]=UINT64_C(0x3ff0000000000000);
  core(saved,out);for(unsigned i=0;i<8;++i)if(!(mask&(1u<<i)))out[i]=pass[i];memcpy(output,out,64);return 0;
}
