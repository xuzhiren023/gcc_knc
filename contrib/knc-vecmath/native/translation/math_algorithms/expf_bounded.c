/* Adapted from Arm optimized-routines v26.01 math/expf.c, exp2f_data.c.
 * Copyright (c) 2017-2025, Arm Limited.
 * SPDX-License-Identifier: MIT
 * Upstream commit 649ccc8411e7c4862965710f25c570d854a1483f.
 * Full upstream license and exact original sources are retained in
 * native/upstream/arm-optimized-routines-v26.01/.
 * Adaptation: four-lane GCC arithmetic, fixed N=32, bounded finite domain,
 * double intermediates; no exceptional-lane path or scalar libm fallback.
 */
#include "bounded_f32.h"
#include <string.h>
typedef float f32x4 __attribute__((vector_size(16)));
typedef double f64x4 __attribute__((vector_size(32)));
typedef uint64_t u64x4 __attribute__((vector_size(32)));

static const uint64_t table[32] = {
  0x3ff0000000000000, 0x3fefd9b0d3158574, 0x3fefb5586cf9890f, 0x3fef9301d0125b51,
  0x3fef72b83c7d517b, 0x3fef54873168b9aa, 0x3fef387a6e756238, 0x3fef1e9df51fdee1,
  0x3fef06fe0a31b715, 0x3feef1a7373aa9cb, 0x3feedea64c123422, 0x3feece086061892d,
  0x3feebfdad5362a27, 0x3feeb42b569d4f82, 0x3feeab07dd485429, 0x3feea47eb03a5585,
  0x3feea09e667f3bcd, 0x3fee9f75e8ec5f74, 0x3feea11473eb0187, 0x3feea589994cce13,
  0x3feeace5422aa0db, 0x3feeb737b0cdc5e5, 0x3feec49182a3f090, 0x3feed503b23e255d,
  0x3feee89f995ad3ad, 0x3feeff76f2fb5e47, 0x3fef199bdd85529c, 0x3fef3720dcef9069,
  0x3fef5818dcfba487, 0x3fef7c97337b9b5f, 0x3fefa4afa2a490da, 0x3fefd0765b6e4540
};

int phi_expf_bounded4(const uint32_t in[4], uint32_t out[4]) {
  for (unsigned i=0; i<4; ++i)
    if ((in[i] & UINT32_C(0x7fffffff)) > UINT32_C(0x42a00000)) return 1;
  f32x4 x; memcpy(&x, in, sizeof x);
  const f64x4 xd=__builtin_convertvector(x, f64x4);
  f64x4 z=xd*(0x1.71547652b82fep+0*32);
  f64x4 kd=z+0x1.8p+52;
  u64x4 ki; memcpy(&ki, &kd, sizeof ki);
  kd=kd-0x1.8p+52;
  const f64x4 r=z-kd;
  u64x4 t={table[ki[0]&31],table[ki[1]&31],table[ki[2]&31],table[ki[3]&31]};
  t=t+(ki<<47);
  f64x4 s; memcpy(&s, &t, sizeof s);
  z=(0x1.c6af84b912394p-5/32/32/32)*r+(0x1.ebfce50fac4f3p-3/32/32);
  const f64x4 r2=r*r;
  f64x4 y=(0x1.62e42ff0c52d6p-1/32)*r+1;
  y=z*r2+y;
  y=y*s;
  const f32x4 result=__builtin_convertvector(y, f32x4);
  memcpy(out, &result, sizeof result);
  return 0;
}
