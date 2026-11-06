#include "tan_e.h"
#include "knc_mvec_abi.h"
#include <fenv.h>
#include <immintrin.h>
#include <stdio.h>
#include <string.h>
int knc_mvec_algorithm_tan_e8(const uint64_t *,unsigned,const uint64_t *,uint64_t *);
int knc_mvec_algorithm_tanf_e16(const uint32_t *,unsigned,const uint32_t *,uint32_t *);
static void clear(void){feclearexcept(FE_ALL_EXCEPT);_mm_setcsr(_mm_getcsr()&~63u);}
int main(void) {
  if(fegetround()!=FE_TONEAREST||(_mm_getcsr()&0xffc0)!=0x1f80)return 2;
  unsigned calls=0,lanes=0,masked=0,inactive=0;uint64_t random=UINT64_C(0x54414e57495245);
  const uint64_t dp[]={0,UINT64_C(0x8000000000000000),1,UINT64_C(0x0010000000000000),UINT64_C(0x3ff0000000000000),UINT64_C(0xbff0000000000000),UINT64_C(0x3ff921fb54442d18),UINT64_C(0x3ff921fb54442d19),UINT64_C(0x7fefffffffffffff),UINT64_C(0xffefffffffffffff),UINT64_C(0x7ff0000000000000),UINT64_C(0xfff0000000000000),UINT64_C(0x7ff0000000000001),UINT64_C(0xfff8000000000023),UINT64_C(0x3fe921fb54442d18),UINT64_C(0x3fe5942800000000)};
  const uint32_t sp[]={0,0x80000000u,1,0x00800000u,0x3f800000u,0xbf800000u,0x3fc90fdbu,0x3fc90fdcu,0x7f7fffffu,0xff7fffffu,0x7f800000u,0xff800000u,0x7f800001u,0xffc00023u,0x3f490fdbu,0x3f2ca140u};
  for(unsigned batch=0;batch<64;++batch) {
    uint32_t sx[16],se[16],sg[16],sm[16];uint64_t dx[8],de[8],dg[8],dm[8];
    for(unsigned i=0;i<16;++i){random=random*UINT64_C(6364136223846793005)+1;sx[i]=batch<16?sp[(batch+i)%16]:(uint32_t)random&0xff7fffffu;sm[i]=(uint32_t)random;if(i<8){dx[i]=batch<16?dp[(batch+i)%16]:random&UINT64_C(0xffefffffffffffff);dm[i]=random;}}
    clear();if(phi_host_tanf_e16(sx,65535u,sx,se))return 3;int ef=fetestexcept(FE_ALL_EXCEPT);unsigned ec=_mm_getcsr();clear();
    knc_mvec_f32x16 sa;memcpy(&sa,sx,64);const knc_mvec_f32x16 sr=__knc_vmath_tanf_16(sa);memcpy(sg,&sr,64);
    if(ef!=fetestexcept(FE_ALL_EXCEPT)||ec!=_mm_getcsr()||memcmp(sg,se,64))return 4;calls++;lanes+=16;
    clear();if(phi_host_tan_e8(dx,255u,dx,de))return 3;ef=fetestexcept(FE_ALL_EXCEPT);ec=_mm_getcsr();clear();
    knc_mvec_f64x8 da;memcpy(&da,dx,64);const knc_mvec_f64x8 dr=__knc_vmath_tan_8(da);memcpy(dg,&dr,64);
    if(ef!=fetestexcept(FE_ALL_EXCEPT)||ec!=_mm_getcsr()||memcmp(dg,de,64))return 4;calls++;lanes+=8;
    unsigned mask=batch&1?0xaaaau:0x5555u;
    for(unsigned i=0;i<16;++i)sx[i]=mask&(1u<<i)?(i&1?0x80000000u:0):i&1?0x7f800001u:0x7f800000u;
    clear();if(phi_host_tanf_e16(sx,mask,sm,se))return 3;ef=fetestexcept(FE_ALL_EXCEPT);ec=_mm_getcsr();clear();
    if(knc_mvec_algorithm_tanf_e16(sx,mask,sm,sg)||ef||fetestexcept(FE_ALL_EXCEPT)||ec!=_mm_getcsr()||ec&63||memcmp(sg,se,64))return 5;masked++;inactive+=8;
    mask&=255u;for(unsigned i=0;i<8;++i)dx[i]=mask&(1u<<i)?(i&1?UINT64_C(0x8000000000000000):0):i&1?UINT64_C(0x7ff0000000000001):UINT64_C(0x7ff0000000000000);
    clear();if(phi_host_tan_e8(dx,mask,dm,de))return 3;ef=fetestexcept(FE_ALL_EXCEPT);ec=_mm_getcsr();clear();
    if(knc_mvec_algorithm_tan_e8(dx,mask,dm,dg)||ef||fetestexcept(FE_ALL_EXCEPT)||ec!=_mm_getcsr()||ec&63||memcmp(dg,de,64))return 5;masked++;inactive+=4;
  }
  printf("TAN_SOURCE_WIRING calls=%u lanes=%u privateMaskCalls=%u inactivePoisonLanes=%u bitFlagMxcsrMismatches=0\n",calls,lanes,masked,inactive);return 0;
}
