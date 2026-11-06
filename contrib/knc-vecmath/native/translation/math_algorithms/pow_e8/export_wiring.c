/* Compact DP source-boundary check. Independent MPFR accuracy is separate. */
#include "pow_e8.h"
#include "knc_mvec_abi.h"
#include <fenv.h>
#include <immintrin.h>
#include <stdio.h>
#include <string.h>
static uint64_t next(uint64_t *s){*s=*s*UINT64_C(6364136223846793005)+UINT64_C(1442695040888963407);return *s;}
int main(void) {
  if(fegetround()!=FE_TONEAREST||(_mm_getcsr()&0xffc0)!=0x1f80)return 2;
  uint64_t random=UINT64_C(0x706f776438);unsigned calls=0,lanes=0;
  const uint64_t special[]={0,UINT64_C(0x8000000000000000),1,UINT64_C(0x8000000000000001),
    UINT64_C(0x0010000000000000),UINT64_C(0x3fe0000000000000),UINT64_C(0xbfe0000000000000),
    UINT64_C(0x3ff0000000000000),UINT64_C(0xbff0000000000000),UINT64_C(0x4000000000000000),
    UINT64_C(0xc000000000000000),UINT64_C(0x7fefffffffffffff),UINT64_C(0x7ff0000000000000),
    UINT64_C(0xfff0000000000000),UINT64_C(0x7ff8123456789abc),UINT64_C(0x7ff0123456789abc)};
  for(unsigned batch=0;batch<64;++batch) {
    uint64_t x[8],y[8],expected[8],got[8];
    for(unsigned i=0;i<8;++i){x[i]=batch<16?special[(batch+i)%16]:next(&random)&UINT64_C(0x7fefffffffffffff);y[i]=batch<16?special[(batch*3+i*5)%16]:UINT64_C(0x3fe0000000000000)+(next(&random)&UINT64_C(0x000fffffffffffff));}
    for(unsigned width=2;width<=8;width*=2) {
      feclearexcept(FE_ALL_EXCEPT);_mm_setcsr(_mm_getcsr()&~63u);
      if(phi_host_pow_e8(x,y,(1u<<width)-1,x,expected))return 3;
      const int ef=fetestexcept(FE_ALL_EXCEPT);const unsigned ec=_mm_getcsr();
      feclearexcept(FE_ALL_EXCEPT);_mm_setcsr(_mm_getcsr()&~63u);
      if(width==2){knc_mvec_f64x2 a,b;memcpy(&a,x,16);memcpy(&b,y,16);const knc_mvec_f64x2 r=__knc_vmath_pow_2(a,b);memcpy(got,&r,16);}
      else if(width==4){knc_mvec_f64x4 a,b;memcpy(&a,x,32);memcpy(&b,y,32);const knc_mvec_f64x4 r=__knc_vmath_pow_4(a,b);memcpy(got,&r,32);}
      else{knc_mvec_f64x8 a,b;memcpy(&a,x,64);memcpy(&b,y,64);const knc_mvec_f64x8 r=__knc_vmath_pow_8(a,b);memcpy(got,&r,64);}
      const int af=fetestexcept(FE_ALL_EXCEPT);const unsigned ac=_mm_getcsr();
      if(af!=ef||ac!=ec||memcmp(got,expected,width*8))return 4;calls++;lanes+=width;
    }
  }
  printf("POW_SOURCE_WIRING calls=%u lanes=%u bitFlagMxcsrMismatches=0\n",calls,lanes);return 0;
}
