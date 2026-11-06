/* Windows/Cygwin host-only numerical experiment driver. Never deployed. */
#include "bounded_f64.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fenv.h>
#include <immintrin.h>

int main(int argc,char **argv) {
  __builtin_cpu_init();
  if(argc==2 && strcmp(argv[1],"--capabilities")==0) {
    printf("{\"avx2\":%s,\"fma\":%s,\"avx512f\":%s,\"roundingMode\":%d,\"feTonearest\":%d,\"mxcsr\":%u,\"compiler\":\"%s\"}\n",
      __builtin_cpu_supports("avx2")?"true":"false",
      __builtin_cpu_supports("fma")?"true":"false",
      __builtin_cpu_supports("avx512f")?"true":"false",
      fegetround(),FE_TONEAREST,_mm_getcsr(),__VERSION__);
    return 0;
  }
  if(argc!=3) {fprintf(stderr,"usage: driver INPUT.u64 OUTPUT.u64\n");return 2;}
  if(!__builtin_cpu_supports("avx2") || fegetround()!=FE_TONEAREST || (_mm_getcsr()&0x8040)) {
    fprintf(stderr,"unsupported host capability or floating-point state\n");return 3;
  }
  FILE *f=fopen(argv[1],"rb");if(!f)return 4;
  if(fseek(f,0,SEEK_END)!=0)return 4;
  long bytes=ftell(f);if(bytes<=0 || bytes>16777216 || bytes%32)return 5;
  rewind(f);
  uint64_t *input=malloc(bytes),*output=malloc(bytes);if(!input||!output)return 6;
  if(fread(input,1,bytes,f)!=(size_t)bytes || fclose(f)!=0)return 7;
  for(long i=0;i<bytes/8;i+=4) {
    if(phi_log_bounded4(input+i,output+i)) {
      fprintf(stderr,"unsupported domain at input offset %ld\n",i);return 8;
    }
  }
  f=fopen(argv[2],"wb");if(!f)return 9;
  if(fwrite(output,1,bytes,f)!=(size_t)bytes || fclose(f)!=0)return 10;
  free(input);free(output);return 0;
}
