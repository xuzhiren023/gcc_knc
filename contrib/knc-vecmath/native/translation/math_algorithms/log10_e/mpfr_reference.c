/* Independent MPFR log10 endpoints, no candidate constants or equations. */
#include <mpfr.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <fenv.h>
#if PW_SP
typedef uint32_t word;typedef float real;
#define LANES 16
#define SIGN UINT32_C(0x80000000)
#define MAG UINT32_C(0x7fffffff)
#define INF UINT32_C(0x7f800000)
#define QUIET UINT32_C(0x00400000)
#define ONE UINT32_C(0x3f800000)
#define MIN_NORMAL UINT32_C(0x00800000)
#define GET mpfr_get_flt
#define SET mpfr_set_flt
#define SHIFT 23
#define BIAS 150
#define SUB_SHIFT -149
#else
typedef uint64_t word;typedef double real;
#define LANES 8
#define SIGN UINT64_C(0x8000000000000000)
#define MAG UINT64_C(0x7fffffffffffffff)
#define INF UINT64_C(0x7ff0000000000000)
#define QUIET UINT64_C(0x0008000000000000)
#define ONE UINT64_C(0x3ff0000000000000)
#define MIN_NORMAL UINT64_C(0x0010000000000000)
#define GET mpfr_get_d
#define SET mpfr_set_d
#define SHIFT 52
#define BIAS 1075
#define SUB_SHIFT -1074
#endif
static word bits(real x){word b;memcpy(&b,&x,sizeof b);return b;}
static real value(word b){real x;memcpy(&x,&b,sizeof x);return x;}
int main(int argc,char **argv) {
  if(argc!=3)return 2;FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"rb");if(!in||!out)return 3;
  uint32_t ih[8],oh[8],eh[8];if(fread(ih,4,8,in)!=8||fread(oh,4,8,out)!=8)return 4;
  if(ih[0]!=0x494c5750u||ih[1]!=1||ih[2]!=LANES||ih[3]!=144||!ih[4]||ih[5]!=sizeof(word)*8||ih[6]||ih[7])return 4;
  memcpy(eh,ih,32);eh[0]=0x4f4c5750u;eh[3]=88;if(memcmp(eh,oh,32))return 4;
  mpfr_t x,lo,hi,lo2,hi2,a,e,t,u,m;mpfr_inits2(384,x,lo2,hi2,a,e,t,u,m,(mpfr_ptr)0);mpfr_init2(lo,256);mpfr_init2(hi,256);mpfr_set_zero(m,1);
  uint64_t active=0,merge=0,finite=0,nans=0,infs=0,subnormal=0,bins[4]={0},worst_row=0;unsigned worst_lane=0;word wx=0,wgot=0,wn=0;
  for(unsigned row=0;row<ih[4];++row) {
    unsigned char input[144],output[88];uint64_t id;uint32_t mask,mode,flags,csr;word xb[LANES],mb[LANES],got[LANES];
    if(fread(input,1,144,in)!=144||fread(output,1,88,out)!=88)return 4;
    memcpy(&id,input,8);memcpy(&mask,input+8,4);memcpy(&mode,input+12,4);if(id!=row||mask&~((1u<<LANES)-1)||mode>2||memcmp(input,output,16))return 4;
    memcpy(xb,input+16,64);memcpy(mb,input+80,64);memcpy(got,output+16,64);memcpy(&flags,output+80,4);memcpy(&csr,output+84,4);if((csr&~63u)!=0x1f80u)return 5;
    unsigned required=0,identities=1;
    for(unsigned lane=0;lane<LANES;++lane) {
      if(!(mask&(1u<<lane))){if(got[lane]!=mb[lane])return 5;merge++;continue;}active++;
      word mag=xb[lane]&MAG;int nan=mag>INF;
      if(xb[lane]!=ONE)identities=0;
      if(nan){if(!(xb[lane]&QUIET))required|=FE_INVALID;}else if(!mag)required|=FE_DIVBYZERO;else if(xb[lane]&SIGN)required|=FE_INVALID;
      SET(x,value(xb[lane]),MPFR_RNDN);mpfr_log10(lo,x,MPFR_RNDD);mpfr_log10(hi,x,MPFR_RNDU);mpfr_log10(lo2,x,MPFR_RNDD);mpfr_log10(hi2,x,MPFR_RNDU);
      if(mpfr_nan_p(lo)){if((got[lane]&MAG)<=INF||!(got[lane]&QUIET))return 6;nans++;continue;}
      word n=bits(GET(lo,MPFR_RNDN)),h=bits(GET(hi,MPFR_RNDN)),n2=bits(GET(lo2,MPFR_RNDN)),h2=bits(GET(hi2,MPFR_RNDN));
      if(n!=h||n!=n2||n!=h2||mpfr_cmp(lo,lo2)>0||mpfr_cmp(hi2,hi)>0)return 7;
      if((n&MAG)==INF){if(got[lane]!=n)return 6;infs++;continue;}
      if((got[lane]&MAG)>=INF||(!n&&got[lane]))return 6;
      SET(a,value(got[lane]),MPFR_RNDN);mpfr_sub(e,a,lo2,MPFR_RNDA);mpfr_abs(e,e,MPFR_RNDU);mpfr_sub(t,a,hi2,MPFR_RNDA);mpfr_abs(t,t,MPFR_RNDU);if(mpfr_cmp(t,e)>0)mpfr_set(e,t,MPFR_RNDU);
      int exponent=(n>>SHIFT)&(PW_SP?255:2047);mpfr_set_ui_2exp(u,1,exponent?exponent-BIAS:SUB_SHIFT,MPFR_RNDN);mpfr_div(e,e,u,MPFR_RNDU);
      if(mpfr_cmp(e,m)>0){mpfr_set(m,e,MPFR_RNDU);worst_row=row;worst_lane=lane;wx=xb[lane];wgot=got[lane];wn=n;}
      if(mpfr_cmp_d(e,1)>0){fprintf(stderr,"over1ULP row%u lane%u x%016llx got%016llx nearest%016llx error%.17g\n",row,lane,(unsigned long long)xb[lane],(unsigned long long)got[lane],(unsigned long long)n,mpfr_get_d(e,MPFR_RNDU));return 8;}
      bins[mpfr_cmp_d(e,.5)<=0?0:mpfr_cmp_d(e,.75)<=0?1:mpfr_cmp_ui(e,1)<=0?2:3]++;finite++;subnormal+=mag>0&&mag<MIN_NORMAL;
    }
    if((flags&(FE_INVALID|FE_DIVBYZERO))!=required||flags&(FE_OVERFLOW|FE_UNDERFLOW))return 9;
    if(identities&&(flags||(csr&63)))return 9;
  }
  if(fgetc(in)!=EOF||fgetc(out)!=EOF||fclose(in)||fclose(out))return 4;
  printf("{\"mpfrVersion\":\"%s\",\"precisions\":[256,384],\"endpointAgreement\":true,\"packets\":%u,\"activeLanes\":%llu,\"mergeLanes\":%llu,\"finiteUlpComparisons\":%llu,\"nanComparisons\":%llu,\"infinityComparisons\":%llu,\"subnormalInputComparisons\":%llu,\"maxUlpBound\":%.17g,\"histogram\":{\"leHalf\":%llu,\"leThreeQuarters\":%llu,\"leOne\":%llu,\"aboveOne\":%llu},\"worst\":{\"row\":%llu,\"lane\":%u,\"x\":\"%016llx\",\"actual\":\"%016llx\",\"nearest\":\"%016llx\"},\"bitMergeSevereFlagMismatches\":0}\n",mpfr_get_version(),ih[4],(unsigned long long)active,(unsigned long long)merge,(unsigned long long)finite,(unsigned long long)nans,(unsigned long long)infs,(unsigned long long)subnormal,mpfr_get_d(m,MPFR_RNDU),(unsigned long long)bins[0],(unsigned long long)bins[1],(unsigned long long)bins[2],(unsigned long long)bins[3],(unsigned long long)worst_row,worst_lane,(unsigned long long)wx,(unsigned long long)wgot,(unsigned long long)wn);
  mpfr_clears(x,lo,hi,lo2,hi2,a,e,t,u,m,(mpfr_ptr)0);return 0;
}
