/* Independent directed-endpoint MPFR binary64 pow reference. New DP packet
 * domain; no candidate arithmetic/table/source equations imported. */
#include <mpfr.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <fenv.h>
static uint64_t word(double x){uint64_t b;memcpy(&b,&x,8);return b;}
static double value(uint64_t x){double b;memcpy(&b,&x,8);return b;}
static int nanbits(uint64_t x){return (x&UINT64_C(0x7fffffffffffffff))>UINT64_C(0x7ff0000000000000);}
static int snanbits(uint64_t x){return nanbits(x)&&!(x&UINT64_C(0x0008000000000000));}
static unsigned kind(uint64_t x){unsigned e=(x>>52)&2047;if(e<1023)return 0;if(e>1075)return 2;unsigned s=1075-e;if(x&((UINT64_C(1)<<s)-1))return 0;return x&(UINT64_C(1)<<s)?1:2;}
static unsigned mandatory(uint64_t x,uint64_t y,uint64_t rounded) {
  uint64_t xm=x&UINT64_C(0x7fffffffffffffff),ym=y&UINT64_C(0x7fffffffffffffff);
  if(!ym)return snanbits(x)?FE_INVALID:0;
  if(x==UINT64_C(0x3ff0000000000000))return snanbits(y)?FE_INVALID:0;
  if(nanbits(x)||nanbits(y))return snanbits(x)||snanbits(y)?FE_INVALID:0;
  if(ym==UINT64_C(0x7ff0000000000000))return 0;
  if(!xm)return y>>63?FE_DIVBYZERO:0;
  if(xm==UINT64_C(0x7ff0000000000000))return 0;
  if((x>>63)&&!kind(y))return FE_INVALID;
  return (rounded&UINT64_C(0x7fffffffffffffff))==UINT64_C(0x7ff0000000000000)?FE_OVERFLOW:0;
}
int main(int argc,char **argv) {
  if(argc!=3)return 2;FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"rb");if(!in||!out)return 3;
  uint32_t ih[8],oh[8],expected[8];if(fread(ih,4,8,in)!=8||fread(oh,4,8,out)!=8)return 4;
  if(ih[0]!=0x49574450u||ih[1]!=1||ih[2]!=8||ih[3]!=208||!ih[4]||ih[5]||ih[6]||ih[7])return 4;
  memcpy(expected,ih,32);expected[0]=0x4f574450u;expected[3]=88;if(memcmp(expected,oh,32))return 4;
  mpfr_t x,y,lo,hi,lo2,hi2,actual,error,temp,ulp,maximum;mpfr_inits2(384,x,y,lo2,hi2,actual,error,temp,ulp,maximum,(mpfr_ptr)0);mpfr_init2(lo,256);mpfr_init2(hi,256);mpfr_set_zero(maximum,1);
  uint64_t active=0,merge=0,finite=0,nans=0,infs=0,zeros=0,bins[4]={0},negative_base=0,negative_exponent=0,subnormal_base=0,tiny_exponent=0,large_exponent=0;
  uint64_t worst_row=0,worst_x=0,worst_y=0,worst_actual=0,worst_nearest=0;unsigned worst_lane=0;
  for(uint32_t row=0;row<ih[4];++row) {
    unsigned char input[208],output[88];uint64_t id,xb[8],yb[8],mb[8],got[8];uint32_t mask,mode,flags,csr;
    if(fread(input,1,208,in)!=208||fread(output,1,88,out)!=88)return 4;
    memcpy(&id,input,8);memcpy(&mask,input+8,4);memcpy(&mode,input+12,4);if(id!=row||mask&~255u||mode>3||memcmp(input,output,16))return 4;
    memcpy(xb,input+16,64);memcpy(yb,input+80,64);memcpy(mb,input+144,64);memcpy(got,output+16,64);memcpy(&flags,output+80,4);memcpy(&csr,output+84,4);if((csr&~63u)!=0x1f80u)return 5;
    unsigned required=0,exact_identities=1;
    for(unsigned lane=0;lane<8;++lane) {
      if(!(mask&(1u<<lane))){if(got[lane]!=mb[lane])return 5;merge++;continue;}active++;
      uint64_t xm=xb[lane]&UINT64_C(0x7fffffffffffffff),ym=yb[lane]&UINT64_C(0x7fffffffffffffff);
      if(!((!ym&&!snanbits(xb[lane]))||(xb[lane]==UINT64_C(0x3ff0000000000000)&&!snanbits(yb[lane]))))exact_identities=0;
      negative_base+=xb[lane]>>63;negative_exponent+=yb[lane]>>63;subnormal_base+=xm>0&&xm<UINT64_C(0x0010000000000000);tiny_exponent+=ym<UINT64_C(0x0010000000000000);large_exponent+=ym>UINT64_C(0x4340000000000000)&&ym<UINT64_C(0x7ff0000000000000);
      mpfr_set_d(x,value(xb[lane]),MPFR_RNDN);mpfr_set_d(y,value(yb[lane]),MPFR_RNDN);
      mpfr_pow(lo,x,y,MPFR_RNDD);mpfr_pow(hi,x,y,MPFR_RNDU);mpfr_pow(lo2,x,y,MPFR_RNDD);mpfr_pow(hi2,x,y,MPFR_RNDU);
      int force_nan=(!ym&&snanbits(xb[lane]))||(xb[lane]==UINT64_C(0x3ff0000000000000)&&snanbits(yb[lane]));
      int force_one=(!ym&&!snanbits(xb[lane]))||(xb[lane]==UINT64_C(0x3ff0000000000000)&&!snanbits(yb[lane]));
      uint64_t nearest=word(mpfr_get_d(lo,MPFR_RNDN)),upper=word(mpfr_get_d(hi,MPFR_RNDN)),nearest2=word(mpfr_get_d(lo2,MPFR_RNDN)),upper2=word(mpfr_get_d(hi2,MPFR_RNDN));
      if(force_nan||(!force_one&&mpfr_nan_p(lo))) {if(!nanbits(got[lane])||!(got[lane]&UINT64_C(0x0008000000000000)))return 6;nans++;}
      else {
        if(force_one){nearest=upper=nearest2=upper2=UINT64_C(0x3ff0000000000000);mpfr_set_ui(lo2,1,MPFR_RNDN);mpfr_set_ui(hi2,1,MPFR_RNDN);}
        if(nearest!=upper||nearest!=nearest2||nearest!=upper2||nanbits(nearest)||mpfr_cmp(lo,lo2)>0||mpfr_cmp(hi2,hi)>0)return 7;
        if((nearest&UINT64_C(0x7fffffffffffffff))==UINT64_C(0x7ff0000000000000)){if(got[lane]!=nearest)return 6;infs++;}
        else {
          if((got[lane]&UINT64_C(0x7fffffffffffffff))>=UINT64_C(0x7ff0000000000000))return 6;
          if(!(nearest&UINT64_C(0x7fffffffffffffff))){zeros++;if((got[lane]>>63)!=(nearest>>63))return 6;}
          mpfr_set_d(actual,value(got[lane]),MPFR_RNDN);mpfr_sub(error,actual,lo2,MPFR_RNDA);mpfr_abs(error,error,MPFR_RNDU);mpfr_sub(temp,actual,hi2,MPFR_RNDA);mpfr_abs(temp,temp,MPFR_RNDU);if(mpfr_cmp(temp,error)>0)mpfr_set(error,temp,MPFR_RNDU);
          int e=(nearest>>52)&2047;mpfr_set_ui_2exp(ulp,1,e?e-1075:-1074,MPFR_RNDN);mpfr_div(error,error,ulp,MPFR_RNDU);
          if(mpfr_cmp(error,maximum)>0){mpfr_set(maximum,error,MPFR_RNDU);worst_row=row;worst_lane=lane;worst_x=xb[lane];worst_y=yb[lane];worst_actual=got[lane];worst_nearest=nearest;}
          if(mpfr_cmp_d(error,1)>0){fprintf(stderr,"over1ULP row%u lane%u x%016llx y%016llx got%016llx near%016llx error%.17g\n",row,lane,(unsigned long long)xb[lane],(unsigned long long)yb[lane],(unsigned long long)got[lane],(unsigned long long)nearest,mpfr_get_d(error,MPFR_RNDU));return 8;}
          bins[mpfr_cmp_d(error,.5)<=0?0:mpfr_cmp_d(error,.75)<=0?1:mpfr_cmp_ui(error,1)<=0?2:3]++;finite++;
        }
      }
      required|=mandatory(xb[lane],yb[lane],nearest);
    }
    if((flags&(FE_INVALID|FE_DIVBYZERO))!=(required&(FE_INVALID|FE_DIVBYZERO))||((required&FE_OVERFLOW)&&!(flags&FE_OVERFLOW)))return 9;
    if(!mask&&(flags||(csr&63)))return 9;
    if(exact_identities&&(flags||(csr&63)))return 9;
  }
  if(fgetc(in)!=EOF||fgetc(out)!=EOF||fclose(in)||fclose(out))return 4;
  printf("{\"mpfrVersion\":\"%s\",\"precisions\":[256,384],\"directedEndpointAgreement\":true,\"packets\":%u,\"activeLanes\":%llu,\"mergeLanes\":%llu,\"finiteUlpComparisons\":%llu,\"nanComparisons\":%llu,\"infinityComparisons\":%llu,\"roundedZeros\":%llu,\"maxUlpBound\":%.17g,\"histogram\":{\"leHalf\":%llu,\"leThreeQuarters\":%llu,\"leOne\":%llu,\"aboveOne\":%llu},\"coverage\":{\"negativeBase\":%llu,\"negativeExponent\":%llu,\"subnormalBase\":%llu,\"subnormalExponent\":%llu,\"absExponentAbove2pow53\":%llu},\"worst\":{\"row\":%llu,\"lane\":%u,\"x\":\"%016llx\",\"y\":\"%016llx\",\"actual\":\"%016llx\",\"nearest\":\"%016llx\"},\"bitMergeSevereFlagMismatches\":0}\n",
    mpfr_get_version(),ih[4],(unsigned long long)active,(unsigned long long)merge,(unsigned long long)finite,(unsigned long long)nans,(unsigned long long)infs,(unsigned long long)zeros,mpfr_get_d(maximum,MPFR_RNDU),(unsigned long long)bins[0],(unsigned long long)bins[1],(unsigned long long)bins[2],(unsigned long long)bins[3],(unsigned long long)negative_base,(unsigned long long)negative_exponent,(unsigned long long)subnormal_base,(unsigned long long)tiny_exponent,(unsigned long long)large_exponent,(unsigned long long)worst_row,worst_lane,(unsigned long long)worst_x,(unsigned long long)worst_y,(unsigned long long)worst_actual,(unsigned long long)worst_nearest);
  mpfr_clears(x,y,lo,hi,lo2,hi2,actual,error,temp,ulp,maximum,(mpfr_ptr)0);return 0;
}
