/* E16 GCC-vector adaptation of Arm optimized-routines powf.c and data,
 * commit649ccc8411e7c4862965710f25c570d854a1483f, v26.01.
 * Copyright (c)2017-2025, Arm Limited. SPDX-License-Identifier: MIT
 * Modifications:16 lanes, integer special classification, sanitized exceptional
 * lanes, private pointer/software-mask ABI, no scalar powf delegation.
 * Nearest-even, masked FP exceptions and FTZ/DAZ off only. Not target proof. */
#include "powf_e16.h"
#include "math_config.h"
#include <string.h>
#ifdef __FAST_MATH__
#error "powf_e16 requires strict floating point"
#endif
typedef float fv __attribute__((vector_size(64)));
typedef double dv __attribute__((vector_size(128)));
typedef uint32_t uv __attribute__((vector_size(64)));
typedef int32_t iv __attribute__((vector_size(64)));

/* Integer-only parity classification, valid for every finite nonzero y. */
static unsigned integer_kind(uint32_t iy) {
  unsigned e=(iy>>23)&255;
  if(e<127)return 0;
  if(e>150)return 2;
  unsigned shift=150-e;
  if(iy&((UINT32_C(1)<<shift)-1))return 0;
  return (iy&(UINT32_C(1)<<shift))?1:2;
}
static unsigned snan(uint32_t w) {
  return (w&UINT32_C(0x7fffffff))>UINT32_C(0x7f800000) && !(w&UINT32_C(0x00400000));
}

static __attribute__((noinline)) void core(const uint32_t x[16],const uint32_t y[16],uint32_t output[16]) {
  uint32_t ax[16],ay[16],norm[16],sign[16]={0},special[16]={0};
  unsigned direct=0,nans=0,invalid=0,divzero=0,subnormal=0;
  for(unsigned i=0;i<16;++i) {
    const uint32_t xb=x[i],yb=y[i],xm=xb&UINT32_C(0x7fffffff),ym=yb&UINT32_C(0x7fffffff);
    ax[i]=UINT32_C(0x3f800000);ay[i]=0;norm[i]=UINT32_C(0x3f800000);
    if(!ym) { /* x^0=1 except a signaling NaN. */
      if(snan(xb))nans|=1u<<i;else {direct|=1u<<i;special[i]=UINT32_C(0x3f800000);}continue;
    }
    if(xb==UINT32_C(0x3f800000)) {
      if(snan(yb))nans|=1u<<i;else {direct|=1u<<i;special[i]=UINT32_C(0x3f800000);}continue;
    }
    if(xm>UINT32_C(0x7f800000) || ym>UINT32_C(0x7f800000)) {nans|=1u<<i;continue;}
    if(ym==UINT32_C(0x7f800000)) {
      direct|=1u<<i;
      special[i]=xm==UINT32_C(0x3f800000)?UINT32_C(0x3f800000):
        ((xm<UINT32_C(0x3f800000))==!(yb>>31)?0:UINT32_C(0x7f800000));
      continue;
    }
    const unsigned kind=integer_kind(yb),negative=(xb>>31)&&(kind==1);
    sign[i]=negative?UINT32_C(0x80000000):0;
    if(!xm || xm==UINT32_C(0x7f800000)) {
      direct|=1u<<i;
      special[i]=sign[i]|((!xm)==!(yb>>31)?0:UINT32_C(0x7f800000));
      if(!xm && (yb>>31))divzero|=1u<<i;
      continue;
    }
    if((xb>>31) && !kind) {invalid|=1u<<i;continue;}
    ax[i]=xm;ay[i]=yb;
    if(xm<UINT32_C(0x00800000)) {subnormal|=1u<<i;norm[i]=xm;}
  }
  if(subnormal) {
    fv n;memcpy(&n,norm,64);const fv scaled=n*0x1p23f;uint32_t bits[16];memcpy(bits,&scaled,64);
    for(unsigned i=0;i<16;++i)if(subnormal&(1u<<i))ax[i]=bits[i]-(23u<<23);
  }
  uv ix;memcpy(&ix,ax,64);
  const uv tmp=ix-UINT32_C(0x3f330000),top=tmp&UINT32_C(0xff800000),index=(tmp>>19)&15,iz=ix-top;
  iv signed_top;memcpy(&signed_top,&top,64);const iv k=signed_top>>23;
  fv zf,yf;memcpy(&zf,&iz,64);memcpy(&yf,ay,64);
  const dv z=__builtin_convertvector(zf,dv),yd=__builtin_convertvector(yf,dv);
  dv invc,logc;
  for(unsigned i=0;i<16;++i) {invc[i]=__powf_log2_data.tab[index[i]].invc;logc[i]=__powf_log2_data.tab[index[i]].logc;}
  const dv r=z*invc-1,y0=logc+__builtin_convertvector(k,dv),r2=r*r,r4=r2*r2;
  const dv p0=__powf_log2_data.poly[0]*r+__powf_log2_data.poly[1];
  const dv p1=__powf_log2_data.poly[2]*r+__powf_log2_data.poly[3];
  const dv q0=__powf_log2_data.poly[4]*r+y0,q1=p1*r2+q0;
  const dv log2x=p0*r4+q1;
  dv exponent=yd*log2x;
  unsigned overflow=0,underflow=0;
  for(unsigned i=0;i<16;++i) {
    if(exponent[i]>0x1.fffffffd1d571p+6) {overflow|=1u<<i;exponent[i]=0;}
    else if(exponent[i]<=-150.0) {underflow|=1u<<i;exponent[i]=0;}
  }
  dv kd=exponent+__exp2f_data.shift_scaled;uint64_t ki[16];memcpy(ki,&kd,sizeof kd);
  kd-=__exp2f_data.shift_scaled;
  const dv er=exponent-kd,er2=er*er;
  dv scale;
  for(unsigned i=0;i<16;++i) {
    const uint64_t bias=sign[i]?UINT64_C(65536):0;
    uint64_t bits=__exp2f_data.tab[ki[i]&31]+((ki[i]+bias)<<47);
    memcpy(&scale[i],&bits,8);
  }
  const dv ep=__exp2f_data.poly[0]*er+__exp2f_data.poly[1];
  const dv eq=__exp2f_data.poly[2]*er+1;
  const dv approximation=(ep*er2+eq)*scale;
  const fv result=__builtin_convertvector(approximation,fv);memcpy(output,&result,64);
  /* Exceptional arithmetic uses only marked lanes; no inactive poison enters
   * an FP expression. Volatile factors prevent constant-folded exceptions. */
  if(nans) {
    uint32_t nx[16]={0},ny[16]={0};for(unsigned i=0;i<16;++i)if(nans&(1u<<i)){nx[i]=x[i];ny[i]=y[i];}
    fv a,b;memcpy(&a,nx,64);memcpy(&b,ny,64);const fv c=a+b;uint32_t w[16];memcpy(w,&c,64);
    for(unsigned i=0;i<16;++i)if(nans&(1u<<i))output[i]=w[i];
  }
  if(invalid) {
    fv a=(fv){0},b=(fv){0}+1;for(unsigned i=0;i<16;++i)if(invalid&(1u<<i))b[i]=0;
    const fv c=a/b;uint32_t w[16];memcpy(w,&c,64);
    for(unsigned i=0;i<16;++i)if(invalid&(1u<<i))output[i]=w[i];
  }
  if(divzero) {
    volatile float one=1.0f;fv a=(fv){0}+1,b=(fv){0}+1;
    for(unsigned i=0;i<16;++i)if(divzero&(1u<<i)){a[i]=sign[i]?-one:one;b[i]=0;}
    const fv c=a/b;uint32_t w[16];memcpy(w,&c,64);
    for(unsigned i=0;i<16;++i)if(divzero&(1u<<i))special[i]=w[i];
  }
  if(overflow || underflow) {
    volatile float large=0x1p97f,small=0x1p-95f;
    fv a=(fv){0}+1,b=(fv){0}+1;
    for(unsigned i=0;i<16;++i) {
      if(overflow&(1u<<i)){a[i]=sign[i]?-large:large;b[i]=large;}
      if(underflow&(1u<<i)){a[i]=sign[i]?-small:small;b[i]=small;}
    }
    const fv c=a*b;uint32_t w[16];memcpy(w,&c,64);
    for(unsigned i=0;i<16;++i)if((overflow|underflow)&(1u<<i))output[i]=w[i];
  }
  for(unsigned i=0;i<16;++i)if(direct&(1u<<i))output[i]=special[i];
}

/* Full64-byte readable buffers; exact x/out, y/out and merge/out aliases are
 * supported. Partial overlaps are outside this private experimental ABI. */
int phi_host_powf_e16(const uint32_t x[16],const uint32_t y[16],unsigned active,
                     const uint32_t merge[16],uint32_t output[16]) {
  if(active&~65535u)return 1;
  uint32_t ax[16],ay[16],pass[16],value[16];
  memcpy(ax,x,64);memcpy(ay,y,64);memcpy(pass,merge,64);
  if(!active){memcpy(output,pass,64);return 0;}
  for(unsigned i=0;i<16;++i)if(!(active&(1u<<i))){ax[i]=UINT32_C(0x3f800000);ay[i]=0;}
  core(ax,ay,value);
  for(unsigned i=0;i<16;++i)if(!(active&(1u<<i)))value[i]=pass[i];
  memcpy(output,value,64);return 0;
}
