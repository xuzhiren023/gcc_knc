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
/* GCC-KNC (S10-07, see NOTICE): a dd travels by pointer, not by value. Each
 * helper reads its operands, then writes *o, which may be an operand, and
 * returns o so that calls nest as before; NEW is a fresh temporary. */
#define NEW (&(dd){{0},{0}})
INLINE const dd *number(dd *o,double a){*o=(dd){splat(a),(dv){0}};return o;}
INLINE const dd *norm(dd *o,dv h,dv l){dv s=h+l;*o=(dd){s,l-(s-h)};return o;}
INLINE const dd *add(dd *o,const dd *a,const dd *b){dv s=a->h+b->h,v=s-a->h,e=(a->h-(s-v))+(b->h-v)+a->l+b->l;return norm(o,s,e);}
INLINE const dd *neg(dd *o,const dd *a){*o=(dd){-a->h,-a->l};return o;}
INLINE const dd *sub(dd *o,const dd *a,const dd *b){return add(o,a,neg(NEW,b));}
INLINE const dd *mul(dd *o,const dd *a,const dd *b){
  dv p=a->h*b->h,ca=0x1.0000002p27*a->h,cb=0x1.0000002p27*b->h;
  dv ah=ca-(ca-a->h),al=a->h-ah,bh=cb-(cb-b->h),bl=b->h-bh;
  dv e=((ah*bh-p)+ah*bl+al*bh)+al*bl+a->h*b->l+a->l*b->h+a->l*b->l;
  return norm(o,p,e);
}
INLINE const dd *divide(dd *o,const dd *a,const dd *b){
  dv q=a->h/b->h;dd first={q,(dv){0}},r,result;sub(&r,a,mul(NEW,b,&first));
  dv q2=(r.h+r.l)/b->h;add(&result,&first,&(dd){q2,(dv){0}});
  sub(&r,a,mul(NEW,b,&result));return add(o,&result,&(dd){(r.h+r.l)/b->h,(dv){0}});
}
INLINE const dd *scale(dd *o,const dd *a,dv power){*o=(dd){a->h*power,a->l*power};return o;}
INLINE dv frombits(uv b){dv v;memcpy(&v,&b,64);return v;}
INLINE uv tobits(dv v){uv b;memcpy(&b,&v,64);return b;}

/* Same scaled Q1..Q5 bit patterns as the pinned official expm1.c. */
INLINE const dd *reduced_exp(dd *o,const dd *r){
  dd half,z,p,r1,t,e;mul(&half,r,number(NEW,.5));mul(&z,r,&half);
  number(&p,-0x1.afdb76e09c32dp-23);
  add(&p,number(NEW,0x1.0cfca86e65239p-18),mul(NEW,&z,&p));
  add(&p,number(NEW,-0x1.4ce199eaadbb7p-14),mul(NEW,&z,&p));
  add(&p,number(NEW,0x1.a01a019fe5585p-10),mul(NEW,&z,&p));
  add(&p,number(NEW,-0x1.11111111110f4p-5),mul(NEW,&z,&p));
  add(&r1,number(NEW,1),mul(NEW,&z,&p));sub(&t,number(NEW,3),mul(NEW,&r1,&half));
  /* Multiply the zero numerator first, avoiding unused1/3 on neutral lanes. */
  divide(&e,mul(NEW,&z,sub(NEW,&r1,&t)),sub(NEW,number(NEW,6),mul(NEW,r,&t)));
  return add(o,number(NEW,1),add(NEW,r,sub(NEW,&z,mul(NEW,r,&e))));
}

static __attribute__((noinline)) void core(unsigned operation,const double input[8],double output[8]){
  dv x;memcpy(&x,input,64);double kd[8];uv small_scale_bits,half_scale_bits;
  unsigned twice=0;
  for(unsigned i=0;i<8;i++){
    int k=(int)(input[i]*0x1.71547652b82fep0+.5);kd[i]=(double)k;
    int exponent=k-1;
    if(exponent==1024){exponent=1023;twice|=1u<<i;}
    half_scale_bits[i]=(uint64_t)(exponent+1023)<<52;
    small_scale_bits[i]=input[i]<20?(uint64_t)(k+1023)<<52:UINT64_C(0x3ff0000000000000);
  }
  dv k;memcpy(&k,kd,64);
  dd r,er,ex,t,sh,ch;
  sub(&r,sub(NEW,&(dd){x,(dv){0}},mul(NEW,&(dd){k,(dv){0}},number(NEW,0x1.62e42fee00000p-1))),
      mul(NEW,&(dd){k,(dv){0}},number(NEW,0x1.a39ef35793c76p-33)));
  reduced_exp(&er,&r);
  /* Only finite small arguments participate in reciprocal/cancellation paths. */
  for(unsigned i=0;i<8;i++)if(input[i]>=20){er.h[i]=1;er.l[i]=0;}
  scale(&ex,&er,frombits(small_scale_bits));sub(&t,&ex,number(NEW,1));
  mul(&sh,number(NEW,.5),add(NEW,&t,divide(NEW,&t,add(NEW,&t,number(NEW,1)))));
  add(&ch,number(NEW,1),divide(NEW,mul(NEW,&t,&t),mul(NEW,number(NEW,2),add(NEW,&t,number(NEW,1)))));
  const dd *answer=operation==0?&sh:operation==1?&ch:divide(NEW,&sh,&ch);
  dv value=answer->h+answer->l;
  unsigned large=0;for(unsigned i=0;i<8;i++)if(input[i]>=20)large|=1u<<i;
  if(large&&operation!=2){
    /* Recompute only sanitized large lanes; no overflowing DD intermediates. */
    dd large_r=r;for(unsigned i=0;i<8;i++)if(!(large&(1u<<i))){large_r.h[i]=0;large_r.l[i]=0;}
    dd y;reduced_exp(&y,&large_r);dv half=(y.h+y.l)*frombits(half_scale_bits);
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
  if(tiny){dv force=(dv){0},under=splat(1);for(unsigned i=0;i<8;i++)if(tiny&(1u<<i)){
    memcpy(&force[i],&saved[i],8);if(operation!=1&&(saved[i]&UINT64_C(0x7fffffffffffffff))<UINT64_C(0x0010000000000000))under[i]=force[i];
  }volatile dv inexact=force+0x1p120,underflow=under*under;(void)inexact;(void)underflow;}
  if(saturated){dv small=(dv){0};for(unsigned i=0;i<8;i++)if(saturated&(1u<<i))small[i]=0x1p-100;volatile dv force=1-small;(void)force;}
  if(nan){dv x=(dv){0};for(unsigned i=0;i<8;i++)if(nan&(1u<<i))memcpy(&x[i],&saved[i],8);dv y=x+x;uv b=tobits(y);for(unsigned i=0;i<8;i++)if(nan&(1u<<i))bits[i]=b[i];}
  if(over){dv x=splat(1);for(unsigned i=0;i<8;i++)if(over&(1u<<i))x[i]=0x1p769;dv y=x*x;uv b=tobits(y);for(unsigned i=0;i<8;i++)if(over&(1u<<i))bits[i]=b[i]|(operation==0?saved[i]&UINT64_C(0x8000000000000000):0);}
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
