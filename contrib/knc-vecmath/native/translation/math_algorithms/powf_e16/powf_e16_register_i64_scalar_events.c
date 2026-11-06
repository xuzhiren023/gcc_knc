/* Additive source-only scalar-event experiment. Only the invalid/divzero
 * event blocks change from powf_e16_register_i64.c, apart from private names
 * and this provenance note. The inherited parent provenance comments below
 * describe that earlier variant. No host accuracy, ISA, event/flag, target ABI
 * or G5 proof is inherited; one fresh strict compile and target assay remain
 * required. Scalar volatile division executes only inside marked-lane branches.
 */
/* Additive i64 predicate/table-motion variant. All original finite FP
 * expressions, conversion expressions and special-event blocks are retained.
 * Integer vectors are at most64B; the original128B FP dv carrier is unchanged
 * to preserve sixteen-lane conversion expressions. Private full64B volatile
 * integer fold stages do not access an FP environment API or clear status.
 * No emitted-ISA, host accuracy, target ABI or G5 qualification is inherited. */
/* Additive source-only powf register-table candidate. Original source/export,
 * host evidence and qualified helpers remain unchanged. No accuracy, target
 * ISA, exception, mask or ABI qualification is inherited. */
/* E16 GCC-vector adaptation of Arm optimized-routines powf.c and data,
 * commit649ccc8411e7c4862965710f25c570d854a1483f, v26.01.
 * Copyright (c)2017-2025, Arm Limited. SPDX-License-Identifier: MIT
 * Modifications:16 lanes, integer special classification, sanitized exceptional
 * lanes, private pointer/software-mask ABI, no scalar powf delegation.
 * Nearest-even, masked FP exceptions and FTZ/DAZ off only. Not target proof. */
#include "powf_e16_register_i64_scalar_events.h"
#include "math_config.h"
#include <string.h>
#if defined(__FAST_MATH__) || HAVE_FAST_FMA || HAVE_FAST_ROUND
#error "powf register candidate requires original strict non-FMA/non-toint configuration"
#endif
_Static_assert(POWF_LOG2_TABLE_BITS==4 && POWF_LOG2_POLY_ORDER==5 &&
  EXP2F_TABLE_BITS==5 && EXP2F_POLY_ORDER==3 && POWF_SCALE_BITS==0,
  "unsupported pinned powf table configuration");
typedef float fv __attribute__((vector_size(64)));
typedef double dv __attribute__((vector_size(128)));
typedef uint32_t uv __attribute__((vector_size(64)));
typedef int32_t iv __attribute__((vector_size(64)));

/* Exact binary64/uint64 words from the pinned Arm data sources.
 * Each lookup uses native8-qword chunks; no table word is truncated to SP. */
typedef unsigned long long qv __attribute__((vector_size(64)));
typedef long long v8di __attribute__((vector_size(64)));
static const qv pw_powf_invc_0 __attribute__((aligned(64))) = {
  UINT64_C(0x3ff661ec79f8f3be), UINT64_C(0x3ff571ed4aaf883d), UINT64_C(0x3ff49539f0f010b0), UINT64_C(0x3ff3c995b0b80385), UINT64_C(0x3ff30d190c8864a5), UINT64_C(0x3ff25e227b0b8ea0), UINT64_C(0x3ff1bb4a4a1a343f), UINT64_C(0x3ff12358f08ae5ba)
};
static const qv pw_powf_invc_1 __attribute__((aligned(64))) = {
  UINT64_C(0x3ff0953f419900a7), UINT64_C(0x3ff0000000000000), UINT64_C(0x3fee608cfd9a47ac), UINT64_C(0x3feca4b31f026aa0), UINT64_C(0x3feb2036576afce6), UINT64_C(0x3fe9c2d163a1aa2d), UINT64_C(0x3fe886e6037841ed), UINT64_C(0x3fe767dcf5534862)
};
static const qv pw_powf_logc_0 __attribute__((aligned(64))) = {
  UINT64_C(0xbfdefec65b963019), UINT64_C(0xbfdb0b6832d4fca4), UINT64_C(0xbfd7418b0a1fb77b), UINT64_C(0xbfd39de91a6dcf7b), UINT64_C(0xbfd01d9bf3f2b631), UINT64_C(0xbfc97c1d1b3b7af0), UINT64_C(0xbfc2f9e393af3c9f), UINT64_C(0xbfb960cbbf788d5c)
};
static const qv pw_powf_logc_1 __attribute__((aligned(64))) = {
  UINT64_C(0xbfaa6f9db6475fce), UINT64_C(0x0000000000000000), UINT64_C(0x3fb338ca9f24f53d), UINT64_C(0x3fc476a9543891ba), UINT64_C(0x3fce840b4ac4e4d2), UINT64_C(0x3fd40645f0c6651c), UINT64_C(0x3fd88e9c2c1b9ff8), UINT64_C(0x3fdce0a44eb17bcc)
};
static const qv pw_powf_exp_scale_0 __attribute__((aligned(64))) = {
  UINT64_C(0x3ff0000000000000), UINT64_C(0x3fefd9b0d3158574), UINT64_C(0x3fefb5586cf9890f), UINT64_C(0x3fef9301d0125b51), UINT64_C(0x3fef72b83c7d517b), UINT64_C(0x3fef54873168b9aa), UINT64_C(0x3fef387a6e756238), UINT64_C(0x3fef1e9df51fdee1)
};
static const qv pw_powf_exp_scale_1 __attribute__((aligned(64))) = {
  UINT64_C(0x3fef06fe0a31b715), UINT64_C(0x3feef1a7373aa9cb), UINT64_C(0x3feedea64c123422), UINT64_C(0x3feece086061892d), UINT64_C(0x3feebfdad5362a27), UINT64_C(0x3feeb42b569d4f82), UINT64_C(0x3feeab07dd485429), UINT64_C(0x3feea47eb03a5585)
};
static const qv pw_powf_exp_scale_2 __attribute__((aligned(64))) = {
  UINT64_C(0x3feea09e667f3bcd), UINT64_C(0x3fee9f75e8ec5f74), UINT64_C(0x3feea11473eb0187), UINT64_C(0x3feea589994cce13), UINT64_C(0x3feeace5422aa0db), UINT64_C(0x3feeb737b0cdc5e5), UINT64_C(0x3feec49182a3f090), UINT64_C(0x3feed503b23e255d)
};
static const qv pw_powf_exp_scale_3 __attribute__((aligned(64))) = {
  UINT64_C(0x3feee89f995ad3ad), UINT64_C(0x3feeff76f2fb5e47), UINT64_C(0x3fef199bdd85529c), UINT64_C(0x3fef3720dcef9069), UINT64_C(0x3fef5818dcfba487), UINT64_C(0x3fef7c97337b9b5f), UINT64_C(0x3fefa4afa2a490da), UINT64_C(0x3fefd0765b6e4540)
};

static __attribute__((always_inline)) inline qv pw_powf_lookup_invc(qv key) {
  const qv keys=key&UINT64_C(15),group=keys>>3;
  const v8di selector=(v8di)(keys&UINT64_C(7));
  qv result={0};
  {
    const qv keep=(qv)(group==UINT64_C(0));
    result|=__builtin_shuffle(pw_powf_invc_0,selector)&keep;
  }
  {
    const qv keep=(qv)(group==UINT64_C(1));
    result|=__builtin_shuffle(pw_powf_invc_1,selector)&keep;
  }
  return result;
}

static __attribute__((always_inline)) inline qv pw_powf_lookup_logc(qv key) {
  const qv keys=key&UINT64_C(15),group=keys>>3;
  const v8di selector=(v8di)(keys&UINT64_C(7));
  qv result={0};
  {
    const qv keep=(qv)(group==UINT64_C(0));
    result|=__builtin_shuffle(pw_powf_logc_0,selector)&keep;
  }
  {
    const qv keep=(qv)(group==UINT64_C(1));
    result|=__builtin_shuffle(pw_powf_logc_1,selector)&keep;
  }
  return result;
}

static __attribute__((always_inline)) inline qv pw_powf_lookup_exp_scale(qv key) {
  const qv keys=key&UINT64_C(31),group=keys>>3;
  const v8di selector=(v8di)(keys&UINT64_C(7));
  qv result={0};
  {
    const qv keep=(qv)(group==UINT64_C(0));
    result|=__builtin_shuffle(pw_powf_exp_scale_0,selector)&keep;
  }
  {
    const qv keep=(qv)(group==UINT64_C(1));
    result|=__builtin_shuffle(pw_powf_exp_scale_1,selector)&keep;
  }
  {
    const qv keep=(qv)(group==UINT64_C(2));
    result|=__builtin_shuffle(pw_powf_exp_scale_2,selector)&keep;
  }
  {
    const qv keep=(qv)(group==UINT64_C(3));
    result|=__builtin_shuffle(pw_powf_exp_scale_3,selector)&keep;
  }
  return result;
}

static __attribute__((always_inline)) inline void
pw_powf_log_register_lookup(uv index,dv *invc,dv *logc) {
  uint32_t indices[16];uint64_t invc_words[16],logc_words[16];
  memcpy(indices,&index,64);
  for(unsigned chunk=0;chunk<2;++chunk) {
    const qv keys={(uint64_t)indices[chunk*8+0],(uint64_t)indices[chunk*8+1],(uint64_t)indices[chunk*8+2],(uint64_t)indices[chunk*8+3],(uint64_t)indices[chunk*8+4],(uint64_t)indices[chunk*8+5],(uint64_t)indices[chunk*8+6],(uint64_t)indices[chunk*8+7]};
    const qv a=pw_powf_lookup_invc(keys),b=pw_powf_lookup_logc(keys);
    memcpy(invc_words+chunk*8,&a,64);memcpy(logc_words+chunk*8,&b,64);
  }
  memcpy(invc,invc_words,128);memcpy(logc,logc_words,128);
}

static __attribute__((always_inline)) inline void
pw_powf_exp_register_lookup(const uint64_t ki[16],const uint32_t sign[16],dv *scale) {
  uint64_t words[16];
  for(unsigned chunk=0;chunk<2;++chunk) {
    qv keys;memcpy(&keys,ki+chunk*8,64);
    const qv signs={(uint64_t)sign[chunk*8+0],(uint64_t)sign[chunk*8+1],(uint64_t)sign[chunk*8+2],(uint64_t)sign[chunk*8+3],(uint64_t)sign[chunk*8+4],(uint64_t)sign[chunk*8+5],(uint64_t)sign[chunk*8+6],(uint64_t)sign[chunk*8+7]};
    const qv bias=(qv)(signs!=UINT64_C(0))&UINT64_C(65536);
    const qv value=pw_powf_lookup_exp_scale(keys)+((keys+bias)<<47);
    memcpy(words+chunk*8,&value,64);
  }
  memcpy(scale,words,128);
}

static uv pw_powf_lane_mask(unsigned active) {
  const uv lanes={1u,2u,4u,8u,16u,32u,64u,128u,256u,512u,1024u,2048u,4096u,8192u,16384u,32768u};
  const uv requested=(uv){0}+(uint32_t)active;
  return (uv)((requested&lanes)!=UINT32_C(0));
}


/* A predicate is one full qword per original lane. Only bits0..15 may
 * be set. Combining the two chunks preserves the sixteen-lane mask.
 * Volatile full64B stages make each qword shuffle/OR result observable as
 * a complete integer vector; they prevent exposing the former DWORD
 * horizontal-reduction idiom. These are private integer stores/loads only.
 * Actual emitted byte-SIMD absence remains a fresh compiler obligation. */
static unsigned pw_powf_fold_predicate_i64(qv low,qv high) {
  qv fold=low|high;
  volatile qv stage;
  stage=fold|__builtin_shuffle(fold,(v8di){4,5,6,7,0,1,2,3});
  fold=stage;
  stage=fold|__builtin_shuffle(fold,(v8di){2,3,0,1,6,7,4,5});
  fold=stage;
  stage=fold|__builtin_shuffle(fold,(v8di){1,0,3,2,5,4,7,6});
  fold=stage;
  /* Every qword now holds the same OR. Narrow only this scalar API mask. */
  return (unsigned)fold[0];
}

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
  pw_powf_log_register_lookup(index,&invc,&logc);
  const dv r=z*invc-1,y0=logc+__builtin_convertvector(k,dv),r2=r*r,r4=r2*r2;
  const dv p0=__powf_log2_data.poly[0]*r+__powf_log2_data.poly[1];
  const dv p1=__powf_log2_data.poly[2]*r+__powf_log2_data.poly[3];
  const dv q0=__powf_log2_data.poly[4]*r+y0,q1=p1*r2+q0;
  const dv log2x=p0*r4+q1;
  dv exponent=yd*log2x;
  unsigned overflow=0,underflow=0;
  qv overflow_lanes[2]={{0},{0}},underflow_lanes[2]={{0},{0}};
  for(unsigned i=0;i<16;++i) {
    if(exponent[i]>0x1.fffffffd1d571p+6) {overflow_lanes[i>>3][i&7]=UINT64_C(1)<<i;exponent[i]=0;}
    else if(exponent[i]<=-150.0) {underflow_lanes[i>>3][i&7]=UINT64_C(1)<<i;exponent[i]=0;}
  }
  overflow=pw_powf_fold_predicate_i64(overflow_lanes[0],overflow_lanes[1]);
  underflow=pw_powf_fold_predicate_i64(underflow_lanes[0],underflow_lanes[1]);
  dv kd=exponent+__exp2f_data.shift_scaled;uint64_t ki[16];memcpy(ki,&kd,sizeof kd);
  kd-=__exp2f_data.shift_scaled;
  const dv er=exponent-kd,er2=er*er;
  dv scale;
  pw_powf_exp_register_lookup(ki,sign,&scale);
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
    for(unsigned i=0;i<16;++i)if(invalid&(1u<<i)) {
      volatile float numerator=0.0f,denominator=0.0f;
      volatile float quotient=numerator/denominator;
      const float value=quotient;memcpy(&output[i],&value,sizeof value);
    }
  }
  if(divzero) {
    for(unsigned i=0;i<16;++i)if(divzero&(1u<<i)) {
      volatile float numerator=sign[i]?-1.0f:1.0f,denominator=0.0f;
      volatile float quotient=numerator/denominator;
      const float value=quotient;memcpy(&special[i],&value,sizeof value);
    }
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
int phi_host_powf_register_i64_scalar_events_e16(const uint32_t x[16],const uint32_t y[16],unsigned active,
                     const uint32_t merge[16],uint32_t output[16]) {
  if(active&~65535u)return 1;
  uint32_t ax[16],ay[16],pass[16],value[16];
  memcpy(ax,x,64);memcpy(ay,y,64);memcpy(pass,merge,64);
  if(!active){memcpy(output,pass,64);return 0;}
  const uv mask=pw_powf_lane_mask(active);uv xb,yb;
  memcpy(&xb,ax,64);memcpy(&yb,ay,64);
  xb=(xb&mask)|(((uv){0}+UINT32_C(0x3f800000))&~mask);yb&=mask;
  memcpy(ax,&xb,64);memcpy(ay,&yb,64);
  core(ax,ay,value);
  uv computed,merge_bits;memcpy(&computed,value,64);memcpy(&merge_bits,pass,64);
  computed=(computed&mask)|(merge_bits&~mask);memcpy(value,&computed,64);
  memcpy(output,value,64);return 0;
}
