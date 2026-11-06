/* Independent binary-power interval oracle. No candidate coefficients, source
 * equations or libm pow are imported. MPFR correctly rounded pow is evaluated
 * down/up at256 and384 bits; both endpoint pairs must round to the same float.
 * Raw packets/aliases/masks are validated independently before comparisons. */
#include <mpfr.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <fenv.h>
static uint32_t word(float x){uint32_t b;memcpy(&b,&x,4);return b;}
static float value(uint32_t x){float b;memcpy(&b,&x,4);return b;}
static int isnanbits(uint32_t x){return (x&0x7fffffffu)>0x7f800000u;}
static int snanbits(uint32_t x){return isnanbits(x)&&!(x&0x00400000u);}
static unsigned kind(uint32_t x) {
  unsigned e=(x>>23)&255;
  if(e<127)return 0;if(e>150)return 2;
  unsigned bit=150-e;if(x&((1u<<bit)-1))return 0;
  return (x&(1u<<bit))?1:2;
}
static unsigned mandatory(uint32_t x,uint32_t y,uint32_t rounded) {
  unsigned xm=x&0x7fffffffu,ym=y&0x7fffffffu;
  if(!ym)return snanbits(x)?FE_INVALID:0;
  if(x==0x3f800000u)return snanbits(y)?FE_INVALID:0;
  if(isnanbits(x)||isnanbits(y))return snanbits(x)||snanbits(y)?FE_INVALID:0;
  if(ym==0x7f800000u)return 0;
  if(!xm)return y>>31?FE_DIVBYZERO:0;
  if(xm==0x7f800000u)return 0;
  if(x>>31&&!kind(y))return FE_INVALID;
  return (rounded&0x7fffffffu)==0x7f800000u?FE_OVERFLOW:0;
}
static int nan_expected(uint32_t x,uint32_t y) {
  if(!(y&0x7fffffffu))return snanbits(x);
  if(x==0x3f800000u)return snanbits(y);
  return -1; /* MPFR decides all other mathematical domains. */
}
int main(int argc,char **argv) {
  if(argc!=3)return 2;
  FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"rb");if(!in||!out)return 3;
  uint32_t ih[8],oh[8];if(fread(ih,4,8,in)!=8||fread(oh,4,8,out)!=8)return 4;
  if(ih[0]!=0x49575050u||ih[1]!=1||ih[2]!=16||ih[3]!=208||!ih[4]||ih[5]||ih[6]||ih[7])return 4;
  uint32_t expected[8];memcpy(expected,ih,32);expected[0]=0x4f575050u;expected[3]=88;
  if(memcmp(expected,oh,32))return 4;
  mpfr_t x,y,lo,hi,lo2,hi2,actual,error,temp,ulp,maximum;
  mpfr_inits2(384,x,y,lo2,hi2,actual,error,temp,ulp,maximum,(mpfr_ptr)0);
  mpfr_init2(lo,256);mpfr_init2(hi,256);mpfr_set_zero(maximum,1);
  uint64_t active=0,merge=0,finite=0,nans=0,infinities=0,rounded_zeros=0,bins[4]={0};
  uint64_t negative_base=0,negative_exponent=0,subnormal_base=0,tiny_exponent=0,large_exponent=0;
  uint64_t worst_row=0;unsigned worst_lane=0;uint32_t worst_x=0,worst_y=0,worst_actual=0,worst_nearest=0;
  for(uint32_t row=0;row<ih[4];++row) {
    unsigned char input[208],output[88];uint64_t id;uint32_t mask,mode,xb[16],yb[16],mb[16],got[16],flags,csr;
    if(fread(input,1,208,in)!=208||fread(output,1,88,out)!=88)return 4;
    memcpy(&id,input,8);memcpy(&mask,input+8,4);memcpy(&mode,input+12,4);
    if(id!=row||mask&~65535u||mode>3||memcmp(input,output,16))return 4;
    memcpy(xb,input+16,64);memcpy(yb,input+80,64);memcpy(mb,input+144,64);memcpy(got,output+16,64);memcpy(&flags,output+80,4);memcpy(&csr,output+84,4);
    if((csr&~63u)!=0x1f80u)return 5;
    unsigned required=0;
    for(unsigned lane=0;lane<16;++lane) {
      if(!(mask&(1u<<lane))){if(got[lane]!=mb[lane])return 5;merge++;continue;}
      active++;negative_base+=xb[lane]>>31;negative_exponent+=yb[lane]>>31;
      subnormal_base+=(xb[lane]&0x7fffffffu)>0&&(xb[lane]&0x7fffffffu)<0x00800000u;
      tiny_exponent+=(yb[lane]&0x7fffffffu)<0x00800000u;
      large_exponent+=(yb[lane]&0x7fffffffu)>0x4b800000u&&(yb[lane]&0x7fffffffu)<0x7f800000u;
      mpfr_set_flt(x,value(xb[lane]),MPFR_RNDN);mpfr_set_flt(y,value(yb[lane]),MPFR_RNDN);
      mpfr_pow(lo,x,y,MPFR_RNDD);mpfr_pow(hi,x,y,MPFR_RNDU);
      mpfr_pow(lo2,x,y,MPFR_RNDD);mpfr_pow(hi2,x,y,MPFR_RNDU);
      int special=nan_expected(xb[lane],yb[lane]);
      uint32_t nearest=word(mpfr_get_flt(lo,MPFR_RNDN)),upper=word(mpfr_get_flt(hi,MPFR_RNDN));
      uint32_t nearest2=word(mpfr_get_flt(lo2,MPFR_RNDN)),upper2=word(mpfr_get_flt(hi2,MPFR_RNDN));
      int expect_nan=special==1||(special<0&&mpfr_nan_p(lo));
      if(expect_nan) {
        if(!isnanbits(got[lane])||!(got[lane]&0x400000u))return 6;
        nans++;
      } else {
        if(special==0){nearest=upper=nearest2=upper2=0x3f800000u;mpfr_set_ui(lo2,1,MPFR_RNDN);mpfr_set_ui(hi2,1,MPFR_RNDN);}
        if(nearest!=upper||nearest!=nearest2||nearest!=upper2||isnanbits(nearest))return 7;
        if(mpfr_cmp(lo,lo2)>0||mpfr_cmp(hi2,hi)>0)return 7;
        if((nearest&0x7fffffffu)==0x7f800000u) {
          if(got[lane]!=nearest)return 6;
          infinities++;
        } else {
          if((got[lane]&0x7fffffffu)>=0x7f800000u)return 6;
          if(!(nearest&0x7fffffffu)){rounded_zeros++;if((got[lane]>>31)!=(nearest>>31))return 6;}
          mpfr_set_flt(actual,value(got[lane]),MPFR_RNDN);
          mpfr_sub(error,actual,lo2,MPFR_RNDA);mpfr_abs(error,error,MPFR_RNDU);
          mpfr_sub(temp,actual,hi2,MPFR_RNDA);mpfr_abs(temp,temp,MPFR_RNDU);
          if(mpfr_cmp(temp,error)>0)mpfr_set(error,temp,MPFR_RNDU);
          int exponent=(int)((nearest>>23)&255);mpfr_set_ui_2exp(ulp,1,exponent?exponent-150:-149,MPFR_RNDN);
          mpfr_div(error,error,ulp,MPFR_RNDU);
          if(mpfr_cmp(error,maximum)>0) {
            mpfr_set(maximum,error,MPFR_RNDU);worst_row=row;worst_lane=lane;worst_x=xb[lane];worst_y=yb[lane];worst_actual=got[lane];worst_nearest=nearest;
          }
          if(mpfr_cmp_d(error,1)>0){fprintf(stderr,"over1ULP row%u lane%u x%08x y%08x got%08x near%08x error%.17g\n",row,lane,xb[lane],yb[lane],got[lane],nearest,mpfr_get_d(error,MPFR_RNDU));return 8;}
          bins[mpfr_cmp_d(error,.5)<=0?0:mpfr_cmp_d(error,.75)<=0?1:mpfr_cmp_ui(error,1)<=0?2:3]++;finite++;
        }
      }
      required|=mandatory(xb[lane],yb[lane],nearest);
    }
    if((flags&(FE_INVALID|FE_DIVBYZERO))!=(required&(FE_INVALID|FE_DIVBYZERO))||((required&FE_OVERFLOW)&&!(flags&FE_OVERFLOW)))return 9;
    if(!mask&&(flags||(csr&63)))return 9;
  }
  if(fgetc(in)!=EOF||fgetc(out)!=EOF||fclose(in)||fclose(out))return 4;
  printf("{\"mpfrVersion\":\"%s\",\"precisions\":[256,384],\"directedEndpointAgreement\":true,\"packets\":%u,\"activeLanes\":%llu,\"mergeLanes\":%llu,\"finiteUlpComparisons\":%llu,\"nanComparisons\":%llu,\"infinityComparisons\":%llu,\"roundedZeros\":%llu,\"maxUlpBound\":%.17g,\"histogram\":{\"leHalf\":%llu,\"leThreeQuarters\":%llu,\"leOne\":%llu,\"aboveOne\":%llu},\"coverage\":{\"negativeBase\":%llu,\"negativeExponent\":%llu,\"subnormalBase\":%llu,\"subnormalExponent\":%llu,\"absExponentAbove2pow24\":%llu},\"worst\":{\"row\":%llu,\"lane\":%u,\"x\":\"%08x\",\"y\":\"%08x\",\"actual\":\"%08x\",\"nearest\":\"%08x\"},\"bitMergeSevereFlagMismatches\":0}\n",
    mpfr_get_version(),ih[4],(unsigned long long)active,(unsigned long long)merge,(unsigned long long)finite,(unsigned long long)nans,(unsigned long long)infinities,(unsigned long long)rounded_zeros,mpfr_get_d(maximum,MPFR_RNDU),
    (unsigned long long)bins[0],(unsigned long long)bins[1],(unsigned long long)bins[2],(unsigned long long)bins[3],(unsigned long long)negative_base,(unsigned long long)negative_exponent,(unsigned long long)subnormal_base,(unsigned long long)tiny_exponent,(unsigned long long)large_exponent,
    (unsigned long long)worst_row,worst_lane,worst_x,worst_y,worst_actual,worst_nearest);
  mpfr_clears(x,y,lo,hi,lo2,hi2,actual,error,temp,ulp,maximum,(mpfr_ptr)0);return 0;
}
