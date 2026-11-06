/* GCC DP8-vector adaptation of musl v1.2.5 __sin.c and __cos.c.
 * ====================================================
 * Copyright (C) 1993 by Sun Microsystems, Inc. All rights reserved.
 * Developed at SunSoft, a Sun Microsystems, Inc. business.
 * Permission to use, copy, modify, and distribute this software is freely
 * granted, provided that this notice is preserved.
 * ====================================================
 * Changes: scalar complete-domain official reduction, 8-DP vector polynomial,
 * lane classification/sanitization, integer quadrant selection and private
 * 64-byte raw pointer ABI. SP16 evaluates two DP8 groups and rounds once.
 * Source experiment only: target vector ABI/ISA/performance remain unqualified.
 */
#include "e_export_adapter.h"
#include <string.h>
#ifdef __FAST_MATH__
#error "cos_sin_e requires strict FP"
#endif
typedef double dv __attribute__((vector_size(64)));
int phi_trig_rem_pio2(double,double *);
static uint64_t dbits(double x){uint64_t b;memcpy(&b,&x,8);return b;}
static double dvalue(uint64_t b){double x;memcpy(&x,&b,8);return x;}

/* All actual polynomial arithmetic is GCC-vector arithmetic. Per-lane range
 * reduction supplies high/low parts and quadrant, never a trig result. */
static __attribute__((noinline)) void finite_core(const double input[8],uint64_t output[8]) {
  dv x,y;unsigned quadrant[8],small[8];
  for(unsigned i=0;i<8;++i) {
    uint64_t mag=dbits(input[i])&UINT64_C(0x7fffffffffffffff);
    small[i]=mag<UINT64_C(0x3e40000000000000); /* <2^-27 */
    quadrant[i]=0;x[i]=small[i]?0:input[i];y[i]=0;
    if(mag>UINT64_C(0x3fe921fb54442d18)) {
      double reduced[2];quadrant[i]=(unsigned)phi_trig_rem_pio2(input[i],reduced)&3;
      x[i]=reduced[0];y[i]=reduced[1];
    }
  }
  const dv z=x*x,w=z*z;
  const dv sr=8.33333333332248946124e-03+z*(-1.98412698298579493134e-04+z*2.75573137070700676789e-06)
       +z*w*(-2.50507602534068634195e-08+z*1.58969099521155010221e-10);
  const dv v=z*x;
  const dv s=x-((z*(.5*y-v*sr)-y)-v*(-1.66666666666666324348e-01));
  const dv cr=z*(4.16666666666666019037e-02+z*(-1.38888888888741095749e-03+z*2.48015872894767294178e-05))
       +w*w*(-2.75573143513906633035e-07+z*(2.08757232129817482790e-09+z*(-1.13596475577881948265e-11)));
  const dv hz=.5*z,cw=1-hz,c=cw+(((1-cw)-hz)+(z*cr-x*y));
  uint64_t sine_bits[8] __attribute__((aligned(64))), cosine_bits[8] __attribute__((aligned(64)));
  memcpy(sine_bits,&s,64);memcpy(cosine_bits,&c,64);
  /* Exact integer selection; volatile integer loads keep the scalar bit
   * boundary explicit instead of GCC introducing a YMM FP blend/sign XOR. */
  const volatile uint64_t *sword=sine_bits,*cword=cosine_bits;
  for(unsigned i=0;i<8;++i) {
    unsigned q=(quadrant[i]+1u)&3u;
    uint64_t select=UINT64_C(0)-(uint64_t)(q&1u);
    uint64_t b=(sword[i]&~select)|(cword[i]&select);
    b^=(uint64_t)(q&2u)<<62;
    uint64_t tiny=UINT64_C(0)-(uint64_t)small[i];
    output[i]=(b&~tiny)|(UINT64_C(0x3ff0000000000000)&tiny);
  }
}
static int apply_dp(const uint64_t input[8],unsigned mask,const uint64_t merge[8],uint64_t output[8]) {
  if(mask&~255u)return 1;
  uint64_t saved[8],pass[8],out[8];double values[8];unsigned exceptional=0;
  memcpy(saved,input,64);memcpy(pass,merge,64);
  if(!mask){memcpy(output,pass,64);return 0;}
  for(unsigned i=0;i<8;++i) {
    uint64_t mag=saved[i]&UINT64_C(0x7fffffffffffffff);
    if((mask&(1u<<i))&&mag>=UINT64_C(0x7ff0000000000000))exceptional|=1u<<i;
    values[i]=((mask&(1u<<i))&&!(exceptional&(1u<<i)))?dvalue(saved[i]):0;
  }
  finite_core(values,out);
  if(exceptional) {
    dv a={0};for(unsigned i=0;i<8;++i)if(exceptional&(1u<<i))a[i]=dvalue(saved[i]);
    const dv nan=a-a;uint64_t bits[8];memcpy(bits,&nan,64);
    for(unsigned i=0;i<8;++i)if(exceptional&(1u<<i))out[i]=bits[i];
  }
  for(unsigned i=0;i<8;++i)if(!(mask&(1u<<i)))out[i]=pass[i];memcpy(output,out,64);return 0;
}

/* DP cosine only. Finite polynomial/reduction expressions, tiny and nonfinite
 * behavior match the preserved host-checked cos_sin_e.c; target unqualified. */
int knc_mvec_algorithm_cos_i64_e8(const uint64_t x[8],unsigned m,const uint64_t p[8],uint64_t o[8]) {
  return apply_dp(x,m,p,o);
}
KNC_MVEC_E_EXPORT(__knc_vmath_cos_8,knc_mvec_f64x8,uint64_t,8,knc_mvec_algorithm_cos_i64_e8)
