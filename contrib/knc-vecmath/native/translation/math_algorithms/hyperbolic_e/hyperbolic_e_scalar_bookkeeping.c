/* Additive N5 source-only successor for the actual12-miss hyperbolic TU.
 * Only witnessed scalar scale construction, er sanitization, tiny-input
 * selection and overflow bit merge move to local scalar helpers.
 * All explicit64B formulas, coefficients and special arithmetic are retained.
 * No generator, target, ABI or numerical qualification is claimed. */
/* Vector double-double evaluation of musl v1.2.5 Sun expm1's official rational
 * kernel and split-ln2 reduction, followed by its stable hyperbolic identities.
 * Original Sun notices and official sources are retained in upstream/.
 * No fitted coefficient or scalar exp/expm1/hyperbolic supplies a lane result.
 * New host algorithm only; target ABI/ISA/accuracy remain unqualified. */
#include "hyperbolic_e.h"
#include <string.h>
#if defined(__FAST_MATH__)
#error "strict floating point required"
#endif
#pragma GCC push_options
#pragma GCC optimize ("fp-contract=off")
typedef double dv __attribute__((vector_size(64)));
typedef uint64_t uv __attribute__((vector_size(64)));
typedef struct {dv h,l;} dd;
#define INLINE static inline __attribute__((always_inline))
INLINE dv splat(double a){return(dv){0}+a;}
INLINE dd number(double a){return(dd){splat(a),(dv){0}};}
INLINE dd norm(dv h,dv l){dv s=h+l;return(dd){s,l-(s-h)};}
INLINE dd add(dd a,dd b){dv s=a.h+b.h,v=s-a.h,e=(a.h-(s-v))+(b.h-v)+a.l+b.l;return norm(s,e);}
INLINE dd neg(dd a){return(dd){-a.h,-a.l};}
INLINE dd sub(dd a,dd b){return add(a,neg(b));}
INLINE dd mul(dd a,dd b){
  dv p=a.h*b.h,ca=0x1.0000002p27*a.h,cb=0x1.0000002p27*b.h;
  dv ah=ca-(ca-a.h),al=a.h-ah,bh=cb-(cb-b.h),bl=b.h-bh;
  dv e=((ah*bh-p)+ah*bl+al*bh)+al*bl+a.h*b.l+a.l*b.h+a.l*b.l;
  return norm(p,e);
}
INLINE dd divide(dd a,dd b){
  dv q=a.h/b.h;dd first={q,(dv){0}},r=sub(a,mul(b,first));
  dv q2=(r.h+r.l)/b.h;dd result=add(first,(dd){q2,(dv){0}});
  r=sub(a,mul(b,result));return add(result,(dd){(r.h+r.l)/b.h,(dv){0}});
}
INLINE dd scale(dd a,dv power){return(dd){a.h*power,a.l*power};}
INLINE dv frombits(uv b){dv v;memcpy(&v,&b,64);return v;}
INLINE uv tobits(dv v){uv b;memcpy(&b,&v,64);return b;}

/* Same scaled Q1..Q5 bit patterns as the pinned official expm1.c. */
INLINE dd reduced_exp(dd r){
  dd half=mul(r,number(.5)),z=mul(r,half);
  dd p=number(-0x1.afdb76e09c32dp-23);
  p=add(number(0x1.0cfca86e65239p-18),mul(z,p));
  p=add(number(-0x1.4ce199eaadbb7p-14),mul(z,p));
  p=add(number(0x1.a01a019fe5585p-10),mul(z,p));
  p=add(number(-0x1.11111111110f4p-5),mul(z,p));
  dd r1=add(number(1),mul(z,p)),t=sub(number(3),mul(r1,half));
  /* Multiply the zero numerator first, avoiding unused1/3 on neutral lanes. */
  dd e=divide(mul(z,sub(r1,t)),sub(number(6),mul(r,t)));
  return add(number(1),add(r,sub(z,mul(r,e))));
}

/* Only the witnessed scalar scale/selection preparation is isolated.  The
 * explicit64B arithmetic below retains its original formulas and controls. */
#define PW_HYPER_SCALAR_HELPER __attribute__((noinline,noipa,optimize("no-tree-vectorize","no-tree-slp-vectorize")))
static PW_HYPER_SCALAR_HELPER unsigned pw_hyper_scales(const double input[8],double kd[8],uint64_t small_scale_bits[8],uint64_t half_scale_bits[8]){
  unsigned twice=0;
  for(unsigned i=0;i<8;i++){
    int k=(int)(input[i]*0x1.71547652b82fep0+.5);kd[i]=(double)k;
    int exponent=k-1;
    if(exponent==1024){exponent=1023;twice|=1u<<i;}
    half_scale_bits[i]=(uint64_t)(exponent+1023)<<52;
    small_scale_bits[i]=input[i]<20?(uint64_t)(k+1023)<<52:UINT64_C(0x3ff0000000000000);
  }
  return twice;
}
static PW_HYPER_SCALAR_HELPER void pw_hyper_small_inputs(const double input[8],double high[8],double low[8]){
  for(unsigned i=0;i<8;i++)if(input[i]>=20){high[i]=1;low[i]=0;}
}
static PW_HYPER_SCALAR_HELPER void pw_hyper_tiny_inputs(unsigned tiny,unsigned operation,const uint64_t saved[8],double force[8],double under[8]){
  for(unsigned i=0;i<8;i++)if(tiny&(1u<<i)){
    memcpy(&force[i],&saved[i],8);if(operation!=1&&(saved[i]&UINT64_C(0x7fffffffffffffff))<UINT64_C(0x0010000000000000))under[i]=force[i];
  }
}
static PW_HYPER_SCALAR_HELPER void pw_hyper_overflow_merge(unsigned over,unsigned operation,const uint64_t saved[8],const uint64_t value[8],uint64_t bits[8]){
  for(unsigned i=0;i<8;i++)if(over&(1u<<i))bits[i]=value[i]|(operation==0?saved[i]&UINT64_C(0x8000000000000000):0);
}

static __attribute__((noinline)) void core(unsigned operation,const double input[8],double output[8]){
  dv x;memcpy(&x,input,64);double kd[8];uv small_scale_bits,half_scale_bits;
  uint64_t small_scale_lane[8],half_scale_lane[8];
  unsigned twice=pw_hyper_scales(input,kd,small_scale_lane,half_scale_lane);
  memcpy(&small_scale_bits,small_scale_lane,64);memcpy(&half_scale_bits,half_scale_lane,64);
  dv k;memcpy(&k,kd,64);
  dd r=sub(sub((dd){x,(dv){0}},mul((dd){k,(dv){0}},number(0x1.62e42fee00000p-1))),
      mul((dd){k,(dv){0}},number(0x1.a39ef35793c76p-33)));
  dd er=reduced_exp(r);
  /* Only finite small arguments participate in reciprocal/cancellation paths. */
  double small_high[8],small_low[8];memcpy(small_high,&er.h,64);memcpy(small_low,&er.l,64);
  pw_hyper_small_inputs(input,small_high,small_low);
  memcpy(&er.h,small_high,64);memcpy(&er.l,small_low,64);
  dd ex=scale(er,frombits(small_scale_bits)),t=sub(ex,number(1));
  dd sh=mul(number(.5),add(t,divide(t,add(t,number(1)))));
  dd ch=add(number(1),divide(mul(t,t),mul(number(2),add(t,number(1)))));
  dd answer=operation==0?sh:operation==1?ch:divide(sh,ch);
  dv value=answer.h+answer.l;
  unsigned large=0;for(unsigned i=0;i<8;i++)if(input[i]>=20)large|=1u<<i;
  if(large&&operation!=2){
    /* Recompute only sanitized large lanes; no overflowing DD intermediates. */
    dd large_r=r;for(unsigned i=0;i<8;i++)if(!(large&(1u<<i))){large_r.h[i]=0;large_r.l[i]=0;}
    dd y=reduced_exp(large_r);dv half=(y.h+y.l)*frombits(half_scale_bits);
    for(unsigned i=0;i<8;i++)if(twice&(1u<<i))half[i]*=2;
    for(unsigned i=0;i<8;i++)if(large&(1u<<i))value[i]=half[i];
  }
  for(unsigned i=0;i<8;i++)if(operation==2&&input[i]>=20)value[i]=1;
  memcpy(output,&value,64);
}

/* No numerical argument, including inactive poison, reaches an unsafe path. */
int phi_hyperbolic_e8(unsigned operation,const uint64_t input[8],unsigned active,const uint64_t merge[8],uint64_t output[8]){
  if(operation>2||active&~255u)return 1;
  uint64_t saved[8],pass[8],bits[8];memcpy(saved,input,64);memcpy(pass,merge,64);
  if(!active){memcpy(output,pass,64);return 0;}
  double ordinary[8]={0},answer[8];unsigned work=0,tiny=0,over=0,nan=0,saturated=0;
  for(unsigned i=0;i<8;i++)if(active&(1u<<i)){
    uint64_t a=saved[i]&UINT64_C(0x7fffffffffffffff);bits[i]=operation==1?UINT64_C(0x3ff0000000000000):saved[i];
    if(a>UINT64_C(0x7ff0000000000000)){nan|=1u<<i;continue;}
    if(a==UINT64_C(0x7ff0000000000000)){bits[i]=operation==1?a:operation==2?(saved[i]&UINT64_C(0x8000000000000000))|UINT64_C(0x3ff0000000000000):saved[i];continue;}
    double x;memcpy(&x,&a,8);
    if(x<0x1p-27){tiny|=1u<<i;continue;}
    if(operation==2&&x>=20){saturated|=1u<<i;bits[i]=(saved[i]&UINT64_C(0x8000000000000000))|UINT64_C(0x3ff0000000000000);continue;}
    /* Above710.5 both finite sinh/cosh are certainly beyond DBL_MAX; keeping
     * them out also prevents construction of an exponent1025 scale image. */
    if(x>710.5){over|=1u<<i;continue;}
    ordinary[i]=x;work|=1u<<i;
  }
  if(work){core(operation,ordinary,answer);for(unsigned i=0;i<8;i++)if(work&(1u<<i)){
    memcpy(&bits[i],&answer[i],8);if(operation!=1)bits[i]|=saved[i]&UINT64_C(0x8000000000000000);
  }}
  if(tiny){dv force,under;double force_lane[8]={0},under_lane[8]={1,1,1,1,1,1,1,1};
    pw_hyper_tiny_inputs(tiny,operation,saved,force_lane,under_lane);
    memcpy(&force,force_lane,64);memcpy(&under,under_lane,64);
  volatile dv inexact=force+0x1p120,underflow=under*under;(void)inexact;(void)underflow;}
  if(saturated){dv small=(dv){0};for(unsigned i=0;i<8;i++)if(saturated&(1u<<i))small[i]=0x1p-100;volatile dv force=1-small;(void)force;}
  if(nan){dv x=(dv){0};for(unsigned i=0;i<8;i++)if(nan&(1u<<i))memcpy(&x[i],&saved[i],8);dv y=x+x;uv b=tobits(y);for(unsigned i=0;i<8;i++)if(nan&(1u<<i))bits[i]=b[i];}
  if(over){dv x=splat(1);for(unsigned i=0;i<8;i++)if(over&(1u<<i))x[i]=0x1p769;dv y=x*x;uv b=tobits(y);uint64_t value_lane[8];memcpy(value_lane,&b,64);pw_hyper_overflow_merge(over,operation,saved,value_lane,bits);}
  for(unsigned i=0;i<8;i++)if(!(active&(1u<<i)))bits[i]=pass[i];memcpy(output,bits,64);return 0;
}

int phi_hyperbolic_e16(unsigned operation,const uint32_t input[16],unsigned active,const uint32_t merge[16],uint32_t output[16]){
  if(operation>2||active&~65535u)return 1;
  uint32_t saved[16],pass[16],result[16];memcpy(saved,input,64);memcpy(pass,merge,64);
  if(!active){memcpy(output,pass,64);return 0;}
  for(unsigned group=0;group<2;group++){
    double values[8]={0};uint64_t ib[8],mb[8]={0},ob[8];unsigned mask=0;
    for(unsigned i=0;i<8;i++){unsigned lane=8*group+i;if(active&(1u<<lane)){
      uint32_t a=saved[lane]&0x7fffffffu;
      if(a>=0x7f800000u){result[lane]=a>0x7f800000u?saved[lane]|0x00400000u:operation==1?a:operation==2?(saved[lane]&0x80000000u)|0x3f800000u:saved[lane];continue;}
      float f;memcpy(&f,&saved[lane],4);values[i]=f;mask|=1u<<i;
    }}
    memcpy(ib,values,64);phi_hyperbolic_e8(operation,ib,mask,mb,ob);
    for(unsigned i=0;i<8;i++){unsigned lane=8*group+i;if(mask&(1u<<i)){
      double d;memcpy(&d,&ob[i],8);float f=(float)d;memcpy(&result[lane],&f,4);
    }}
  }
  /* Active signaling NaNs are quieted with the source-format operation. */
  typedef float fv __attribute__((vector_size(64)));fv n=(fv){0},u=(fv){0};unsigned nan=0,sub=0;
  for(unsigned i=0;i<16;i++)if(active&(1u<<i)){
    uint32_t a=saved[i]&0x7fffffffu;if(a>0x7f800000u){memcpy(&n[i],&saved[i],4);nan=1;}
    if(a&&a<0x00800000u){memcpy(&u[i],&saved[i],4);sub=1;}
  }
  if(nan){volatile fv force=n+n;(void)force;}
  if(sub&&operation!=1){volatile fv force=u*u;(void)force;}
  for(unsigned i=0;i<16;i++)if(!(active&(1u<<i)))result[i]=pass[i];memcpy(output,result,64);return 0;
}
#pragma GCC pop_options
