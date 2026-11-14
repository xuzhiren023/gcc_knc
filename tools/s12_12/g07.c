#include "common.h"
extern unsigned branches_0_0(const unsigned char*);
extern unsigned branches_0_16(const unsigned char*);
extern unsigned branches_64_0(const unsigned char*);
extern unsigned branches_64_16(const unsigned char*);
extern unsigned branches_1024_0(const unsigned char*);
extern unsigned branches_1024_16(const unsigned char*);
int main(void) {
    start("G07",1);
    unsigned (*fs[])(const unsigned char*)={branches_0_0,branches_0_16,branches_64_0,branches_64_16,branches_1024_0,branches_1024_16};
    const unsigned gaps[]={0,0,64,64,1024,1024};
    unsigned char *data=alloc(4096*64); printf("MAPPING branch_input=%p bytes=262144\n",data); dump("/proc/self/smaps");
    for(unsigned pattern=0;pattern<3;pattern++) {
        uint32_t rng=42; unsigned expected=0;
        for(unsigned i=0;i<4096*64;i++) {
            rng=rng*1664525u+1013904223u;
            data[i]=pattern==0?1:pattern==1?(i&1):(rng>>31); expected+=data[i];
        }
        for(unsigned rep=0;rep<3;rep++) for(unsigned k=0;k<6;k++) {
            unsigned v=(k+rep)%6,s=0; double t=now();
            for(unsigned i=0;i<4096;i++) s+=fs[v](data+i*64);
            t=now()-t; require(s==expected,"branch independent population count");
            printf("TIME branch pattern=%u spacing=%u entry_offset=%u rep=%u calls=4096 branches=262144 seconds=%.9f check=%u\n",pattern,gaps[v],(v%2)*16,rep,t,s);
        }
    }
    munmap(data,4096*64); result("G07","PASS"); return 0;
}
