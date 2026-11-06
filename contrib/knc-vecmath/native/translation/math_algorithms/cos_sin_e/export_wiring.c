/* Source wiring against the independently MPFR-sampled pointer algorithms. */
#include "cos_sin_e.h"
#include "knc_mvec_abi.h"
#include <fenv.h>
#include <immintrin.h>
#include <stdio.h>
#include <string.h>
static void clear(void){feclearexcept(FE_ALL_EXCEPT);_mm_setcsr(_mm_getcsr()&~63u);}
int main(void) {
  if(fegetround()!=FE_TONEAREST||(_mm_getcsr()&0xffc0)!=0x1f80)return 2;
  unsigned calls=0,lanes=0,inactive=0;uint64_t random=UINT64_C(0x5452494757495245);
  const uint64_t dp[]={0,UINT64_C(0x8000000000000000),1,UINT64_C(0x0010000000000000),UINT64_C(0x3ff0000000000000),UINT64_C(0xbff0000000000000),UINT64_C(0x3ff921fb54442d18),UINT64_C(0x413921fb54442d18),UINT64_C(0x7fefffffffffffff),UINT64_C(0xffefffffffffffff),UINT64_C(0x7ff0000000000000),UINT64_C(0xfff0000000000000),UINT64_C(0x7ff0000000000001),UINT64_C(0xfff8000000000023),UINT64_C(0x3fe921fb54442d18),UINT64_C(0x3e40000000000000)};
  const uint32_t sp[]={0,0x80000000u,1,0x00800000u,0x3f800000u,0xbf800000u,0x3fc90fdbu,0x49c90fdbu,0x7f7fffffu,0xff7fffffu,0x7f800000u,0xff800000u,0x7f800001u,0xffc00023u,0x3f490fdbu,0x32000000u};
  for(unsigned batch=0;batch<64;++batch) {
    uint32_t sx[16],se[16],sg[16];uint64_t dx[8],de[8],dg[8];
    for(unsigned i=0;i<16;++i){random=random*UINT64_C(6364136223846793005)+1;sx[i]=batch<16?sp[(batch+i)%16]:(uint32_t)random&0xff7fffffu;if(i<8)dx[i]=batch<16?dp[(batch+i)%16]:random&UINT64_C(0xffefffffffffffff);}
    for(unsigned cosine=0;cosine<2;++cosine) {
      clear();if((cosine?phi_host_cosf_e16:phi_host_sinf_e16)(sx,65535u,sx,se))return 3;
      int ef=fetestexcept(FE_ALL_EXCEPT);unsigned ec=_mm_getcsr();clear();
      knc_mvec_f32x16 sa;memcpy(&sa,sx,64);const knc_mvec_f32x16 sr=cosine?__knc_vmath_cosf_16(sa):__knc_vmath_sinf_16(sa);memcpy(sg,&sr,64);
      if(ef!=fetestexcept(FE_ALL_EXCEPT)||ec!=_mm_getcsr()||memcmp(sg,se,64))return 4;calls++;lanes+=16;
      clear();if((cosine?phi_host_cos_e8:phi_host_sin_e8)(dx,255u,dx,de))return 3;
      ef=fetestexcept(FE_ALL_EXCEPT);ec=_mm_getcsr();clear();
      knc_mvec_f64x8 da;memcpy(&da,dx,64);const knc_mvec_f64x8 dr=cosine?__knc_vmath_cos_8(da):__knc_vmath_sin_8(da);memcpy(dg,&dr,64);
      if(ef!=fetestexcept(FE_ALL_EXCEPT)||ec!=_mm_getcsr()||memcmp(dg,de,64))return 4;calls++;lanes+=8;
    }
    /* The independently sampled pointer boundary gets readable poison in the
     * six inactive lanes; the wrapper must supply exact neutral zeros. */
    for(unsigned i=2;i<8;++i)dx[i]=UINT64_C(0x7ff0000000000001);
    if(!(batch%8)){dx[0]=0;dx[1]=UINT64_C(0x8000000000000000);}
    clear();if(phi_host_cos_e8(dx,3,dx,de))return 3;int ef=fetestexcept(FE_ALL_EXCEPT);unsigned ec=_mm_getcsr();
    if(!(batch%8)&&(ef||(ec&63)||de[0]!=UINT64_C(0x3ff0000000000000)||de[1]!=UINT64_C(0x3ff0000000000000)))return 5;
    clear();knc_mvec_f64x2 a;memcpy(&a,dx,16);const knc_mvec_f64x2 r=__knc_vmath_cos_2(a);memcpy(dg,&r,16);
    if(ef!=fetestexcept(FE_ALL_EXCEPT)||ec!=_mm_getcsr()||memcmp(dg,de,16))return 4;calls++;lanes+=2;inactive+=6;
  }
  printf("TRIG_SOURCE_WIRING calls=%u lanes=%u inactivePoisonLanes=%u bitFlagMxcsrMismatches=0\n",calls,lanes,inactive);return 0;
}
