/* Eight-DP GCC-vector adaptation of Arm optimized-routines v26.01 pow.c/data,
 * commit649ccc8411e7c4862965710f25c570d854a1483f.
 * Copyright(c)2018-2025 Arm Limited. SPDX-License-Identifier: MIT
 * Preserve compensated log/product/exp and signed subnormal rounding. Host
 * source experiment; no scalar pow delegation or target qualification. */
#include "pow_e8.h"
#include "math_config.h"
#include <string.h>
#if defined(__FAST_MATH__) || HAVE_FAST_FMA || HAVE_FAST_ROUND
#error "pow_e8 requires strict non-FMA/non-toint source configuration"
#endif
_Static_assert(POW_LOG_TABLE_BITS==7&&POW_LOG_POLY_ORDER==8&&EXP_TABLE_BITS==7&&EXP_POLY_ORDER==5&&EXP_USE_TOINT_NARROW==0,"unsupported pinned data configuration");
typedef double dv __attribute__((vector_size(64)));
typedef uint64_t uv __attribute__((vector_size(64)));
typedef int64_t iv __attribute__((vector_size(64)));
static unsigned kind(uint64_t x) {
  unsigned e=(x>>52)&2047;
  if(e<1023)return 0;if(e>1075)return 2;
  unsigned shift=1075-e;
  if(x&((UINT64_C(1)<<shift)-1))return 0;
  return (x&(UINT64_C(1)<<shift))?1:2;
}
static unsigned snan(uint64_t x){return (x&UINT64_C(0x7fffffffffffffff))>UINT64_C(0x7ff0000000000000)&&!(x&UINT64_C(0x0008000000000000));}
static dv frombits(uv bits){dv result;memcpy(&result,&bits,64);return result;}
static uv tobits(dv value){uv result;memcpy(&result,&value,64);return result;}
static __attribute__((noinline)) void core(const uint64_t x[8],const uint64_t y[8],uint64_t output[8]) {
  uint64_t ax[8],ay[8],norm[8],sign[8]={0},special[8]={0};
  unsigned direct=0,nans=0,invalid=0,divzero=0,subnormal=0,tiny_y=0,overflow=0,underflow=0;
  for(unsigned i=0;i<8;++i) {
    uint64_t xb=x[i],yb=y[i],xm=xb&UINT64_C(0x7fffffffffffffff),ym=yb&UINT64_C(0x7fffffffffffffff);
    ax[i]=norm[i]=UINT64_C(0x3ff0000000000000);ay[i]=0;
    if(!ym){if(snan(xb))nans|=1u<<i;else{direct|=1u<<i;special[i]=UINT64_C(0x3ff0000000000000);}continue;}
    if(xb==UINT64_C(0x3ff0000000000000)){if(snan(yb))nans|=1u<<i;else{direct|=1u<<i;special[i]=UINT64_C(0x3ff0000000000000);}continue;}
    if(xm>UINT64_C(0x7ff0000000000000)||ym>UINT64_C(0x7ff0000000000000)){nans|=1u<<i;continue;}
    if(ym==UINT64_C(0x7ff0000000000000)) {
      direct|=1u<<i;special[i]=xm==UINT64_C(0x3ff0000000000000)?UINT64_C(0x3ff0000000000000):
        ((xm<UINT64_C(0x3ff0000000000000))==!(yb>>63)?0:UINT64_C(0x7ff0000000000000));continue;
    }
    unsigned integer=kind(yb);sign[i]=(xb>>63)&&integer==1?UINT64_C(0x8000000000000000):0;
    if(!xm||xm==UINT64_C(0x7ff0000000000000)) {
      direct|=1u<<i;special[i]=sign[i]|((!xm)==!(yb>>63)?0:UINT64_C(0x7ff0000000000000));
      if(!xm&&(yb>>63))divzero|=1u<<i;continue;
    }
    if((xb>>63)&&!integer){invalid|=1u<<i;continue;}
    if(ym<UINT64_C(0x3be0000000000000)){tiny_y|=1u<<i;continue;}
    if(ym>=UINT64_C(0x43e0000000000000)) {
      if(xm==UINT64_C(0x3ff0000000000000)){direct|=1u<<i;special[i]=UINT64_C(0x3ff0000000000000);}
      else if((xm>UINT64_C(0x3ff0000000000000))==!(yb>>63))overflow|=1u<<i;
      else underflow|=1u<<i;
      continue;
    }
    ax[i]=xm;ay[i]=yb;
    if(xm<UINT64_C(0x0010000000000000)){subnormal|=1u<<i;norm[i]=xm;}
  }
  if(subnormal) {
    dv v;memcpy(&v,norm,64);v*=0x1p52;uint64_t bits[8];memcpy(bits,&v,64);
    for(unsigned i=0;i<8;++i)if(subnormal&(1u<<i))ax[i]=bits[i]-(UINT64_C(52)<<52);
  }
  uv ix;memcpy(&ix,ax,64);
  const uv offset=ix-UINT64_C(0x3fe6955500000000),index=(offset>>45)&127,iz=ix-(offset&UINT64_C(0xfff0000000000000));
  iv signed_offset;memcpy(&signed_offset,&offset,64);const dv kd=__builtin_convertvector(signed_offset>>52,dv),z=frombits(iz);
  dv invc,logc,logtail;
  for(unsigned i=0;i<8;++i){invc[i]=__pow_log_data.tab[index[i]].invc;logc[i]=__pow_log_data.tab[index[i]].logc;logtail[i]=__pow_log_data.tab[index[i]].logctail;}
  const dv zhi=frombits((iz+(UINT64_C(1)<<31))&UINT64_C(0xffffffff00000000)),zlo=z-zhi;
  const dv rhi=zhi*invc-1,rlo=zlo*invc,r=rhi+rlo;
  const dv t1=kd*__pow_log_data.ln2hi+logc,t2=t1+r,lo1=kd*__pow_log_data.ln2lo+logtail,lo2=t1-t2+r;
  const dv ar=__pow_log_data.poly[0]*r,ar2=r*ar,ar3=r*ar2,arhi=__pow_log_data.poly[0]*rhi,arhi2=rhi*arhi;
  const dv hi=t2+arhi2,lo3=rlo*(ar+arhi),lo4=t2-hi+arhi2;
  const dv p=ar3*(__pow_log_data.poly[1]+r*__pow_log_data.poly[2]+ar2*(__pow_log_data.poly[3]+r*__pow_log_data.poly[4]+ar2*(__pow_log_data.poly[5]+r*__pow_log_data.poly[6])));
  const dv lo=lo1+lo2+lo3+lo4+p,loghi=hi+lo,loglo=hi-loghi+lo;
  dv yd;memcpy(&yd,ay,64);
  const dv yhi=frombits(tobits(yd)&UINT64_C(0xfffffffff8000000)),ylo=yd-yhi;
  const dv lhi=frombits(tobits(loghi)&UINT64_C(0xfffffffff8000000)),llo=loghi-lhi+loglo;
  dv ehi=yhi*lhi,elo=ylo*lhi+yd*llo;
  uint64_t ewords[8];memcpy(ewords,&ehi,64);
  unsigned tiny_exp=0,large_pos=0,large_neg=0;
  for(unsigned i=0;i<8;++i) {
    unsigned top=(ewords[i]>>52)&2047;
    if(top<969){tiny_exp|=1u<<i;ehi[i]=0;elo[i]=0;}
    else if(top>=1033){if(ewords[i]>>63)underflow|=1u<<i;else overflow|=1u<<i;ehi[i]=0;elo[i]=0;}
    else if(top>=1032){if(ewords[i]>>63)large_neg|=1u<<i;else large_pos|=1u<<i;}
  }
  dv eround=ehi*__exp_data.invln2N+__exp_data.shift;uv ki=tobits(eround);eround-=__exp_data.shift;
  const dv er=ehi+eround*__exp_data.negln2hiN+eround*__exp_data.negln2loN+elo,er2=er*er;
  uv sbits;dv tail;
  for(unsigned i=0;i<8;++i) {
    unsigned idx=2*(ki[i]&127);uint64_t tb=__exp_data.tab[idx];memcpy(&tail[i],&tb,8);
    sbits[i]=__exp_data.tab[idx+1]+((ki[i]+(sign[i]?UINT64_C(262144):0))<<45);
  }
  const dv tmp=tail+er+er2*(__exp_data.poly[0]+er*__exp_data.poly[1])+er2*er2*(__exp_data.poly[2]+er*__exp_data.poly[3]);
  uv normal=sbits;for(unsigned i=0;i<8;++i)if((large_pos|large_neg)&(1u<<i))normal[i]=UINT64_C(0x3ff0000000000000);
  const dv scale=frombits(normal),approx=scale+scale*tmp;memcpy(output,&approx,64);
  if(large_pos) {
    uv bits=(uv){0}+UINT64_C(0x3ff0000000000000);dv t=(dv){0};
    for(unsigned i=0;i<8;++i)if(large_pos&(1u<<i)){bits[i]=sbits[i]-(UINT64_C(1009)<<52);t[i]=tmp[i];}
    const dv s=frombits(bits),v=(s+s*t)*0x1p1009;uint64_t out[8];memcpy(out,&v,64);
    for(unsigned i=0;i<8;++i)if(large_pos&(1u<<i))output[i]=out[i];
  }
  if(large_neg) {
    uv bits=(uv){0}+UINT64_C(0x3ff0000000000000);dv t=(dv){0};
    for(unsigned i=0;i<8;++i)if(large_neg&(1u<<i)){bits[i]=sbits[i]+(UINT64_C(1022)<<52);t[i]=tmp[i];}
    const dv s=frombits(bits);dv v=s+s*t;unsigned sub=0;
    for(unsigned i=0;i<8;++i)if((large_neg&(1u<<i))&&(tobits(v)[i]&UINT64_C(0x7fffffffffffffff))<UINT64_C(0x3ff0000000000000))sub|=1u<<i;
    if(sub) {
      dv one=(dv){0}+1;for(unsigned i=0;i<8;++i)if(sub&(1u<<i))one[i]=sign[i]?-1:1;
      dv low=s-v+s*t;const dv high=one+v;low=one-high+v+low;const dv rounded=(high+low)-one;
      for(unsigned i=0;i<8;++i)if(sub&(1u<<i))v[i]=rounded[i];
      uv vb=tobits(v);for(unsigned i=0;i<8;++i)if((sub&(1u<<i))&&!(vb[i]&UINT64_C(0x7fffffffffffffff)))vb[i]=sign[i];v=frombits(vb);
      volatile double factor=0x1p-1022;volatile double force=factor*factor;(void)force;
    }
    const dv vout=0x1p-1022*v;uint64_t out[8];memcpy(out,&vout,64);
    for(unsigned i=0;i<8;++i)if(large_neg&(1u<<i))output[i]=out[i];
  }
  if(tiny_exp) {
    dv a=(dv){0};for(unsigned i=0;i<8;++i)if(tiny_exp&(1u<<i))memcpy(&a[i],&ewords[i],8);
    const dv v=1+a;uint64_t out[8];memcpy(out,&v,64);for(unsigned i=0;i<8;++i)if(tiny_exp&(1u<<i))output[i]=out[i]^sign[i];
  }
  if(tiny_y) {
    dv a=(dv){0};for(unsigned i=0;i<8;++i)if(tiny_y&(1u<<i)){memcpy(&a[i],&y[i],8);if((x[i]&UINT64_C(0x7fffffffffffffff))<UINT64_C(0x3ff0000000000000))a[i]=-a[i];}
    const dv v=1+a;uint64_t out[8];memcpy(out,&v,64);for(unsigned i=0;i<8;++i)if(tiny_y&(1u<<i))output[i]=out[i];
  }
  if(nans) {
    dv a=(dv){0},b=(dv){0};for(unsigned i=0;i<8;++i)if(nans&(1u<<i)){memcpy(&a[i],&x[i],8);memcpy(&b[i],&y[i],8);}
    const dv v=a+b;uint64_t out[8];memcpy(out,&v,64);for(unsigned i=0;i<8;++i)if(nans&(1u<<i))output[i]=out[i];
  }
  if(invalid||divzero) {
    volatile double one=1;dv a=(dv){0}+1,b=(dv){0}+1;
    for(unsigned i=0;i<8;++i){if(invalid&(1u<<i)){a[i]=0;b[i]=0;}if(divzero&(1u<<i)){a[i]=sign[i]?-one:one;b[i]=0;}}
    const dv v=a/b;uint64_t out[8];memcpy(out,&v,64);
    for(unsigned i=0;i<8;++i){if(invalid&(1u<<i))output[i]=out[i];if(divzero&(1u<<i))special[i]=out[i];}
  }
  if(overflow||underflow) {
    volatile double big=0x1p769,small=0x1p-767;dv a=(dv){0}+1,b=(dv){0}+1;
    for(unsigned i=0;i<8;++i){if(overflow&(1u<<i)){a[i]=sign[i]?-big:big;b[i]=big;}if(underflow&(1u<<i)){a[i]=sign[i]?-small:small;b[i]=small;}}
    const dv v=a*b;uint64_t out[8];memcpy(out,&v,64);for(unsigned i=0;i<8;++i)if((overflow|underflow)&(1u<<i))output[i]=out[i];
  }
  for(unsigned i=0;i<8;++i)if(direct&(1u<<i))output[i]=special[i];
}
int phi_host_pow_e8(const uint64_t x[8],const uint64_t y[8],unsigned active,const uint64_t merge[8],uint64_t output[8]) {
  if(active&~255u)return 1;
  uint64_t ax[8],ay[8],pass[8],result[8];memcpy(ax,x,64);memcpy(ay,y,64);memcpy(pass,merge,64);
  if(!active){memcpy(output,pass,64);return 0;}
  for(unsigned i=0;i<8;++i)if(!(active&(1u<<i))){ax[i]=UINT64_C(0x3ff0000000000000);ay[i]=0;}
  core(ax,ay,result);for(unsigned i=0;i<8;++i)if(!(active&(1u<<i)))result[i]=pass[i];memcpy(output,result,64);return 0;
}
