/* Host-only raw lane results and per-vector exception-state recorder. */
#include "logf_full.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fenv.h>
#include <immintrin.h>

int main(int argc,char **argv) {
  __builtin_cpu_init();
  if(argc==2 && !strcmp(argv[1],"--capabilities")) {
    printf("{\"avx2\":%s,\"fma\":%s,\"avx512f\":%s,\"roundingMode\":%d,\"feTonearest\":%d,\"mxcsr\":%u,\"compiler\":\"%s\",\"flags\":{\"invalid\":%d,\"divbyzero\":%d,\"overflow\":%d,\"underflow\":%d,\"inexact\":%d,\"all\":%d}}\n",
      __builtin_cpu_supports("avx2")?"true":"false",
      __builtin_cpu_supports("fma")?"true":"false",
      __builtin_cpu_supports("avx512f")?"true":"false",
      fegetround(),FE_TONEAREST,_mm_getcsr(),__VERSION__,
      FE_INVALID,FE_DIVBYZERO,FE_OVERFLOW,FE_UNDERFLOW,FE_INEXACT,FE_ALL_EXCEPT);
    return 0;
  }
  int offset=1;
  if(argc==4) {
    if(!strcmp(argv[1],"--round-up")) {if(fesetround(FE_UPWARD))return 11;}
    else if(!strcmp(argv[1],"--ftz")) _mm_setcsr(_mm_getcsr()|0x8000);
    else if(!strcmp(argv[1],"--daz")) _mm_setcsr(_mm_getcsr()|0x40);
    else return 2;
    offset=2;
  } else if(argc!=3) {fprintf(stderr,"usage: driver [STATE-CONTROL] INPUT.u32 OUTPUT.records\n");return 2;}
  const unsigned csr=_mm_getcsr();
  if(!__builtin_cpu_supports("avx2") || fegetround()!=FE_TONEAREST ||
     (csr&0x8040) || (csr&0x1f80)!=0x1f80) {
    fprintf(stderr,"unsupported host capability or floating-point state\n");return 3;
  }
  FILE *file=fopen(argv[offset],"rb");if(!file)return 4;
  if(fseek(file,0,SEEK_END))return 4;
  long bytes=ftell(file);if(bytes<=0 || bytes>16777216 || bytes%16)return 5;
  rewind(file);
  uint32_t *input=malloc((size_t)bytes);
  uint32_t *records=malloc((size_t)bytes/16*24);
  if(!input || !records)return 6;
  if(fread(input,1,(size_t)bytes,file)!=(size_t)bytes || fclose(file))return 7;
  for(long i=0;i<bytes/16;++i) {
    if(feclearexcept(FE_ALL_EXCEPT))return 12;
    _mm_setcsr(csr&~0x3fu); /* Clear the nonstandard denormal-operand flag too. */
    phi_host_logf_full4(input+4*i,records+6*i);
    records[6*i+4]=(uint32_t)fetestexcept(FE_ALL_EXCEPT);
    records[6*i+5]=_mm_getcsr();
  }
  file=fopen(argv[offset+1],"wb");if(!file)return 9;
  const size_t result_bytes=(size_t)bytes/16*24;
  if(fwrite(records,1,result_bytes,file)!=result_bytes || fclose(file))return 10;
  free(input);free(records);return 0;
}
