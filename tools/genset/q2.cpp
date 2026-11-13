// Constructed AoS batch loops around unmodified CC0 vec3 operators.
#include "ray_headers.h"
#include "common.h"
#include <vector>
#include <limits>
using namespace genset_rt;
struct plain { double c[3]; };
void batch(vec3 *out, const vec3 *in, size_t n) {
    for(size_t i=0;i<n;++i) out[i] = 0.5*out[i] + in[i];
}
void disjoint(vec3 *__restrict out, const vec3 *__restrict in, size_t n) {
    for(size_t i=0;i<n;++i) out[i] = 0.5*out[i] + in[i];
}
int main() {
    const size_t sizes[]={0,1,3,4,5,7,8,9,15,16,17,257,1048576};
    kernel_clock timer("Q2-batches-and-checks");
    for(size_t n:sizes) for(int offset=0;offset<2;++offset)
      for(int mode=0;mode<5;++mode) {
        // modes: no-restrict disjoint; restricted disjoint; equal; +1; -1.
        std::vector<vec3> a(n+4), b(n+4);
        std::vector<plain> ra(n+4), rb(n+4);
        for(size_t i=0;i<n+4;++i) for(int c=0;c<3;++c) {
            a[i][c]=ra[i].c[c]=double((i*7+c)%31)/8;
            b[i][c]=rb[i].c[c]=double((i*3+c)%23)/16;
        }
        vec3 *out=&a[offset+1], *in=mode<2?&b[offset+1]:&a[offset+(mode==2?1:mode==3?0:2)];
        plain *ro=&ra[offset+1], *ri=mode<2?&rb[offset+1]:&ra[offset+(mode==2?1:mode==3?0:2)];
        for(size_t i=0;i<n;++i) for(int c=0;c<3;++c) ro[i].c[c]=0.5*ro[i].c[c]+ri[i].c[c];
        if(mode==1) disjoint(out,in,n); else batch(out,in,n);
        for(size_t i=0;i<n+4;++i) for(int c=0;c<3;++c)
            if(!close_value(a[i][c],ra[i].c[c]) || !close_value(b[i][c],rb[i].c[c])) return 1;
        std::printf("Q2 %lu %d %d PASS\n",(unsigned long)n,offset,mode);
      }
    // Contract allows IEEE infinities and NaNs; test their classes separately.
    vec3 x(std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN(),-0.0);
    vec3 y(1,2,-0.0);
    batch(&x,&y,1);
    if(!std::isinf(x[0]) || !std::isnan(x[1]) || x[2]!=0 || !std::signbit(x[2])) return 1;
    std::puts("SPECIAL PASS");
    return std::ferror(stdout) ? 2 : 0;
}
