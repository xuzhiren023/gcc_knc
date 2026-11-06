/* Compact new-family wiring check; pointer algorithm accuracy is separate. */
#include "powf_e16.h"
#include "knc_mvec_abi.h"
#include <fenv.h>
#include <immintrin.h>
#include <stdio.h>
#include <string.h>
static unsigned next(unsigned *state){*state=*state*1664525u+1013904223u;return *state;}
int main(void) {
  if(fegetround()!=FE_TONEAREST||(_mm_getcsr()&0xffc0)!=0x1f80)return 2;
  unsigned random=0x706f7766,calls=0,lanes=0;
  const unsigned special[]={0,0x80000000,1,0x80000001,0x00800000,0x3f000000,
    0xbf000000,0x3f800000,0xbf800000,0x40000000,0xc0000000,0x7f7fffff,
    0x7f800000,0xff800000,0x7fc12345,0x7f812345};
  for(unsigned batch=0;batch<64;++batch) {
    unsigned x[16],y[16],expected[16],got[16];
    for(unsigned i=0;i<16;++i) {
      x[i]=batch<16?special[(batch+i)%16]:(next(&random)&0x7f7fffffu);
      y[i]=batch<16?special[(batch*3+i*5)%16]:0x3f000000u+((next(&random)>>9)&0x7fffffu);
    }
    for(unsigned width=4;width<=16;width*=2) {
      unsigned mask=(1u<<width)-1;
      feclearexcept(FE_ALL_EXCEPT);_mm_setcsr(_mm_getcsr()&~63u);
      if(phi_host_powf_e16(x,y,mask,x,expected))return 3;
      const int expected_flags=fetestexcept(FE_ALL_EXCEPT);const unsigned expected_csr=_mm_getcsr();
      feclearexcept(FE_ALL_EXCEPT);_mm_setcsr(_mm_getcsr()&~63u);
      if(width==4) {
        knc_mvec_f32x4 a,b;memcpy(&a,x,16);memcpy(&b,y,16);
        const knc_mvec_f32x4 r=__knc_vmath_powf_4(a,b);memcpy(got,&r,16);
      } else if(width==8) {
        knc_mvec_f32x8 a,b;memcpy(&a,x,32);memcpy(&b,y,32);
        const knc_mvec_f32x8 r=__knc_vmath_powf_8(a,b);memcpy(got,&r,32);
      } else {
        knc_mvec_f32x16 a,b;memcpy(&a,x,64);memcpy(&b,y,64);
        const knc_mvec_f32x16 r=__knc_vmath_powf_16(a,b);memcpy(got,&r,64);
      }
      const int actual_flags=fetestexcept(FE_ALL_EXCEPT);const unsigned actual_csr=_mm_getcsr();
      if(actual_flags!=expected_flags||actual_csr!=expected_csr||memcmp(got,expected,width*4))return 4;
      calls++;lanes+=width;
    }
  }
  printf("POWF_SOURCE_WIRING calls=%u lanes=%u bitFlagMxcsrMismatches=0\n",calls,lanes);return 0;
}
