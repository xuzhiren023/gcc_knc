// Independently written traversal variants; no code copied from BLAS.
#include "common.h"
#include <vector>
extern "C" void dgemm_(const char*,const char*,const int*,const int*,const int*,
                        const double*,const double*,const int*,const double*,
                        const int*,const double*,double*,const int*);
static double ga[40*40],gb[40*40],gc[40*40];
void bad_order(long m,long n,long k,long ld) {
    for(long i=0;i<m;++i) for(long j=0;j<n;++j)
        for(long h=0;h<k;++h) gc[i+j*ld]+=ga[i+h*ld]*gb[h+j*ld];
}
void good_order(long m,long n,long k,long ld) {
    for(long j=0;j<n;++j) for(long h=0;h<k;++h)
        for(long i=0;i<m;++i) gc[i+j*ld]+=ga[i+h*ld]*gb[h+j*ld];
}
int main() {
    int m=17,n=31,k=9,ld=40;
    double alpha=1,beta=1;
    std::vector<double> a(ld*ld),b(ld*ld),c(ld*ld);
    std::puts("Q4 17 31 9 40");
    for(char ta: {'N','T'}) for(char tb: {'N','T'}) {
        for(int j=0;j<ld;++j) for(int i=0;i<ld;++i) {
            a[i+j*ld]=double((i+2*j)%7)-3;
            b[i+j*ld]=double((3*i+j)%5)-2;
            c[i+j*ld]=-7;
        }
        { kernel_clock t("Q4-Fortran"); dgemm_(&ta,&tb,&m,&n,&k,&alpha,a.data(),&ld,b.data(),&ld,&beta,c.data(),&ld); }
        for(int j=0;j<ld;++j) for(int i=0;i<ld;++i) {
            double expected=-7;
            if(i<m && j<n) for(int h=0;h<k;++h)
                expected+=a[ta=='N'?i+h*ld:h+i*ld]*b[tb=='N'?h+j*ld:j+h*ld];
            if(c[i+j*ld]!=expected) return 1;
            value(c[i+j*ld]); // Includes every padding sentinel.
        }
    }
    for(int order=0;order<2;++order) {
        for(int j=0;j<ld;++j) for(int i=0;i<ld;++i) {
            ga[i+j*ld]=double((i+2*j)%7)-3;
            gb[i+j*ld]=double((3*i+j)%5)-2;
            gc[i+j*ld]=-7;
        }
        { kernel_clock t(order?"Q4-C-good":"Q4-C-bad");
          if(order) good_order(m,n,k,ld); else bad_order(m,n,k,ld); }
        for(int j=0;j<ld;++j) for(int i=0;i<ld;++i) {
            double expected=-7;
            if(i<m && j<n) for(int h=0;h<k;++h) expected+=ga[i+h*ld]*gb[h+j*ld];
            if(gc[i+j*ld]!=expected) return 1;
            value(gc[i+j*ld]);
        }
    }
    return std::ferror(stdout) ? 2 : 0;
}
