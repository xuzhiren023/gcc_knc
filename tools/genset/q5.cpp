// Original MIT smallpt is unmodified; replace only its large example main.
// The example uses POSIX erand48 and the math constants extension.
#define _XOPEN_SOURCE 700
#define _DEFAULT_SOURCE 1
#define main upstream_smallpt_main
#include "smallpt.cpp"
#undef main
#include "common.h"
int main() {
    Vec pixels[16*12];
    {
        kernel_clock timer("Q5-radiance");
        for(int y=0;y<12;++y) for(int x=0;x<16;++x) {
            unsigned short seed[3]={17,23,(unsigned short)(x+16*y+1)};
            Vec direction((x-7.5)/24.0,(y-5.5)/24.0-0.042612,-1);
            pixels[y*16+x]=radiance(Ray(Vec(50,52,295.6),direction.norm()),0,seed);
        }
    }
    std::puts("Q5 16 12 1 17 23");
    for(int i=0;i<16*12;++i) { value(pixels[i].x); value(pixels[i].y); value(pixels[i].z); }
    return std::ferror(stdout) ? 2 : 0;
}
