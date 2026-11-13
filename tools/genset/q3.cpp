// Unmodified LGPL MD is included with only its example entry point renamed.
#define main upstream_md_main
#include "md.cpp"
#undef main
#include "common.h"
#include <vector>
int main() {
    const int n=32, d=3;
    std::vector<double> p(n*d),v(n*d),f(n*d),a(n*d);
    for(int j=0;j<n;++j) for(int i=0;i<d;++i) {
        p[i+d*j]=0.125*j+0.0625*i;
        v[i+d*j]=0.001*(i+j);
    }
    double pot,kin;
    std::puts("Q3 32 3 3");
    for(int step=0;step<3;++step) {
        { kernel_clock t("Q3-compute"); compute(n,d,p.data(),v.data(),1.0,f.data(),pot,kin); }
        value(pot); value(kin);
        for(double x:f) value(x);
        { kernel_clock t("Q3-update"); update(n,d,p.data(),v.data(),f.data(),a.data(),1.0,0.001); }
        for(double x:p) value(x);
        for(double x:v) value(x);
        for(double x:a) value(x);
    }
    return std::ferror(stdout) ? 2 : 0;
}
