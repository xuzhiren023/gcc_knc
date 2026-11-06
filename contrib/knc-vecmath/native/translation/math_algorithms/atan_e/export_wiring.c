#include "atan_e.h"
#include "knc_mvec_abi.h"
#include <fenv.h>
#include <immintrin.h>
#include <stdio.h>
#include <string.h>
int knc_mvec_algorithm_atanf_e16(const uint32_t*,unsigned,const uint32_t*,uint32_t*);
int knc_mvec_algorithm_atan2f_e16(const uint32_t*,const uint32_t*,unsigned,const uint32_t*,uint32_t*);
int knc_mvec_algorithm_atan2_e8(const uint64_t*,const uint64_t*,unsigned,const uint64_t*,uint64_t*);
static void clear(void){feclearexcept(FE_ALL_EXCEPT);_mm_setcsr(_mm_getcsr()&~63u);}
int main(void){
  if(fegetround()!=FE_TONEAREST||(_mm_getcsr()&0xffc0)!=0x1f80)return 2;
  unsigned calls=0,lanes=0,masked=0,inactive=0;uint64_t random=UINT64_C(0x4154414e57495245);
  const uint64_t dp[]={0,UINT64_C(0x8000000000000000),1,UINT64_C(0x0010000000000000),UINT64_C(0x3ff0000000000000),UINT64_C(0xbff0000000000000),UINT64_C(0x3fe6000000000000),UINT64_C(0x4003800000000000),UINT64_C(0x7fefffffffffffff),UINT64_C(0xffefffffffffffff),UINT64_C(0x7ff0000000000000),UINT64_C(0xfff0000000000000),UINT64_C(0x7ff0000000000001),UINT64_C(0xfff8000000000023),UINT64_C(0x3fdc000000000000),UINT64_C(0x4410000000000000)};
  const uint32_t sp[]={0,0x80000000u,1,0x00800000u,0x3f800000u,0xbf800000u,0x3f300000u,0x401c0000u,0x7f7fffffu,0xff7fffffu,0x7f800000u,0xff800000u,0x7f800001u,0xffc00023u,0x3ee00000u,0x60800000u};
  for(unsigned batch=0;batch<64;++batch){uint32_t sy[16],sx[16],sm[16],se[16],sg[16];uint64_t dy[8],dx[8],dm[8],de[8],dg[8];
    for(unsigned i=0;i<16;++i){random=random*UINT64_C(6364136223846793005)+1;sy[i]=batch<32?sp[(batch+i)%16]:(uint32_t)random&0xff7fffffu;sm[i]=(uint32_t)random;if(i<8){dy[i]=batch<32?dp[(batch+i)%16]:random&UINT64_C(0xffefffffffffffff);dm[i]=random;}random=random*UINT64_C(6364136223846793005)+1;sx[i]=batch<32?sp[(batch*3+i*5)%16]:(uint32_t)random&0xff7fffffu;if(i<8)dx[i]=batch<32?dp[(batch*3+i*5)%16]:random&UINT64_C(0xffefffffffffffff);}
    clear();if(phi_host_atanf_e16(sy,65535u,sm,se))return 3;int ef=fetestexcept(FE_ALL_EXCEPT);unsigned ec=_mm_getcsr();clear();knc_mvec_f32x16 a,b;memcpy(&a,sy,64);memcpy(&b,sx,64);const knc_mvec_f32x16 ar=__knc_vmath_atanf_16(a);memcpy(sg,&ar,64);if(ef!=fetestexcept(FE_ALL_EXCEPT)||ec!=_mm_getcsr()||memcmp(sg,se,64))return 4;calls++;lanes+=16;
    clear();if(phi_host_atan2f_e16(sy,sx,65535u,sm,se))return 3;ef=fetestexcept(FE_ALL_EXCEPT);ec=_mm_getcsr();clear();const knc_mvec_f32x16 br=__knc_vmath_atan2f_16(a,b);memcpy(sg,&br,64);if(ef!=fetestexcept(FE_ALL_EXCEPT)||ec!=_mm_getcsr()||memcmp(sg,se,64))return 4;calls++;lanes+=16;
    clear();if(phi_host_atan2_e8(dy,dx,255u,dm,de))return 3;ef=fetestexcept(FE_ALL_EXCEPT);ec=_mm_getcsr();clear();knc_mvec_f64x8 c,d;memcpy(&c,dy,64);memcpy(&d,dx,64);const knc_mvec_f64x8 cr=__knc_vmath_atan2_8(c,d);memcpy(dg,&cr,64);if(ef!=fetestexcept(FE_ALL_EXCEPT)||ec!=_mm_getcsr()||memcmp(dg,de,64))return 4;calls++;lanes+=8;
    unsigned mask=batch&1?0xaaaau:0x5555u;for(unsigned i=0;i<16;++i){sy[i]=mask&(1u<<i)?(i&1?0x80000000u:0):0x7f800001u;sx[i]=mask&(1u<<i)?0x3f800000u:0x7f800001u;}
    clear();if(phi_host_atanf_e16(sy,mask,sm,se))return 3;ef=fetestexcept(FE_ALL_EXCEPT);ec=_mm_getcsr();clear();if(knc_mvec_algorithm_atanf_e16(sy,mask,sm,sg)||ef||fetestexcept(FE_ALL_EXCEPT)||ec!=_mm_getcsr()||ec&63||memcmp(sg,se,64))return 5;masked++;inactive+=8;
    clear();if(phi_host_atan2f_e16(sy,sx,mask,sm,se))return 3;ef=fetestexcept(FE_ALL_EXCEPT);ec=_mm_getcsr();clear();if(knc_mvec_algorithm_atan2f_e16(sy,sx,mask,sm,sg)||ef||fetestexcept(FE_ALL_EXCEPT)||ec!=_mm_getcsr()||ec&63||memcmp(sg,se,64))return 5;masked++;inactive+=8;
    mask&=255u;for(unsigned i=0;i<8;++i){dy[i]=mask&(1u<<i)?(i&1?UINT64_C(0x8000000000000000):0):UINT64_C(0x7ff0000000000001);dx[i]=mask&(1u<<i)?UINT64_C(0x3ff0000000000000):UINT64_C(0x7ff0000000000001);}
    clear();if(phi_host_atan2_e8(dy,dx,mask,dm,de))return 3;ef=fetestexcept(FE_ALL_EXCEPT);ec=_mm_getcsr();clear();if(knc_mvec_algorithm_atan2_e8(dy,dx,mask,dm,dg)||ef||fetestexcept(FE_ALL_EXCEPT)||ec!=_mm_getcsr()||ec&63||memcmp(dg,de,64))return 5;masked++;inactive+=4;
  }
  printf("ATAN_SOURCE_WIRING calls=%u lanes=%u privateMaskCalls=%u inactivePoisonLanes=%u bitFlagMxcsrMismatches=0\n",calls,lanes,masked,inactive);return 0;
}
