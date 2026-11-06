/* Minimal compatibility surface for the exact pinned musl reducer sources.
 * This is not a replacement public libm header or target runtime. */
#ifndef PHI_TRIG_REDUCER_LIBM_H
#define PHI_TRIG_REDUCER_LIBM_H
#include <float.h>
#include <stdint.h>
#include <math.h>
#if FLT_EVAL_METHOD != 0
#error "This source experiment requires binary64 evaluation (FLT_EVAL_METHOD=0)"
#endif
#define predict_false(x) __builtin_expect(!!(x),0)
#define FORCE_EVAL(x) do { volatile double phi_force_eval=(x); (void)phi_force_eval; } while(0)
double phi_trig_scalbn(double,int);
double phi_trig_floor(double);
int phi_trig_rem_pio2_large(double *,double *,int,int,int);
int phi_trig_rem_pio2(double,double *);
#endif
