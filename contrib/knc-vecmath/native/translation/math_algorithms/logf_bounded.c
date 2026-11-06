/* Adapted from Arm optimized-routines v26.01 math/logf.c, logf_data.c.
 * Copyright (c) 2017-2025, Arm Limited.
 * SPDX-License-Identifier: MIT
 * Upstream commit 649ccc8411e7c4862965710f25c570d854a1483f.
 * Full upstream license and unmodified originals: native/upstream/
 * arm-optimized-routines-v26.01/. Fixed N=16 and degree-four polynomial,
 * GCC vector arithmetic with double intermediates, positive normals only.
 * No exceptional-lane handling or scalar libm fallback.
 */
#include "logf_bounded.h"
#include <string.h>
typedef float f32x4 __attribute__((vector_size(16)));
typedef double f64x4 __attribute__((vector_size(32)));
typedef uint32_t u32x4 __attribute__((vector_size(16)));
typedef int32_t i32x4 __attribute__((vector_size(16)));
static const struct { double invc,logc; } table[16]={
  {0x1.661ec79f8f3bep+0,-0x1.57bf7808caadep-2},
  {0x1.571ed4aaf883dp+0,-0x1.2bef0a7c06ddbp-2},
  {0x1.49539f0f010bp+0,-0x1.01eae7f513a67p-2},
  {0x1.3c995b0b80385p+0,-0x1.b31d8a68224e9p-3},
  {0x1.30d190c8864a5p+0,-0x1.6574f0ac07758p-3},
  {0x1.25e227b0b8eap+0,-0x1.1aa2bc79c81p-3},
  {0x1.1bb4a4a1a343fp+0,-0x1.a4e76ce8c0e5ep-4},
  {0x1.12358f08ae5bap+0,-0x1.1973c5a611cccp-4},
  {0x1.0953f419900a7p+0,-0x1.252f438e10c1ep-5},
  {0x1p+0,0x0p+0},
  {0x1.e608cfd9a47acp-1,0x1.aa5aa5df25984p-5},
  {0x1.ca4b31f026aap-1,0x1.c5e53aa362eb4p-4},
  {0x1.b2036576afce6p-1,0x1.526e57720db08p-3},
  {0x1.9c2d163a1aa2dp-1,0x1.bc2860d22477p-3},
  {0x1.886e6037841edp-1,0x1.1058bc8a07ee1p-2},
  {0x1.767dcf5534862p-1,0x1.4043057b6ee09p-2}
};

int phi_logf_bounded4(const uint32_t in[4],uint32_t out[4]) {
  for(unsigned lane=0;lane<4;++lane)
    if(in[lane]<UINT32_C(0x00800000) || in[lane]>=UINT32_C(0x7f800000))return 1;
  u32x4 ix;memcpy(&ix,in,sizeof ix);
  const u32x4 tmp=ix-UINT32_C(0x3f330000);
  const u32x4 index=(tmp>>19)&15;
  i32x4 signed_tmp;memcpy(&signed_tmp,&tmp,sizeof tmp);
  const i32x4 k=signed_tmp>>23;
  const u32x4 iz=ix-(tmp&UINT32_C(0xff800000));
  f32x4 zf;memcpy(&zf,&iz,sizeof zf);
  const f64x4 z=__builtin_convertvector(zf,f64x4);
  const f64x4 invc={table[index[0]].invc,table[index[1]].invc,table[index[2]].invc,table[index[3]].invc};
  const f64x4 logc={table[index[0]].logc,table[index[1]].logc,table[index[2]].logc,table[index[3]].logc};
  const f64x4 r=z*invc-1;
  const f64x4 y0=logc+__builtin_convertvector(k,f64x4)*0x1.62e42fefa39efp-1;
  const f64x4 r2=r*r;
  f64x4 y=0x1.5575b0be00b6ap-2*r+(-0x1.ffffef20a4123p-2);
  y=(-0x1.00ea348b88334p-2)*r2+y;
  y=y*r2+(y0+r);
  f32x4 result=__builtin_convertvector(y,f32x4);
  memcpy(out,&result,sizeof result);
  return 0;
}
