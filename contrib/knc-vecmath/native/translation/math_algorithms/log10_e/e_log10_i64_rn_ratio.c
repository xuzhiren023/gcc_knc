/* Additive RN-only exact bounded-ratio/integer-storage log10 candidate.
 * Earlier host source/status evidence does not qualify this target variant. */
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
#include "log10_i64_rn_ratio.h"
#include <string.h>
#ifdef __FAST_MATH__
#error "log10_e8 requires strict FP"
#endif
typedef double dv __attribute__((vector_size(64)));
typedef uint64_t uv __attribute__((vector_size(64)));
/* RN-only bounded quotient for the log10 reduction. The caller constructs
 * f=x-1 and d=2+f after x's bits are normalized into the exact interval
 * [0x3fe6a09e00000000,0x3ff6a09dffffffff], contained in [0.7,1.5].
 * Nonzero f has magnitude >=2^-53; d is normal and lies in [1.7,2.5].
 * Thus the quotient is signed zero or normal binary64, never subnormal.
 * No generic VDIVPD, directed-rounding, flag, or performance claim is made.
 * All significands/remainders fit in uint64_t: normalized remainder < 2^53,
 * shifted remainder < 2^54. Exactly 52 quotient bits plus exact remainder
 * determine round-to-nearest/ties-even without a floating-point operation. */
static __attribute__((noinline)) uint64_t pw_log10_rn_ratio_i64(uint64_t f,uint64_t d) {
  const uint64_t fraction=UINT64_C(0x000fffffffffffff);
  const uint64_t sign=f&UINT64_C(0x8000000000000000);
  if(!(f&UINT64_C(0x7fffffffffffffff)))return sign;
  uint64_t ma=(f&fraction)|UINT64_C(0x0010000000000000);
  const uint64_t mb=(d&fraction)|UINT64_C(0x0010000000000000);
  int exponent=(int)((f>>52)&2047u)-(int)((d>>52)&2047u);
  if(ma<mb){ma<<=1;--exponent;}
  uint64_t remainder=ma-mb,quotient=1;
  for(unsigned bit=0;bit<52;++bit) {
    remainder<<=1;quotient<<=1;
    if(remainder>=mb){remainder-=mb;quotient|=1;}
  }
  uint64_t twice=remainder<<1;
  if(twice>mb||(twice==mb&&(quotient&1)))++quotient;
  if(quotient==UINT64_C(0x0020000000000000)){quotient>>=1;++exponent;}
  return sign|((uint64_t)(exponent+1023)<<52)|(quotient&fraction);
}
/* Only exact constants 0/-1 divided by +0 use the qualified scalar SP
 * event mechanism. Conversion of its quiet NaN/infinity to DP is exact.
 * qNaN inputs are classified with integer bits and do not raise invalid. */
static __attribute__((noinline)) uint64_t pw_log10_special_event_i64(unsigned zero) {
  volatile float numerator=0.0f,denominator=0.0f;
  if(zero)numerator=-1.0f;
  volatile float quotient=numerator/denominator;
  const double value=(double)quotient;uint64_t bits;memcpy(&bits,&value,8);return bits;
}
static __attribute__((noinline)) void core(const uint64_t input[8],uint64_t output[8]) {
  uint64_t active[8],norm[8],invalid_input[8]={0};int64_t shifts[8]={0};
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
  dv x,k;uint64_t normalized[8];
  const volatile uint64_t *active_words=active;
  const volatile int64_t *shift_words=shifts;
  for(unsigned i=0;i<8;++i) {
    uint64_t hx=active_words[i]>>32;hx+=UINT64_C(0x3ff00000)-UINT64_C(0x3fe6a09e);
    k[i]=(double)(shift_words[i]+(int64_t)(hx>>20)-1023);
    normalized[i]=(((hx&UINT64_C(0xfffff))+UINT64_C(0x3fe6a09e))<<32)|(active_words[i]&UINT64_C(0xffffffff));
  }
  memcpy(&x,normalized,64);
  const dv f=x-1,hfsq=.5*f*f,denominator=2+f;
  uint64_t numerator_bits[8],denominator_bits[8],quotient_bits[8];
  memcpy(numerator_bits,&f,64);memcpy(denominator_bits,&denominator,64);
  const volatile uint64_t *numerator_words=numerator_bits,*denominator_words=denominator_bits;
  for(unsigned i=0;i<8;++i)quotient_bits[i]=pw_log10_rn_ratio_i64(numerator_words[i],denominator_words[i]);
  dv s;memcpy(&s,quotient_bits,64);
  const dv z=s*s,w=z*z;
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
    for(unsigned i=0;i<8;++i)if(invalid&(1u<<i)) {
      uint64_t bits=invalid_input[i],mag=bits&UINT64_C(0x7fffffffffffffff);
      if(mag>UINT64_C(0x7ff0000000000000)) {
        if(!(bits&UINT64_C(0x0008000000000000)))(void)pw_log10_special_event_i64(0);
        output[i]=bits|UINT64_C(0x0008000000000000);
      } else output[i]=pw_log10_special_event_i64(0);
    }
  }
  if(zero)for(unsigned i=0;i<8;++i)if(zero&(1u<<i))output[i]=pw_log10_special_event_i64(1);
  for(unsigned i=0;i<8;++i){if(inf&(1u<<i))output[i]=UINT64_C(0x7ff0000000000000);if(one&(1u<<i))output[i]=0;}
}
int phi_host_log10_i64_rn_ratio_e8(const uint64_t input[8],unsigned mask,const uint64_t merge[8],uint64_t output[8]) {
  if(mask&~255u)return 1;uint64_t saved[8],pass[8],out[8];memcpy(saved,input,64);memcpy(pass,merge,64);
  if(!mask){memcpy(output,pass,64);return 0;}
  for(unsigned i=0;i<8;++i)if(!(mask&(1u<<i)))saved[i]=UINT64_C(0x3ff0000000000000);
  core(saved,out);for(unsigned i=0;i<8;++i)if(!(mask&(1u<<i)))out[i]=pass[i];memcpy(output,out,64);return 0;
}
