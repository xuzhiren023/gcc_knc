/* Fresh Windows SSE2-only logf research observer. Never a KNC/G5 result. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fenv.h>
#include <xmmintrin.h>
extern int phi_host_logf_register_e16(const uint32_t input[16],unsigned active,
                                  const uint32_t merge[16],uint32_t output[16]);
typedef struct {uint64_t before[8];uint32_t value[16];uint64_t after[8];} Guard;
_Static_assert(sizeof(Guard)==192,"guard layout");
_Static_assert(FE_INVALID==1 && FE_DIVBYZERO==4 && FE_OVERFLOW==8 &&
               FE_UNDERFLOW==16 && FE_INEXACT==32 && FE_ALL_EXCEPT==61,"host flags");
static void initialize(Guard *item,const unsigned char *bytes) {
  for(unsigned i=0;i<8;++i) {
    item->before[i]=UINT64_C(0x0123456789abcdef)^i;
    item->after[i]=UINT64_C(0xfedcba9876543210)^i;
  }
  memcpy(item->value,bytes,64);
}
static int intact(const Guard *item) {
  for(unsigned i=0;i<8;++i)
    if(item->before[i]!=(UINT64_C(0x0123456789abcdef)^i) ||
       item->after[i]!=(UINT64_C(0xfedcba9876543210)^i))return 0;
  return 1;
}
int main(int argc,char **argv) {
  if(argc!=3 || _mm_getcsr()!=0x1f80 || fegetround()!=FE_TONEAREST)return 2;
  FILE *input=fopen(argv[1],"rb");if(!input)return 3;
  uint32_t header[8];
  if(fread(header,4,8,input)!=8 || header[0]!=UINT32_C(0x45575048) ||
     header[1]!=1 || header[2]!=1 || header[3]!=16 || header[4]!=4 ||
     header[5]!=144 || !header[6] || header[6]>=400000 || header[7])return 4;
  const unsigned count=header[6];
  FILE *output=fopen(argv[2],"wbx");if(!output)return 5;
  header[0]=UINT32_C(0x4f575048);header[5]=88;
  if(fwrite(header,4,8,output)!=8)return 6;
  for(unsigned row=0;row<count;++row) {
    unsigned char packet[144];uint64_t index;uint32_t mask,alias;
    if(fread(packet,1,144,input)!=144)return 7;
    memcpy(&index,packet,8);memcpy(&mask,packet+8,4);memcpy(&alias,packet+12,4);
    if(index!=row || mask>65535 || alias>2)return 8;
    Guard x,m,y;initialize(&x,packet+16);initialize(&m,packet+80);initialize(&y,packet+80);
    uint32_t *destination=alias==1?x.value:alias==2?m.value:y.value;
    if(feclearexcept(FE_ALL_EXCEPT))return 9;
    _mm_setcsr(0x1f80);
    if(phi_host_logf_register_e16(x.value,mask,m.value,destination))return 10;
    uint32_t flags=(uint32_t)fetestexcept(FE_ALL_EXCEPT),mxcsr=_mm_getcsr();
    if(!intact(&x) || !intact(&m) || !intact(&y) ||
       (alias!=1 && memcmp(x.value,packet+16,64)) ||
       (alias!=2 && memcmp(m.value,packet+80,64)))return 11;
    if(fwrite(packet,1,16,output)!=16 || fwrite(destination,4,16,output)!=16 ||
       fwrite(&flags,4,1,output)!=1 || fwrite(&mxcsr,4,1,output)!=1)return 12;
  }
  if(fgetc(input)!=EOF || ferror(input) || fclose(input) || fclose(output))return 13;
  printf("HOST_REGISTER_LOGF_CAPTURED vectors=%u lanes=%u\n",count,count*16u);
  return 0;
}
