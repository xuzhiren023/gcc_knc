#include "common.h"
/* One dependent load per node. A 73-step permutation visits every power-of-two set. */
static __attribute__((noipa)) uintptr_t chase(uintptr_t p,unsigned n) {
    for(unsigned i=0;i<n;i++) p=*(volatile uintptr_t*)p;
    return p;
}
int main(void) {
    start("G08",1); unsigned huge_ok=0;
    for(int huge=0;huge<2;huge++) for(unsigned stride=4096;stride<=8192;stride*=2) {
        size_t bytes=4*1024*1024;
        void *p=mmap(NULL,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|(huge?MAP_HUGETLB:0),-1,0);
        if(p==MAP_FAILED) { printf("UNAVAILABLE hugetlb=%d errno=%d %s\n",huge,errno,strerror(errno)); require(huge,"ordinary mapping"); continue; }
        if(huge) huge_ok++;
        /* NOHUGEPAGE is advisory; smaps remains the authority, including older-kernel errors. */
        if(!huge) { errno=0; int rc=madvise(p,bytes,15); printf("MADV_NOHUGEPAGE rc=%d errno=%d\n",rc,errno); }
        memset(p,0,bytes);
        printf("MAPPING pages=%p bytes=%zu requested_huge=%d stride=%u\n",p,bytes,huge,stride); dump("/proc/self/smaps");
        for(unsigned n=16;n<=512;n*=2) for(unsigned spread=0;spread<2;spread++) {
            uintptr_t nodes[512];
            for(unsigned i=0;i<n;i++) nodes[i]=(uintptr_t)p+i*stride+(spread?((i*17)%64)*64:0);
            for(unsigned i=0;i<n;i++) *(uintptr_t*)nodes[i]=nodes[(i+73)%n];
            uintptr_t q=nodes[0];
            for(unsigned i=0;i<n;i++) { require(q==nodes[(i*73)%n],"independent chain order"); q=*(uintptr_t*)q; }
            require(q==nodes[0],"cycle closure");
            for(unsigned rep=0;rep<3;rep++) {
                unsigned steps=n*512; double t=now(); q=chase(nodes[0],steps); t=now()-t;
                require(q==nodes[0],"timed chase"); sink=q;
                printf("TIME chase huge_request=%d nodes=%u stride=%u distributed=%u rep=%u steps=%u seconds=%.9f\n",huge,n,stride,spread,rep,steps,t);
            }
        }
        dump("/proc/self/smaps"); require(!munmap(p,bytes),"unmap");
    }
    printf("COVERAGE explicit_huge_mappings=%u verify_KernelPageSize_before_comparison=1\n",huge_ok);
    result("G08",huge_ok?"PASS":"UNAVAILABLE"); return 0;
}
