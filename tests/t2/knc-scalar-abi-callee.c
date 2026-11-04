#include "knc-scalar-abi.h"
float scalar_f(float x) { return x + 0.5f; }
double scalar_d(double x) { return x + 0.25; }
double scalar_mixed(int i, float f, long j, double d, int k, float g)
{ return i + 2*f + 4*j + 8*d + 16*k + 32*g; }
float scalar_ten_f(float a,float b,float c,float d,float e,float f,float g,float h,float i,float j)
{ return a + 2*b + 3*c + 4*d + 5*e + 6*f + 7*g + 8*h + 9*i + 10*j; }
double scalar_ten_d(double a,double b,double c,double d,double e,double f,double g,double h,double i,double j)
{ return a + 2*b + 3*c + 4*d + 5*e + 6*f + 7*g + 8*h + 9*i + 10*j; }
struct df scalar_df(struct df x) { x.d += 0.25; x.f += 0.5f; return x; }
struct ff scalar_ff(struct ff x) { x.a += 0.25f; x.b += 0.5f; return x; }
double scalar_callback(double (*fn)(double), double x) { return fn(x) + 0.5; }
