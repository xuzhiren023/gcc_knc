// Constructed deterministic driver; upstream CC0 headers remain unedited.
#include "ray_headers.h"
#include "common.h"
using namespace genset_rt;

// Deterministic normal reflection retains recursive virtual hit dispatch,
// without depending on the host C library's random-number implementation.
color trace(const ray& r, const hittable& world, int depth) {
    if (!depth) return color(0,0,0);
    hit_record h;
    if (world.hit(r, interval(0.001, genset_rt::infinity), h)) {
        vec3 d = r.direction() - 2*dot(r.direction(),h.normal)*h.normal;
        return 0.25*(h.normal+color(1,1,1)) + 0.5*trace(ray(h.p,d),world,depth-1);
    }
    double a = 0.5*(unit_vector(r.direction()).y()+1);
    return (1-a)*color(1,1,1)+a*color(0.5,0.7,1);
}
int main(int argc, char **argv) {
    int width = argc > 1 ? std::atoi(argv[1]) : 32;
    if (width != 32) return 2;
    hittable_list world;
    auto mat = make_shared<lambertian>(color(0.7,0.3,0.2));
    world.add(make_shared<sphere>(point3(0,0,-1),0.5,mat));
    world.add(make_shared<sphere>(point3(0,-100.5,-1),100,mat));
    // Analytic hit and rejection controls, independent of renderer output.
    hit_record h;
    if (!world.hit(ray(point3(0,0,0),vec3(0,0,-1)),interval(0.001,genset_rt::infinity),h)
        || !close_value(h.t,0.5) || world.hit(ray(point3(0,0,0),vec3(0,1,0)),
                                            interval(0.001,genset_rt::infinity),h)) return 1;
    color pixels[32*24];
    {
        kernel_clock timer("Q1-hit-recursion");
        for(int y=0;y<24;++y) for(int x=0;x<width;++x)
            pixels[y*width+x]=trace(ray(point3(0,0,0),vec3((2*x+1-width)/32.0,
                                      (23-2*y)/32.0,-1)),world,5);
    }
    std::puts("Q1 32 24 5");
    for(int i=0;i<32*24;++i) for(int c=0;c<3;++c) value(pixels[i][c]);
    return std::ferror(stdout) ? 2 : 0;
}
