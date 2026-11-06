/* Binary raw packets for the new DP pow algorithm assay. Host only. */
#include "pow_e8.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fenv.h>
#include <immintrin.h>
typedef struct {uint64_t pre[8],value[8],post[8];} Guard;
static void init(Guard *g,const uint64_t *p) {
  memcpy(g->value,p,64);
  for(unsigned i=0;i<8;++i){g->pre[i]=0x12345678u^i;g->post[i]=0xfedcba98u^i;}
}
static int intact(const Guard *g) {
  for(unsigned i=0;i<8;++i)if(g->pre[i]!=(0x12345678u^i)||g->post[i]!=(0xfedcba98u^i))return 0;
  return 1;
}
int main(int argc,char **argv) {
  __builtin_cpu_init();
  if(argc==2&&!strcmp(argv[1],"--capabilities")) {
    printf("{\"avx2\":%d,\"fma\":%d,\"avx512f\":%d,\"mxcsr\":%u,\"rounding\":%d,\"compiler\":\"%s\",\"flags\":{\"invalid\":%d,\"divbyzero\":%d,\"overflow\":%d,\"underflow\":%d,\"inexact\":%d}}\n",
      !!__builtin_cpu_supports("avx2"),!!__builtin_cpu_supports("fma"),!!__builtin_cpu_supports("avx512f"),_mm_getcsr(),fegetround(),__VERSION__,FE_INVALID,FE_DIVBYZERO,FE_OVERFLOW,FE_UNDERFLOW,FE_INEXACT);return 0;
  }
  if(argc==2&&!strcmp(argv[1],"--invalid-mask")) {
    uint64_t x[8],y[8],m[8],o[8],saved[8];
    for(unsigned i=0;i<8;++i){x[i]=y[i]=UINT64_C(0x7ff0000000000001);m[i]=0;o[i]=saved[i]=0xaabbccdd;}
    feclearexcept(FE_ALL_EXCEPT);_mm_setcsr(_mm_getcsr()&~63u);
    if(phi_host_pow_e8(x,y,256,m,o)!=1||memcmp(o,saved,64)||fetestexcept(FE_ALL_EXCEPT)||(_mm_getcsr()&63))return 13;
    puts("INVALID_MASK_ZERO_FP_UNCHANGED");return 0;
  }
  if(argc!=3)return 2;
  const unsigned csr=_mm_getcsr();
  if(!__builtin_cpu_supports("avx2")||fegetround()!=FE_TONEAREST||(csr&0x8040)||(csr&0x1f80)!=0x1f80)return 3;
  FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");if(!in||!out)return 4;
  uint32_t h[8];if(fread(h,4,8,in)!=8||h[0]!=0x49574450u||h[1]!=1||h[2]!=8||h[3]!=208||!h[4]||h[5]||h[6]||h[7])return 5;
  const unsigned count=h[4];h[0]=0x4f574450u;h[3]=88;if(fwrite(h,4,8,out)!=8)return 9;
  for(unsigned i=0;i<count;++i) {
    unsigned char row[208];uint64_t id;uint32_t mask,mode;
    if(fread(row,1,208,in)!=208)return 5;
    memcpy(&id,row,8);memcpy(&mask,row+8,4);memcpy(&mode,row+12,4);
    if(id!=i||mask&~255u||mode>3)return 5;
    Guard x,y,m,o;init(&x,(const uint64_t *)(row+16));init(&y,(const uint64_t *)(row+80));init(&m,(const uint64_t *)(row+144));init(&o,(const uint64_t *)(row+144));
    uint64_t *dest=mode==1?x.value:mode==2?y.value:mode==3?m.value:o.value;
    if(feclearexcept(FE_ALL_EXCEPT))return 12;
    _mm_setcsr(csr&~63u);
    const int status=phi_host_pow_e8(x.value,y.value,mask,m.value,dest);
    const uint32_t flags=fetestexcept(FE_ALL_EXCEPT),after=_mm_getcsr();
    if(status||!intact(&x)||!intact(&y)||!intact(&m)||!intact(&o)||
       (mode!=1&&memcmp(x.value,row+16,64))||(mode!=2&&memcmp(y.value,row+80,64))||(mode!=3&&memcmp(m.value,row+144,64)))return 13;
    if(fwrite(row,1,16,out)!=16||fwrite(dest,1,64,out)!=64||fwrite(&flags,4,1,out)!=1||fwrite(&after,4,1,out)!=1)return 9;
  }
  if(fgetc(in)!=EOF||fclose(in)||fclose(out))return 10;
  return 0;
}
