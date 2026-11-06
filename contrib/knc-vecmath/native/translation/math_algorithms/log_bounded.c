/* Four-lane adaptation of Arm optimized-routines v26.01 math/log.c.
 * Copyright (c) 2018-2025, Arm Limited.
 * SPDX-License-Identifier: MIT
 * Commit 649ccc8411e7c4862965710f25c570d854a1483f. Exact upstream log_data.c
 * provides all coefficients/tables. Always use its split-c (non-explicit-FMA)
 * reduction for both host contraction policies, with its separate near-one
 * compensated polynomial. Unsupported lanes are rejected, never sent to libm.
 */
#include "bounded_f64.h"
#include "../../upstream/arm-optimized-routines-v26.01-dp/math/math_config.h"
#include <string.h>
typedef double f64x4 __attribute__((vector_size(32)));
typedef uint64_t u64x4 __attribute__((vector_size(32)));
typedef int64_t i64x4 __attribute__((vector_size(32)));
_Static_assert(LOG_TABLE_BITS==7 && LOG_POLY_ORDER==6 && LOG_POLY1_ORDER==12 && HAVE_FAST_FMA==0,"unsupported upstream configuration");

int phi_log_bounded4(const uint64_t in[4],uint64_t out[4]) {
  uint64_t nearbits[4],farbits[4];u64x4 near={0,0,0,0};
  for(unsigned i=0;i<4;++i) {
    if(in[i]<UINT64_C(0x0010000000000000) || in[i]>=UINT64_C(0x7ff0000000000000))return 1;
    near[i]=in[i]-UINT64_C(0x3fee000000000000)<UINT64_C(0x3ff1090000000000)-UINT64_C(0x3fee000000000000)?UINT64_MAX:0;
    nearbits[i]=near[i]?in[i]:UINT64_C(0x3ff0000000000000);
    farbits[i]=near[i]?UINT64_C(0x3ff0000000000000):in[i];
  }
  f64x4 x;memcpy(&x,nearbits,sizeof x);
  f64x4 r=x-1,r2=r*r,r3=r*r2;
  const double *B=__log_data.poly1;
  f64x4 y=r3*(B[1]+r*B[2]+r2*B[3]+r3*(B[4]+r*B[5]+r2*B[6]+r3*(B[7]+r*B[8]+r2*B[9]+r3*B[10])));
  f64x4 w=r*0x1p27;
  const f64x4 rhi=r+w-w,rlo=r-rhi;
  w=rhi*rhi*B[0];f64x4 hi=r+w,lo=r-hi+w;
  lo=lo+B[0]*rlo*(rhi+r);y=y+lo;y=y+hi;
  const f64x4 near_result=y;
  u64x4 ix;memcpy(&ix,farbits,sizeof ix);
  const u64x4 tmp=ix-UINT64_C(0x3fe6000000000000);
  const u64x4 index=(tmp>>45)&127;
  i64x4 stmp;memcpy(&stmp,&tmp,sizeof tmp);const i64x4 k=stmp>>52;
  const u64x4 iz=ix-(tmp&UINT64_C(0xfff0000000000000));
  f64x4 z;memcpy(&z,&iz,sizeof z);
  const f64x4 invc={__log_data.tab[index[0]].invc,__log_data.tab[index[1]].invc,__log_data.tab[index[2]].invc,__log_data.tab[index[3]].invc};
  const f64x4 logc={__log_data.tab[index[0]].logc,__log_data.tab[index[1]].logc,__log_data.tab[index[2]].logc,__log_data.tab[index[3]].logc};
  const f64x4 chi={__log_data.tab2[index[0]].chi,__log_data.tab2[index[1]].chi,__log_data.tab2[index[2]].chi,__log_data.tab2[index[3]].chi};
  const f64x4 clo={__log_data.tab2[index[0]].clo,__log_data.tab2[index[1]].clo,__log_data.tab2[index[2]].clo,__log_data.tab2[index[3]].clo};
  r=(z-chi-clo)*invc;
  const f64x4 kd=__builtin_convertvector(k,f64x4);
  w=kd*__log_data.ln2hi+logc;hi=w+r;lo=w-hi+r+kd*__log_data.ln2lo;
  r2=r*r;const double *A=__log_data.poly;
  y=lo+r2*A[0]+r*r2*(A[1]+r*A[2]+r2*(A[3]+r*A[4]))+hi;
  u64x4 nb,fb;memcpy(&nb,&near_result,sizeof nb);memcpy(&fb,&y,sizeof fb);
  const u64x4 result=(near&nb)|(~near&fb);memcpy(out,&result,sizeof result);return 0;
}
