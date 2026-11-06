/* GCC-vector adaptation of official musl v1.2.5 atan.c and atan2.c.
 * ====================================================
 * Copyright (C) 1993 by Sun Microsystems, Inc. All rights reserved.
 * Developed at SunSoft/SunPro, a Sun Microsystems, Inc. business.
 * Permission to use, copy, modify, and distribute this software is freely
 * granted, provided that this notice is preserved.
 * ====================================================
 * Changes:8-DP vector reductions/polynomial and safe ratio/quadrant handling;
 * SP16 widens two groups and rounds once. Full64B private raw-pointer/mask ABI.
 * No scalar atan/atan2 fallback. Host source experiment, target/G5 unqualified.
 */
#include "atan_e.h"
#include <string.h>
#ifdef __FAST_MATH__
#error "atan_e requires strict FP"
#endif
typedef double dv __attribute__((vector_size(64)));
typedef float fv __attribute__((vector_size(64)));
static uint64_t dbits(double x){uint64_t b;memcpy(&b,&x,8);return b;}
static double dvalue(uint64_t b){double x;memcpy(&x,&b,8);return x;}
static const double hi[]={4.63647609000806093515e-01,7.85398163397448278999e-01,9.82793723247329054082e-01,1.57079632679489655800e+00};
static const double lo[]={2.26987774529616870924e-17,3.06161699786838301793e-17,1.39033110312309984516e-17,6.12323399573676603587e-17};
static const double aT[]={3.33333333333329318027e-01,-1.99999999998764832476e-01,1.42857142725034663711e-01,-1.11111104054623557880e-01,9.09088713343650656196e-02,-7.69187620504482999495e-02,6.66107313738753120669e-02,-5.83357013379057348645e-02,4.97687799461593236017e-02,-3.65315727442169155270e-02,1.62858201153657823623e-02};
static __attribute__((noinline)) void atan_core(const double input[8],double output[8]) {
  dv x,na,nb,da,db,h,l;int id[8];unsigned tiny[8],large[8];uint64_t sign[8];
  for(unsigned i=0;i<8;++i){uint64_t b=dbits(input[i]),m=b&UINT64_C(0x7fffffffffffffff);sign[i]=b&UINT64_C(0x8000000000000000);tiny[i]=m<UINT64_C(0x3e40000000000000);large[i]=m>=UINT64_C(0x4410000000000000);x[i]=tiny[i]||large[i]?0:dvalue(m);id[i]=m<UINT64_C(0x3fdc000000000000)?-1:m<UINT64_C(0x3fe6000000000000)?0:m<UINT64_C(0x3ff3000000000000)?1:m<UINT64_C(0x4003800000000000)?2:3;if(tiny[i]||large[i])id[i]=-1;
    na[i]=id[i]==0?2:id[i]==3?0:1;nb[i]=id[i]==0||id[i]==1||id[i]==3?-1:id[i]==2?-1.5:0;da[i]=id[i]==0||id[i]==1||id[i]==3?1:id[i]==2?1.5:0;db[i]=id[i]==0?2:id[i]==3?0:1;h[i]=id[i]<0?0:hi[id[i]];l[i]=id[i]<0?0:lo[id[i]];}
  x=(na*x+nb)/(da*x+db);const dv z=x*x,w=z*z;
  const dv s1=z*(aT[0]+w*(aT[2]+w*(aT[4]+w*(aT[6]+w*(aT[8]+w*aT[10]))))),s2=w*(aT[1]+w*(aT[3]+w*(aT[5]+w*(aT[7]+w*aT[9]))));
  const dv direct=x-x*(s1+s2),reduced=h-(x*(s1+s2)-l-x);
  for(unsigned i=0;i<8;++i){if(tiny[i]){output[i]=input[i];continue;}double r=large[i]?hi[3]:id[i]<0?direct[i]:reduced[i];output[i]=dvalue(dbits(r)^sign[i]);}
}
static __attribute__((noinline)) void atan2_core(const double y[8],const double x[8],double output[8]) {
  const double pi=3.1415926535897931160E+00,pi_lo=1.2246467991473531772E-16;
  dv numerator,denominator;double ratio[8],angle[8];unsigned direct=0,negative=0;uint64_t special[8],ysign[8];
  for(unsigned i=0;i<8;++i){uint64_t yb=dbits(y[i]),xb=dbits(x[i]),ym=yb&UINT64_C(0x7fffffffffffffff),xm=xb&UINT64_C(0x7fffffffffffffff);ysign[i]=yb&UINT64_C(0x8000000000000000);unsigned neg=(unsigned)(xb>>63);uint32_t iy=(uint32_t)(ym>>32),ix=(uint32_t)(xm>>32);numerator[i]=0;denominator[i]=1;special[i]=0;
    if(!ym){direct|=1u<<i;special[i]=dbits(neg?pi:0)^ysign[i];}
    else if(!xm){direct|=1u<<i;special[i]=dbits(pi/2)^ysign[i];}
    else if(xm==UINT64_C(0x7ff0000000000000)){direct|=1u<<i;special[i]=dbits(ym==UINT64_C(0x7ff0000000000000)?(neg?3*pi/4:pi/4):(neg?pi:0))^ysign[i];}
    else if(ix+(64u<<20)<iy||ym==UINT64_C(0x7ff0000000000000)){direct|=1u<<i;special[i]=dbits(pi/2)^ysign[i];}
    else {if(neg)negative|=1u<<i;if(!(neg&&iy+(64u<<20)<ix)){numerator[i]=dvalue(ym);denominator[i]=dvalue(xm);}}
  }
  const dv quotient=numerator/denominator;memcpy(ratio,&quotient,64);atan_core(ratio,angle);
  dv z,adjust_input;memcpy(&z,angle,64);for(unsigned i=0;i<8;++i)adjust_input[i]=negative&(1u<<i)?z[i]:pi_lo;const dv adjusted=pi-(adjust_input-pi_lo);
  for(unsigned i=0;i<8;++i)output[i]=direct&(1u<<i)?dvalue(special[i]):dvalue(dbits(negative&(1u<<i)?adjusted[i]:z[i])^ysign[i]);
}
int phi_host_atan2_e8(const uint64_t y[8],const uint64_t x[8],unsigned mask,const uint64_t merge[8],uint64_t output[8]) {
  if(mask&~255u)return 1;uint64_t a[8],b[8],pass[8],out[8];double ay[8],ax[8],result[8];unsigned nan=0;memcpy(a,y,64);memcpy(b,x,64);memcpy(pass,merge,64);if(!mask){memcpy(output,pass,64);return 0;}
  for(unsigned i=0;i<8;++i){if((mask&(1u<<i))&&((a[i]&UINT64_C(0x7fffffffffffffff))>UINT64_C(0x7ff0000000000000)||(b[i]&UINT64_C(0x7fffffffffffffff))>UINT64_C(0x7ff0000000000000)))nan|=1u<<i;ay[i]=mask&(1u<<i)&&!(nan&(1u<<i))?dvalue(a[i]):0;ax[i]=mask&(1u<<i)&&!(nan&(1u<<i))?dvalue(b[i]):1;}
  atan2_core(ay,ax,result);memcpy(out,result,64);if(nan){dv va={0},vb={0};for(unsigned i=0;i<8;++i)if(nan&(1u<<i)){va[i]=dvalue(a[i]);vb[i]=dvalue(b[i]);}const dv n=va+vb;uint64_t words[8];memcpy(words,&n,64);for(unsigned i=0;i<8;++i)if(nan&(1u<<i))out[i]=words[i];}
  for(unsigned i=0;i<8;++i)if(!(mask&(1u<<i)))out[i]=pass[i];memcpy(output,out,64);return 0;
}
int phi_host_atan2f_e16(const uint32_t y[16],const uint32_t x[16],unsigned mask,const uint32_t merge[16],uint32_t output[16]) {
  if(mask&~65535u)return 1;uint32_t a[16],b[16],pass[16],out[16];unsigned nan=0;memcpy(a,y,64);memcpy(b,x,64);memcpy(pass,merge,64);if(!mask){memcpy(output,pass,64);return 0;}
  for(unsigned group=0;group<2;++group){double ay[8],ax[8],result[8];for(unsigned i=0;i<8;++i){unsigned lane=group*8+i;float fa=0,fb=1;if((mask&(1u<<lane))&&((a[lane]&0x7fffffffu)>0x7f800000u||(b[lane]&0x7fffffffu)>0x7f800000u))nan|=1u<<lane;if((mask&(1u<<lane))&&!(nan&(1u<<lane))){memcpy(&fa,&a[lane],4);memcpy(&fb,&b[lane],4);}ay[i]=(double)fa;ax[i]=(double)fb;}atan2_core(ay,ax,result);for(unsigned i=0;i<8;++i){float r=(float)result[i];memcpy(&out[group*8+i],&r,4);}}
  if(nan){fv va={0},vb={0};for(unsigned i=0;i<16;++i)if(nan&(1u<<i)){memcpy(&va[i],&a[i],4);memcpy(&vb[i],&b[i],4);}const fv n=va+vb;uint32_t words[16];memcpy(words,&n,64);for(unsigned i=0;i<16;++i)if(nan&(1u<<i))out[i]=words[i];}for(unsigned i=0;i<16;++i)if(!(mask&(1u<<i)))out[i]=pass[i];memcpy(output,out,64);return 0;
}
int phi_host_atanf_e16(const uint32_t input[16],unsigned mask,const uint32_t merge[16],uint32_t output[16]) {
  if(mask&~65535u)return 1;uint32_t saved[16],pass[16],out[16];unsigned nan=0;memcpy(saved,input,64);memcpy(pass,merge,64);if(!mask){memcpy(output,pass,64);return 0;}
  for(unsigned group=0;group<2;++group){double values[8],result[8];for(unsigned i=0;i<8;++i){unsigned lane=group*8+i;float f=0;if((mask&(1u<<lane))&&(saved[lane]&0x7fffffffu)>0x7f800000u)nan|=1u<<lane;if((mask&(1u<<lane))&&!(nan&(1u<<lane)))memcpy(&f,&saved[lane],4);values[i]=(double)f;}atan_core(values,result);for(unsigned i=0;i<8;++i){float r=(float)result[i];memcpy(&out[group*8+i],&r,4);}}
  if(nan){fv v={0};for(unsigned i=0;i<16;++i)if(nan&(1u<<i))memcpy(&v[i],&saved[i],4);const fv n=v+v;uint32_t words[16];memcpy(words,&n,64);for(unsigned i=0;i<16;++i)if(nan&(1u<<i))out[i]=words[i];}for(unsigned i=0;i<16;++i)if(!(mask&(1u<<i)))out[i]=pass[i];memcpy(output,out,64);return 0;
}
