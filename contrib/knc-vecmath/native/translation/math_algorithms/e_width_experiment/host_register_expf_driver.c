/* Explicit Windows host research only. This format is never a KNC result. */
#include "e_algorithms.h"
#include <stdio.h>
#include <stdint.h>
#include <xmmintrin.h>
int main(int argc, char **argv) {
  fprintf(stderr,"HOST_REGISTER_EXPF argc=%d csr=%x\n",argc,_mm_getcsr());
  if (argc != 3 || _mm_getcsr() != 0x1f80) return 2;
  FILE *input=fopen(argv[1],"rb"), *output=fopen(argv[2],"wb");
  uint32_t header[8], x[16], y[16];
  if (!input || !output || fread(header,4,8,input)!=8) return 3;
  if (header[0]!=0x49453547 || header[1]!=1 || header[2]!=16 || header[3]!=4 ||
      header[4]!=64 || !header[5] || header[6] || header[7]) return 4;
  header[0]=0x48453547; header[4]=68;
  if (fwrite(header,4,8,output)!=8) return 5;
  fprintf(stderr,"HOST_REGISTER_EXPF vectors=%u\n",header[5]);
  for (unsigned row=0; row<header[5]; ++row) {
    if (fread(x,4,16,input)!=16) return 6;
    _mm_setcsr(0x1f80);
    if (!row) fprintf(stderr,"HOST_REGISTER_EXPF first-call\n");
    if (phi_host_expf_e16(x,65535,x,y)) return 7;
    if (!row) fprintf(stderr,"HOST_REGISTER_EXPF first-return\n");
    uint32_t status=_mm_getcsr();
    if (fwrite(y,4,16,output)!=16 || fwrite(&status,4,1,output)!=1) return 8;
  }
  if (fgetc(input)!=EOF || fclose(input) || fclose(output)) return 9;
  return 0;
}
