#include "atan_e.h"
#include <fenv.h>
#include <immintrin.h>
#include <stdio.h>
#include <string.h>
#if PW_SP
typedef uint32_t word;
#define LANES 16
#define SNAN UINT32_C(0x7f800001)
#else
typedef uint64_t word;
#define LANES 8
#define SNAN UINT64_C(0x7ff0000000000001)
#endif
typedef struct {word pre[LANES],value[LANES],post[LANES];} Guard;
static void init(Guard*g,const void*p){memcpy(g->value,p,64);for(unsigned i=0;i<LANES;++i){g->pre[i]=(word)0xaabbccdd^i;g->post[i]=(word)0x12345678^i;}}
static int intact(const Guard*g){for(unsigned i=0;i<LANES;++i)if(g->pre[i]!=((word)0xaabbccdd^i)||g->post[i]!=((word)0x12345678^i))return 0;return 1;}
static int apply(const word*a,const word*b,unsigned mask,const word*m,word*out){
#if PW_BINARY
#if PW_SP
  return phi_host_atan2f_e16(a,b,mask,m,out);
#else
  return phi_host_atan2_e8(a,b,mask,m,out);
#endif
#else
  (void)b;return phi_host_atanf_e16(a,mask,m,out);
#endif
}
int main(int argc,char**argv){
  if(argc==2&&!strcmp(argv[1],"--invalid-mask")){word a[LANES],b[LANES],m[LANES],o[LANES],saved[LANES];for(unsigned i=0;i<LANES;++i){a[i]=b[i]=SNAN;m[i]=0;o[i]=saved[i]=(word)0xabcd1234;}feclearexcept(FE_ALL_EXCEPT);_mm_setcsr(_mm_getcsr()&~63u);if(apply(a,b,1u<<LANES,m,o)!=1||memcmp(o,saved,64)||fetestexcept(FE_ALL_EXCEPT)||(_mm_getcsr()&63))return 13;puts("INVALID_MASK_ZERO_FP_UNCHANGED");return 0;}
  if(argc!=3||fegetround()!=FE_TONEAREST||(_mm_getcsr()&0xffc0)!=0x1f80)return 2;
  FILE*in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");if(!in||!out)return 3;uint32_t h[8];if(fread(h,4,8,in)!=8||h[0]!=0x494c5750u||h[1]!=1||h[2]!=LANES||h[3]!=208||!h[4]||h[5]!=sizeof(word)*8||h[6]!=PW_BINARY||h[7])return 4;unsigned count=h[4];h[0]=0x4f4c5750u;h[3]=88;if(fwrite(h,4,8,out)!=8)return 5;
  for(unsigned row=0;row<count;++row){unsigned char input[208];uint64_t id;uint32_t mask,mode;if(fread(input,1,208,in)!=208)return 4;memcpy(&id,input,8);memcpy(&mask,input+8,4);memcpy(&mode,input+12,4);if(id!=row||mask&~((1u<<LANES)-1)||mode>3)return 4;Guard a,b,m,o;init(&a,input+16);init(&b,input+80);init(&m,input+144);init(&o,input+144);word*dest=mode==1?a.value:mode==2?b.value:mode==3?m.value:o.value;feclearexcept(FE_ALL_EXCEPT);_mm_setcsr(_mm_getcsr()&~63u);if(apply(a.value,b.value,mask,m.value,dest))return 13;uint32_t flags=fetestexcept(FE_ALL_EXCEPT),csr=_mm_getcsr();if(!intact(&a)||!intact(&b)||!intact(&m)||!intact(&o)||(mode!=1&&memcmp(a.value,input+16,64))||(mode!=2&&memcmp(b.value,input+80,64))||(mode!=3&&memcmp(m.value,input+144,64)))return 13;if(fwrite(input,1,16,out)!=16||fwrite(dest,1,64,out)!=64||fwrite(&flags,4,1,out)!=1||fwrite(&csr,4,1,out)!=1)return 5;}
  if(fgetc(in)!=EOF||fclose(in)||fclose(out))return 4;return 0;
}
