#include "common.h"
typedef float v16sf __attribute__((vector_size(64)));
static __attribute__((noipa)) uint64_t stream(uint32_t *a,size_t n,unsigned d,int update) {
    uint64_t s=0;
    for(size_t i=0;i<n;i++) {
        if(d && i+d<n) __builtin_prefetch(a+i+d,0,3);
        uint32_t v=a[i]; s+=v; if(update) a[i]=v+1;
    }
    return s;
}
static __attribute__((noipa)) void stores(v16sf *p,size_t n,int mode) {
    v16sf v={0};
    for(size_t i=0;i<n;i++) {
        if(mode==0) __asm__ volatile("vmovaps %g1,%0":"=m"(p[i]):"YJ"(v):"memory");
        else if(mode==1) __asm__ volatile("vmovnraps %g1,%0":"=m"(p[i]):"YJ"(v):"memory");
        else __asm__ volatile("vmovnrngoaps %g1,%0":"=m"(p[i]):"YJ"(v):"memory");
    }
    /* Includes publication ordering in every store variant (ISA 327364). */
    __asm__ volatile("lock; addl $0,(%%rsp)":::"memory","cc");
}
int main(void) {
    start("G04",1);
    const unsigned ds[]={0,8,16,32,64};
    for(unsigned size=0;size<2;size++) {
        size_t n=(size?32*1024*1024:32*1024)/4;
        uint32_t *a=alloc(n*4); printf("MAPPING stream=%p bytes=%zu\n",(void*)a,n*4);
        for(size_t i=0;i<n;i++) a[i]=(uint32_t)(i&255);
        dump("/proc/self/smaps");
        for(int rep=0;rep<3;rep++) for(int u=0;u<2;u++) for(int j=0;j<5;j++) {
            unsigned d=ds[(j+rep)%5]*16;
            for(size_t i=0;i<n;i++) a[i]=(uint32_t)(i&255);
            double t=now(); uint64_t s=stream(a,n,d,u); t=now()-t;
            require(s==n/256*32640,"stream sum");
            for(size_t i=0;i<n;i++) require(a[i]==(i&255)+(unsigned)u,"stream contents");
            printf("TIME stream bytes=%zu update=%d distance_lines=%u rep=%d seconds=%.9f\n",n*4,u,d/16,rep,t);
        }
        for(int rep=0;rep<3;rep++) for(int j=0;j<3;j++) {
            int m=(j+rep)%3;
            memset(a,0x55,n*4); double t=now(); stores((v16sf*)a,n/16,m); double write=now()-t;
            t=now(); uint64_t s=stream(a,n,0,0); double reuse=now()-t;
            require(s==0,"fenced store/reuse sum");
            for(size_t i=0;i<n;i++) require(a[i]==0,"store contents");
            printf("TIME store bytes=%zu mode=%d rep=%d write_seconds=%.9f reuse_seconds=%.9f\n",n*4,m,rep,write,reuse);
        }
        require(!munmap(a,n*4),"unmap");
    }
    result("G04","PASS"); return 0;
}
