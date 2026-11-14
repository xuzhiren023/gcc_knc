#include "common.h"
#include <math.h>
#include <float.h>
#include <fenv.h>
#include <dlfcn.h>
#include <gnu/libc-version.h>
static double (*volatile logfn)(double);
static void *(*volatile copyfn)(void*,const void*,size_t);
static void *(*volatile setfn)(void*,int,size_t);
static __attribute__((noipa)) double bridge(double x) { return x; }
static double (*volatile bridgefn)(double)=bridge;
static void route(void *f,const char *name) {
    Dl_info d; require(dladdr(f,&d)!=0,"dladdr");
    printf("ROUTE %s address=%p object=%s base=%p symbol=%s symbol_address=%p\n",name,f,d.dli_fname,d.dli_fbase,d.dli_sname?d.dli_sname:"unknown",d.dli_saddr);
}
int main(void) {
    start("G05",1); printf("LIBC %s\n",gnu_get_libc_version());
    logfn=log; copyfn=memcpy; setfn=memset;
    route((void*)logfn,"log"); route((void*)copyfn,"memcpy"); route((void*)setfn,"memset"); dump("/proc/self/maps");
    /* Analytic values, independent of another log implementation. No replacement proposed. */
    const double ln2=0.693147180559945309417232121458176568;
    for(int k=-20;k<=20;k++) {
        double x=ldexp(1.0,k),y=logfn(x),ref=k*ln2;
        require(fabs(y-ref)<=8*DBL_EPSILON*(1+fabs(ref)),"log power-of-two reference");
    }
    const double boundary[]={0.0,-0.0,-1.0,INFINITY,NAN,DBL_MIN,0x1p-1074,DBL_MAX,1.0+DBL_EPSILON};
    for(unsigned i=0;i<sizeof boundary/sizeof *boundary;i++) {
        errno=0; feclearexcept(FE_ALL_EXCEPT); double y=logfn(boundary[i]);
        printf("SEMANTICS log x=%a y=%a errno=%d flags=%x\n",boundary[i],y,errno,fetestexcept(FE_ALL_EXCEPT));
        if(i<2) require(isinf(y)&&signbit(y),"log zero");
        else if(i==2||i==4) require(isnan(y),"log NaN/domain");
        else if(i==3) require(isinf(y)&&!signbit(y),"log infinity");
        else require(isfinite(y),"log finite");
    }
    double input[1024]; for(unsigned i=0;i<1024;i++) input[i]=0.5+i/1024.0;
    for(unsigned rep=0;rep<3;rep++) for(unsigned m=0;m<2;m++) {
        double sum=0,t=now();
        for(unsigned j=0;j<128;j++) for(unsigned i=0;i<1024;i++) sum+=(m?logfn:bridgefn)(input[i]);
        t=now()-t; require(isfinite(sum),"live math output");
        printf("TIME math mode=%s calls=131072 rep=%u seconds=%.9f sum=%a\n",m?"log":"identity_bridge",rep,t,sum);
    }
    size_t cap=4*1024*1024+128; unsigned char *a=alloc(cap),*b=alloc(cap);
    for(size_t i=0;i<cap;i++) a[i]=(i*37+11)&255;
    printf("MAPPING src=%p dst=%p bytes_each=%zu\n",a,b,cap); dump("/proc/self/smaps");
    for(size_t n=16;n<=4*1024*1024;n*=8) for(unsigned off=0;off<2;off++) for(unsigned rep=0;rep<3;rep++) {
        size_t loops=4*1024*1024/n; if(loops>4096) loops=4096;
        memset(b,0xAA,cap); double t=now();
        for(size_t j=0;j<loops;j++) require(copyfn(b+64+off,a+64+off,n)==b+64+off,"copy return");
        t=now()-t; for(size_t i=0;i<n;i++) require(b[64+off+i]==((64+off+i)*37+11)%256,"copy bytes");
        require(b[63+off]==0xAA&&b[64+off+n]==0xAA,"copy bounds");
        printf("TIME memcpy bytes=%zu offset=%u loops=%zu rep=%u seconds=%.9f\n",n,off,loops,rep,t);
        t=now(); for(size_t j=0;j<loops;j++) require(setfn(b+64+off,0x5A,n)==b+64+off,"set return");
        t=now()-t; for(size_t i=0;i<n;i++) require(b[64+off+i]==0x5A,"set bytes");
        require(b[63+off]==0xAA&&b[64+off+n]==0xAA,"set bounds");
        printf("TIME memset bytes=%zu offset=%u loops=%zu rep=%u seconds=%.9f\n",n,off,loops,rep,t);
    }
    munmap(a,cap); munmap(b,cap); result("G05","PASS"); return 0;
}
