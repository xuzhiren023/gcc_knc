/* Minimal compatibility surface for the exact pinned musl reducer sources.
 * This is not a replacement public libm header or target runtime. */
#ifndef PHI_TRIG_REDUCER_LIBM_H
#define PHI_TRIG_REDUCER_LIBM_H
#include <float.h>
#include <stdint.h>
#define double_t phi_native_system_double_t
#define float_t phi_native_system_float_t
#include <math.h>
#undef float_t
#undef double_t
#if FLT_EVAL_METHOD == 0
typedef float float_t;
typedef double double_t;
#elif FLT_EVAL_METHOD == 1
typedef double float_t;
typedef double double_t;
#elif FLT_EVAL_METHOD == 2
typedef long double float_t;
typedef long double double_t;
#else
#error "Native reducer requires genuine FLT_EVAL_METHOD 0, 1 or 2"
#endif
#define predict_false(x) __builtin_expect(!!(x),0)
#define FORCE_EVAL(x) do { volatile double phi_force_eval=(x); (void)phi_force_eval; } while(0)
double phi_trig_scalbn(double,int);
double phi_trig_floor(double);
int phi_trig_rem_pio2_large(double *,double *,int,int,int);
int phi_trig_rem_pio2(double,double *);
#endif
