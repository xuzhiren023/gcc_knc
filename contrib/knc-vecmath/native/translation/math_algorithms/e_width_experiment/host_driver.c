/* Private raw-packet host experiment. No GNU masked ABI or target code. */
#include "e_algorithms.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fenv.h>
#include <immintrin.h>
#define MAGIC 0x45575048u
#define OUTPUT_MAGIC 0x4f575048u
typedef union {uint32_t w[16];uint64_t q[8];unsigned char bytes[64];} Words;
typedef struct {uint64_t before[8];Words value;uint64_t after[8];} Guard;
_Static_assert(sizeof(Words)==64 && sizeof(Guard)==192,"unexpected raw layout");
static void initialize(Guard *item,const void *bytes) {
  for(unsigned i=0;i<8;++i){item->before[i]=UINT64_C(0x0123456789abcdef)^i;item->after[i]=UINT64_C(0xfedcba9876543210)^i;}
  memcpy(item->value.bytes,bytes,64);
}
static int intact(const Guard *item) {
  for(unsigned i=0;i<8;++i)if(item->before[i]!=(UINT64_C(0x0123456789abcdef)^i) || item->after[i]!=(UINT64_C(0xfedcba9876543210)^i))return 0;
  return 1;
}
static int apply(unsigned op,const Words *input,unsigned mask,const Words *merge,Words *output,int unsafe) {
  switch(op) {
    case 0:return unsafe?phi_host_expf_e16_unsafe_negative(input->w,mask,merge->w,output->w):phi_host_expf_e16(input->w,mask,merge->w,output->w);
    case 1:return unsafe?phi_host_logf_e16_unsafe_negative(input->w,mask,merge->w,output->w):phi_host_logf_e16(input->w,mask,merge->w,output->w);
    case 2:return unsafe?phi_host_exp_e8_unsafe_negative(input->q,mask,merge->q,output->q):phi_host_exp_e8(input->q,mask,merge->q,output->q);
    case 3:return unsafe?phi_host_log_e8_unsafe_negative(input->q,mask,merge->q,output->q):phi_host_log_e8(input->q,mask,merge->q,output->q);
    default:return 1;
  }
}
int main(int argc,char **argv) {
  __builtin_cpu_init();
  if(argc==2 && !strcmp(argv[1],"--capabilities")) {
    printf("{\"avx2\":%s,\"fma\":%s,\"avx512f\":%s,\"roundingMode\":%d,\"feTonearest\":%d,\"mxcsr\":%u,\"compiler\":\"%s\",\"flags\":{\"invalid\":%d,\"divbyzero\":%d,\"overflow\":%d,\"underflow\":%d,\"inexact\":%d,\"all\":%d}}\n",
      __builtin_cpu_supports("avx2")?"true":"false",__builtin_cpu_supports("fma")?"true":"false",
      __builtin_cpu_supports("avx512f")?"true":"false",fegetround(),FE_TONEAREST,_mm_getcsr(),__VERSION__,
      FE_INVALID,FE_DIVBYZERO,FE_OVERFLOW,FE_UNDERFLOW,FE_INEXACT,FE_ALL_EXCEPT);return 0;
  }
  if(argc==2 && !strcmp(argv[1],"--invalid-mask-control")) {
    Words input,merge,output,saved;memset(&input,0xff,64);memset(&merge,0xab,64);memset(&saved,0xcd,64);
    for(unsigned op=0;op<4;++op) {
      memcpy(&output,&saved,64);if(feclearexcept(FE_ALL_EXCEPT))return 12;_mm_setcsr(_mm_getcsr()&~0x3fu);
      if(apply(op,&input,1u<<(op<2?16:8),&merge,&output,0)!=1 || memcmp(&output,&saved,64) || fetestexcept(FE_ALL_EXCEPT) || (_mm_getcsr()&0x3f))return 13;
    }
    puts("INVALID_MASK_UNCHANGED_ZERO_FP");return 0;
  }
  int offset=1,unsafe=0;
  if(argc==4) {
    if(!strcmp(argv[1],"--round-up")){if(fesetround(FE_UPWARD))return 11;}
    else if(!strcmp(argv[1],"--ftz"))_mm_setcsr(_mm_getcsr()|0x8000);
    else if(!strcmp(argv[1],"--daz"))_mm_setcsr(_mm_getcsr()|0x40);
    else if(!strcmp(argv[1],"--unsafe-negative"))unsafe=1;
    else return 2;
    offset=2;
  } else if(argc!=3)return 2;
  const unsigned csr=_mm_getcsr();
  if(!__builtin_cpu_supports("avx2") || fegetround()!=FE_TONEAREST || (csr&0x8040) || (csr&0x1f80)!=0x1f80)return 3;
  FILE *file=fopen(argv[offset],"rb");if(!file)return 4;
  if(fseek(file,0,SEEK_END))return 4;
  long bytes=ftell(file);
  if(bytes<32 || bytes>67108864)return 5;
  rewind(file);unsigned char *input=malloc((size_t)bytes);if(!input)return 6;
  if(fread(input,1,(size_t)bytes,file)!=(size_t)bytes || fclose(file))return 7;
  uint32_t header[8];memcpy(header,input,32);
  const unsigned op=header[2],lanes=op<2?16:8,word_bytes=op<2?4:8;
  const unsigned count=header[6],all=(1u<<lanes)-1;
  if(header[0]!=MAGIC || header[1]!=1 || op>3 || header[3]!=lanes || header[4]!=word_bytes || header[5]!=144 || !count || header[7] || (uint64_t)bytes!=32+UINT64_C(144)*count)return 5;
  for(unsigned i=0;i<count;++i) {
    const unsigned char *row=input+32+(size_t)i*144;uint64_t index;uint32_t mask,mode;
    memcpy(&index,row,8);memcpy(&mask,row+8,4);memcpy(&mode,row+12,4);
    if(index!=i || mask&~all || mode>2)return 5;
  }
  const size_t result_bytes=32+(size_t)count*88;
  unsigned char *records=malloc(result_bytes);if(!records)return 6;
  header[0]=OUTPUT_MAGIC;header[5]=88;memcpy(records,header,32);
  for(unsigned i=0;i<count;++i) {
    const unsigned char *row=input+32+(size_t)i*144;unsigned char *record=records+32+(size_t)i*88;
    uint32_t mask,mode;memcpy(&mask,row+8,4);memcpy(&mode,row+12,4);
    Guard x,m,y;initialize(&x,row+16);initialize(&m,row+80);initialize(&y,row+80);
    Words *destination=mode==1?&x.value:mode==2?&m.value:&y.value;
    if(feclearexcept(FE_ALL_EXCEPT))return 12;
    _mm_setcsr(csr&~0x3fu);
    const int status=apply(op,&x.value,mask,&m.value,destination,unsafe);
    const uint32_t flags=(uint32_t)fetestexcept(FE_ALL_EXCEPT),mxcsr=_mm_getcsr();
    if(status || !intact(&x) || !intact(&m) || !intact(&y) ||
       (mode!=1 && memcmp(x.value.bytes,row+16,64)) || (mode!=2 && memcmp(m.value.bytes,row+80,64)))return 13;
    memcpy(record,row,16);memcpy(record+16,destination->bytes,64);memcpy(record+80,&flags,4);memcpy(record+84,&mxcsr,4);
  }
  file=fopen(argv[offset+1],"wb");if(!file)return 9;
  if(fwrite(records,1,result_bytes,file)!=result_bytes || fclose(file))return 10;
  free(input);free(records);return 0;
}
