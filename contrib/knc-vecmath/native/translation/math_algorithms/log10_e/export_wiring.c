#include "log10_e.h"
#include "knc_mvec_abi.h"
#include <fenv.h>
#include <immintrin.h>
#include <stdio.h>
#include <string.h>
int main(void) {
  if(fegetround()!=FE_TONEAREST||(_mm_getcsr()&0xffc0)!=0x1f80)return 2;
  unsigned calls=0,lanes=0;uint64_t random=UINT64_C(0x4c4f473130);
  const uint64_t dp[]={0,UINT64_C(0x8000000000000000),1,UINT64_C(0x0010000000000000),UINT64_C(0x3ff0000000000000),UINT64_C(0xbff0000000000000),UINT64_C(0x7ff0000000000000),UINT64_C(0x7ff0000000000001)};
  const uint32_t sp[]={0,0x80000000u,1,0x00800000u,0x3f800000u,0xbf800000u,0x7f800000u,0x7f800001u};
  for(unsigned batch=0;batch<64;++batch) {
    uint32_t sx[16],se[16],sg[16];uint64_t dx[8],de[8],dg[8];
    for(unsigned i=0;i<16;++i){random=random*UINT64_C(6364136223846793005)+1;sx[i]=batch<8?sp[(batch+i)%8]:(uint32_t)random&0x7f7fffffu;if(i<8)dx[i]=batch<8?dp[(batch+i)%8]:random&UINT64_C(0x7fefffffffffffff);}
    for(unsigned narrow=0;narrow<2;++narrow) {
      unsigned width=narrow?4:16;feclearexcept(FE_ALL_EXCEPT);_mm_setcsr(_mm_getcsr()&~63u);
      if(phi_host_log10f_e16(sx,(1u<<width)-1,sx,se))return 3;int ef=fetestexcept(FE_ALL_EXCEPT);unsigned ec=_mm_getcsr();feclearexcept(FE_ALL_EXCEPT);_mm_setcsr(_mm_getcsr()&~63u);
      if(narrow){knc_mvec_f32x4 a;memcpy(&a,sx,16);const knc_mvec_f32x4 r=__knc_vmath_log10f_4(a);memcpy(sg,&r,16);}else{knc_mvec_f32x16 a;memcpy(&a,sx,64);const knc_mvec_f32x16 r=__knc_vmath_log10f_16(a);memcpy(sg,&r,64);}
      if(ef!=fetestexcept(FE_ALL_EXCEPT)||ec!=_mm_getcsr()||memcmp(sg,se,width*4))return 4;calls++;lanes+=width;
      width=narrow?2:8;feclearexcept(FE_ALL_EXCEPT);_mm_setcsr(_mm_getcsr()&~63u);
      if(phi_host_log10_e8(dx,(1u<<width)-1,dx,de))return 3;ef=fetestexcept(FE_ALL_EXCEPT);ec=_mm_getcsr();feclearexcept(FE_ALL_EXCEPT);_mm_setcsr(_mm_getcsr()&~63u);
      if(narrow){knc_mvec_f64x2 a;memcpy(&a,dx,16);const knc_mvec_f64x2 r=__knc_vmath_log10_2(a);memcpy(dg,&r,16);}else{knc_mvec_f64x8 a;memcpy(&a,dx,64);const knc_mvec_f64x8 r=__knc_vmath_log10_8(a);memcpy(dg,&r,64);}
      if(ef!=fetestexcept(FE_ALL_EXCEPT)||ec!=_mm_getcsr()||memcmp(dg,de,width*8))return 4;calls++;lanes+=width;
    }
  }
  printf("LOG10_SOURCE_WIRING calls=%u lanes=%u bitFlagMxcsrMismatches=0\n",calls,lanes);return 0;
}
