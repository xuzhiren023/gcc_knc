/* Additive N5 revision3: scalar bookkeeping, explicit512-bit numerical core.
 * Only per-lane classification, integer normalization, selection preparation,
 * casts and reconstruction loops move to function-local scalar helpers.
 * Retained coefficients/formulas and vector arithmetic are unchanged.
 * Source-only preparation: no generated ISA, ABI, numerical or native claim. */
/* GCC-vector adaptation of official musl v1.2.5 atan.c and atan2.c.
 * ====================================================
 * Copyright (C) 1993 by Sun Microsystems, Inc. All rights reserved.
 * Developed at SunSoft/SunPro, a Sun Microsystems, Inc. business.
 * Permission to use, copy, modify, and distribute this software is freely
 * granted, provided that this notice is preserved.
 * ====================================================
 * Changes:8-DP vector reductions/polynomial and safe ratio/quadrant handling;
 * SP16 widens two groups and rounds once. V2 carries a compensated division
 * tail into the unrounded atan sum and preserves its low part for quadrants. Full64B private raw-pointer/mask ABI.
 * No scalar atan/atan2 fallback. Host source experiment, target/G5 unqualified.
 */
#include "atan_e.h"
#include "knc_mvec_finite_divide.h"
#include <string.h>
#ifdef __FAST_MATH__
#error "atan_e requires strict FP"
#endif
typedef double dv __attribute__((vector_size(64)));
typedef float fv __attribute__((vector_size(64)));
#define PW_ATAN_SCALAR_HELPER __attribute__((noinline,noipa,optimize("no-tree-vectorize","no-tree-slp-vectorize")))
#include "atan_e_v3_register_tables.h"
static uint64_t dbits(double x){uint64_t b;memcpy(&b,&x,8);return b;}
static double dvalue(uint64_t b){double x;memcpy(&x,&b,8);return x;}
static const double hi[]={4.63647609000806093515e-01,7.85398163397448278999e-01,9.82793723247329054082e-01,1.57079632679489655800e+00};
static const double lo[]={2.26987774529616870924e-17,3.06161699786838301793e-17,1.39033110312309984516e-17,6.12323399573676603587e-17};
static const double aT[]={3.33333333333329318027e-01,-1.99999999998764832476e-01,1.42857142725034663711e-01,-1.11111104054623557880e-01,9.09088713343650656196e-02,-7.69187620504482999495e-02,6.66107313738753120669e-02,-5.83357013379057348645e-02,4.97687799461593236017e-02,-3.65315727442169155270e-02,1.62858201153657823623e-02};
/* Per-lane control/bit reconstruction is isolated from the explicit64B math. */
static PW_ATAN_SCALAR_HELPER void pw_atan_classify(const double input[8],double x[8],double na[8],double nb[8],double da[8],double db[8],int id[8],unsigned tiny[8],unsigned large[8],uint64_t sign[8]) {
  for(unsigned i=0;i<8;++i){uint64_t b=dbits(input[i]),m=b&UINT64_C(0x7fffffffffffffff);sign[i]=b&UINT64_C(0x8000000000000000);tiny[i]=m<UINT64_C(0x3e40000000000000);large[i]=m>=UINT64_C(0x4410000000000000);x[i]=tiny[i]||large[i]?0:dvalue(m);id[i]=m<UINT64_C(0x3fdc000000000000)?-1:m<UINT64_C(0x3fe6000000000000)?0:m<UINT64_C(0x3ff3000000000000)?1:m<UINT64_C(0x4003800000000000)?2:3;if(tiny[i]||large[i])id[i]=-1;
    na[i]=id[i]==0?2:id[i]==3?0:1;nb[i]=id[i]==0||id[i]==1||id[i]==3?-1:id[i]==2?-1.5:0;da[i]=id[i]==0||id[i]==1||id[i]==3?1:id[i]==2?1.5:0;db[i]=id[i]==0?2:id[i]==3?0:1;}
}
static PW_ATAN_SCALAR_HELPER void pw_atan_reconstruct(const double input[8],const double correction[8],double output[8],double low[8],const unsigned tiny[8],const unsigned large[8],const int id[8],const uint64_t sign[8],const double x[8],const double h[8],const double direct_tail[8],const double reduced_tail[8]) {
  for(unsigned i=0;i<8;++i){if(tiny[i]){output[i]=input[i];low[i]=correction[i];continue;}if(large[i]){output[i]=dvalue(dbits(hi[3])^sign[i]);low[i]=dvalue(dbits(lo[3])^sign[i]);continue;}double head=id[i]<0?x[i]:h[i],tail=id[i]<0?direct_tail[i]:reduced_tail[i];double sum=head+tail,residual=(head-sum)+tail;output[i]=dvalue(dbits(sum)^sign[i]);low[i]=dvalue(dbits(residual)^sign[i]);}
}
static PW_ATAN_SCALAR_HELPER void pw_atan2_classify(const double y[8],const double x[8],double numerator[8],double denominator[8],unsigned *direct_out,unsigned *negative_out,uint64_t special[8],uint64_t ysign[8]) {
  const double pi=3.1415926535897931160E+00;unsigned direct=0,negative=0;
  for(unsigned i=0;i<8;++i){uint64_t yb=dbits(y[i]),xb=dbits(x[i]),ym=yb&UINT64_C(0x7fffffffffffffff),xm=xb&UINT64_C(0x7fffffffffffffff);ysign[i]=yb&UINT64_C(0x8000000000000000);unsigned neg=(unsigned)(xb>>63);uint32_t iy=(uint32_t)(ym>>32),ix=(uint32_t)(xm>>32);numerator[i]=0;denominator[i]=1;special[i]=0;
    if(!ym){direct|=1u<<i;special[i]=dbits(neg?pi:0)^ysign[i];}
    else if(!xm){direct|=1u<<i;special[i]=dbits(pi/2)^ysign[i];}
    else if(xm==UINT64_C(0x7ff0000000000000)){direct|=1u<<i;special[i]=dbits(ym==UINT64_C(0x7ff0000000000000)?(neg?3*pi/4:pi/4):(neg?pi:0))^ysign[i];}
    else if(ix+(64u<<20)<iy||ym==UINT64_C(0x7ff0000000000000)){direct|=1u<<i;special[i]=dbits(pi/2)^ysign[i];}
    else {if(neg)negative|=1u<<i;if(!(neg&&iy+(64u<<20)<ix)){numerator[i]=dvalue(ym);denominator[i]=dvalue(xm);}}
  }
  *direct_out=direct;*negative_out=negative;
}
/* Nonzero input, exactly the original CLZ64 count. The opaque GPR value
 * at each shift prevents recognition as an unsupported BSR/LZCNT idiom. */
static PW_ATAN_SCALAR_HELPER int pw_atan_clz64_nonzero(uint64_t value) {
  int count=0;
  __asm__ __volatile__("" : "+r"(value));
  while((value&UINT64_C(0x8000000000000000))==0) {
    value<<=1;
    __asm__ __volatile__("" : "+r"(value));
    ++count;
  }
  return count;
}
static PW_ATAN_SCALAR_HELPER void pw_atan2_scale(const double numerator[8],const double denominator[8],const double quotient[8],double ny[8],double nx[8],double rq[8]) {
  for(unsigned i=0;i<8;++i){ny[i]=0;nx[i]=1;rq[i]=0;uint64_t yb=dbits(numerator[i]),xb=dbits(denominator[i]);if(!yb)continue;int ey=(int)(yb>>52),ex=(int)(xb>>52);uint64_t yf=yb&UINT64_C(0xfffffffffffff),xf=xb&UINT64_C(0xfffffffffffff);if(!ey){int shift=pw_atan_clz64_nonzero(yf)-11;yf=(yf<<shift)&UINT64_C(0xfffffffffffff);ey=1-shift;}if(!ex){int shift=pw_atan_clz64_nonzero(xf)-11;xf=(xf<<shift)&UINT64_C(0xfffffffffffff);ex=1-shift;}int gap=ey-ex;if(gap>=-64&&gap<=64){ny[i]=dvalue(((uint64_t)(1023+gap)<<52)|yf);nx[i]=dvalue((UINT64_C(1023)<<52)|xf);rq[i]=quotient[i];}}
}
static PW_ATAN_SCALAR_HELPER void pw_atan2_dekker_heads(const double rq[8],const double nx[8],double rh[8],double xh[8]) {
  uint64_t rb[8],xb[8];memcpy(rb,rq,64);memcpy(xb,nx,64);for(unsigned i=0;i<8;++i){rh[i]=dvalue(rb[i]&UINT64_C(0xfffffffff8000000));xh[i]=dvalue(xb[i]&UINT64_C(0xfffffffff8000000));}
}
static PW_ATAN_SCALAR_HELPER void pw_atan2_quadrant_inputs(unsigned negative,const double z[8],const double angle_low[8],double qz[8],double ql[8]) {
  const double pi_lo=1.2246467991473531772E-16;for(unsigned i=0;i<8;++i){qz[i]=negative&(1u<<i)?z[i]:0;ql[i]=negative&(1u<<i)?angle_low[i]:pi_lo;}
}
static PW_ATAN_SCALAR_HELPER void pw_atan2_reconstruct(unsigned direct,unsigned negative,const uint64_t special[8],const uint64_t ysign[8],const double adjusted[8],const double z[8],double output[8]) {
  for(unsigned i=0;i<8;++i)output[i]=direct&(1u<<i)?dvalue(special[i]):dvalue(dbits(negative&(1u<<i)?adjusted[i]:z[i])^ysign[i]);
}
static PW_ATAN_SCALAR_HELPER unsigned pw_atan_dp_inputs(const uint64_t a[8],const uint64_t b[8],unsigned mask,double ay[8],double ax[8]) {
  unsigned nan=0;for(unsigned i=0;i<8;++i){if((mask&(1u<<i))&&((a[i]&UINT64_C(0x7fffffffffffffff))>UINT64_C(0x7ff0000000000000)||(b[i]&UINT64_C(0x7fffffffffffffff))>UINT64_C(0x7ff0000000000000)))nan|=1u<<i;ay[i]=mask&(1u<<i)&&!(nan&(1u<<i))?dvalue(a[i]):0;ax[i]=mask&(1u<<i)&&!(nan&(1u<<i))?dvalue(b[i]):1;}return nan;
}
static PW_ATAN_SCALAR_HELPER void pw_atan_dp_nan_inputs(unsigned nan,const uint64_t a[8],const uint64_t b[8],double va[8],double vb[8]) {
  for(unsigned i=0;i<8;++i)if(nan&(1u<<i)){va[i]=dvalue(a[i]);vb[i]=dvalue(b[i]);}
}
static PW_ATAN_SCALAR_HELPER void pw_atan_dp_nan_merge(unsigned nan,const uint64_t words[8],uint64_t out[8]) {
  for(unsigned i=0;i<8;++i)if(nan&(1u<<i))out[i]=words[i];
}
static PW_ATAN_SCALAR_HELPER void pw_atan_dp_inactive(unsigned mask,const uint64_t pass[8],uint64_t out[8]) {
  for(unsigned i=0;i<8;++i)if(!(mask&(1u<<i)))out[i]=pass[i];
}
static PW_ATAN_SCALAR_HELPER unsigned pw_atan_sp2_inputs(const uint32_t a[16],const uint32_t b[16],unsigned mask,unsigned group,unsigned nan,double ay[8],double ax[8]) {
  for(unsigned i=0;i<8;++i){unsigned lane=group*8+i;float fa=0,fb=1;if((mask&(1u<<lane))&&((a[lane]&0x7fffffffu)>0x7f800000u||(b[lane]&0x7fffffffu)>0x7f800000u))nan|=1u<<lane;if((mask&(1u<<lane))&&!(nan&(1u<<lane))){memcpy(&fa,&a[lane],4);memcpy(&fb,&b[lane],4);}ay[i]=(double)fa;ax[i]=(double)fb;}return nan;
}
static PW_ATAN_SCALAR_HELPER void pw_atan_sp_results(const double result[8],unsigned group,uint32_t out[16]) {
  for(unsigned i=0;i<8;++i){float r=(float)result[i];memcpy(&out[group*8+i],&r,4);}
}
static PW_ATAN_SCALAR_HELPER void pw_atan_sp2_nan_inputs(unsigned nan,const uint32_t a[16],const uint32_t b[16],float va[16],float vb[16]) {
  for(unsigned i=0;i<16;++i)if(nan&(1u<<i)){memcpy(&va[i],&a[i],4);memcpy(&vb[i],&b[i],4);}
}
static PW_ATAN_SCALAR_HELPER void pw_atan_sp_nan_merge(unsigned nan,const uint32_t words[16],uint32_t out[16]) {
  for(unsigned i=0;i<16;++i)if(nan&(1u<<i))out[i]=words[i];
}
static PW_ATAN_SCALAR_HELPER void pw_atan_sp_inactive(unsigned mask,const uint32_t pass[16],uint32_t out[16]) {
  for(unsigned i=0;i<16;++i)if(!(mask&(1u<<i)))out[i]=pass[i];
}
static PW_ATAN_SCALAR_HELPER unsigned pw_atan_sp_inputs(const uint32_t saved[16],unsigned mask,unsigned group,unsigned nan,double values[8]) {
  for(unsigned i=0;i<8;++i){unsigned lane=group*8+i;float f=0;if((mask&(1u<<lane))&&(saved[lane]&0x7fffffffu)>0x7f800000u)nan|=1u<<lane;if((mask&(1u<<lane))&&!(nan&(1u<<lane)))memcpy(&f,&saved[lane],4);values[i]=(double)f;}return nan;
}
static PW_ATAN_SCALAR_HELPER void pw_atan_sp_nan_inputs(unsigned nan,const uint32_t saved[16],float v[16]) {
  for(unsigned i=0;i<16;++i)if(nan&(1u<<i))memcpy(&v[i],&saved[i],4);
}

static __attribute__((noinline)) void atan_core(const double input[8],const double correction[8],double output[8],double low[8]) {
  dv x,na,nb,da,db,h,l;int id[8];unsigned tiny[8],large[8];uint64_t sign[8];
  double lane_x[8],lane_na[8],lane_nb[8],lane_da[8],lane_db[8];
  pw_atan_classify(input,lane_x,lane_na,lane_nb,lane_da,lane_db,id,tiny,large,sign);
  memcpy(&x,lane_x,64);memcpy(&na,lane_na,64);memcpy(&nb,lane_nb,64);memcpy(&da,lane_da,64);memcpy(&db,lane_db,64);
  pw_atan_register_lookup(id,&h,&l);
  x=pw_mvec_divide_finite(na*x+nb,da*x+db);const dv z=x*x,w=z*z;
  const dv s1=z*(aT[0]+w*(aT[2]+w*(aT[4]+w*(aT[6]+w*(aT[8]+w*aT[10]))))),s2=w*(aT[1]+w*(aT[3]+w*(aT[5]+w*(aT[7]+w*aT[9]))));
  dv corr;memcpy(&corr,correction,64);const dv poly=x*(s1+s2),direct_tail=corr-poly,reduced_tail=corr-(poly-l-x);
  double lane_h[8],lane_direct[8],lane_reduced[8];
  memcpy(lane_x,&x,64);memcpy(lane_h,&h,64);memcpy(lane_direct,&direct_tail,64);memcpy(lane_reduced,&reduced_tail,64);
  pw_atan_reconstruct(input,correction,output,low,tiny,large,id,sign,lane_x,lane_h,lane_direct,lane_reduced);
}
static __attribute__((noinline)) void atan2_core(const double y[8],const double x[8],double output[8]) {
  const double pi=3.1415926535897931160E+00,pi_lo=1.2246467991473531772E-16;
  dv numerator,denominator;double ratio[8],angle[8],angle_low[8],correction[8];unsigned direct=0,negative=0;uint64_t special[8],ysign[8];
  double lane_numerator[8],lane_denominator[8];
  pw_atan2_classify(y,x,lane_numerator,lane_denominator,&direct,&negative,special,ysign);
  memcpy(&numerator,lane_numerator,64);memcpy(&denominator,lane_denominator,64);
  const dv quotient=pw_mvec_divide_finite(numerator,denominator);memcpy(ratio,&quotient,64);
  /* Exact common-power scaling keeps Dekker products normal and bounded.
   * Only moderate exponent differences need a compensated division tail. */
  dv ny,nx,rq;
  double lane_ny[8],lane_nx[8],lane_rq[8];
  pw_atan2_scale(lane_numerator,lane_denominator,ratio,lane_ny,lane_nx,lane_rq);
  memcpy(&ny,lane_ny,64);memcpy(&nx,lane_nx,64);memcpy(&rq,lane_rq,64);
  dv rh,xh;double lane_rh[8],lane_xh[8];
  pw_atan2_dekker_heads(lane_rq,lane_nx,lane_rh,lane_xh);memcpy(&rh,lane_rh,64);memcpy(&xh,lane_xh,64);
  const dv rl=rq-rh,xl=nx-xh,product=rq*nx,product_tail=((rh*xh-product)+rh*xl+rl*xh)+rl*xl;
  const dv division_tail=pw_mvec_divide_finite((ny-product)-product_tail,nx),angle_correction=pw_mvec_divide_finite(division_tail,1+rq*rq);memcpy(correction,&angle_correction,64);
  atan_core(ratio,correction,angle,angle_low);
  dv z,qz,ql;double lane_qz[8],lane_ql[8];memcpy(&z,angle,64);
  pw_atan2_quadrant_inputs(negative,angle,angle_low,lane_qz,lane_ql);memcpy(&qz,lane_qz,64);memcpy(&ql,lane_ql,64);
  const dv sum=pi-qz,error=(pi-sum)-qz,adjusted=sum+(error+pi_lo-ql);
  double lane_adjusted[8];memcpy(lane_adjusted,&adjusted,64);
  pw_atan2_reconstruct(direct,negative,special,ysign,lane_adjusted,angle,output);
}
int phi_host_atan2_e8(const uint64_t y[8],const uint64_t x[8],unsigned mask,const uint64_t merge[8],uint64_t output[8]) {
  if(mask&~255u)return 1;uint64_t a[8],b[8],pass[8],out[8];double ay[8],ax[8],result[8];unsigned nan=0;memcpy(a,y,64);memcpy(b,x,64);memcpy(pass,merge,64);if(!mask){memcpy(output,pass,64);return 0;}
  nan=pw_atan_dp_inputs(a,b,mask,ay,ax);
  atan2_core(ay,ax,result);memcpy(out,result,64);if(nan){dv va={0},vb={0};double lane_va[8]={0},lane_vb[8]={0};pw_atan_dp_nan_inputs(nan,a,b,lane_va,lane_vb);memcpy(&va,lane_va,64);memcpy(&vb,lane_vb,64);const dv n=va+vb;uint64_t words[8];memcpy(words,&n,64);pw_atan_dp_nan_merge(nan,words,out);}
  pw_atan_dp_inactive(mask,pass,out);memcpy(output,out,64);return 0;
}
int phi_host_atan2f_e16(const uint32_t y[16],const uint32_t x[16],unsigned mask,const uint32_t merge[16],uint32_t output[16]) {
  if(mask&~65535u)return 1;uint32_t a[16],b[16],pass[16],out[16];unsigned nan=0;memcpy(a,y,64);memcpy(b,x,64);memcpy(pass,merge,64);if(!mask){memcpy(output,pass,64);return 0;}
  for(unsigned group=0;group<2;++group){double ay[8],ax[8],result[8];nan=pw_atan_sp2_inputs(a,b,mask,group,nan,ay,ax);atan2_core(ay,ax,result);pw_atan_sp_results(result,group,out);}
  if(nan){fv va={0},vb={0};float lane_va[16]={0},lane_vb[16]={0};pw_atan_sp2_nan_inputs(nan,a,b,lane_va,lane_vb);memcpy(&va,lane_va,64);memcpy(&vb,lane_vb,64);const fv n=va+vb;uint32_t words[16];memcpy(words,&n,64);pw_atan_sp_nan_merge(nan,words,out);}pw_atan_sp_inactive(mask,pass,out);memcpy(output,out,64);return 0;
}
int phi_host_atanf_e16(const uint32_t input[16],unsigned mask,const uint32_t merge[16],uint32_t output[16]) {
  if(mask&~65535u)return 1;uint32_t saved[16],pass[16],out[16];unsigned nan=0;memcpy(saved,input,64);memcpy(pass,merge,64);if(!mask){memcpy(output,pass,64);return 0;}
  for(unsigned group=0;group<2;++group){double values[8],result[8],zero[8]={0},low_result[8];nan=pw_atan_sp_inputs(saved,mask,group,nan,values);atan_core(values,zero,result,low_result);pw_atan_sp_results(result,group,out);}
  if(nan){fv v={0};float lane_v[16]={0};pw_atan_sp_nan_inputs(nan,saved,lane_v);memcpy(&v,lane_v,64);const fv n=v+v;uint32_t words[16];memcpy(words,&n,64);pw_atan_sp_nan_merge(nan,words,out);}pw_atan_sp_inactive(mask,pass,out);memcpy(output,out,64);return 0;
}
