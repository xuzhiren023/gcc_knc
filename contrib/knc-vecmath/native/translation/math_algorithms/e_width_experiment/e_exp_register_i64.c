/* Additive64-bit-lane source candidate; original source/header preserved.
 * No inherited host accuracy, target ABI/ISA or G5 qualification.
 * Arm table copyrights/licenses in the original algorithm comments apply. */
/* Source-only gather-free DP8 exp candidate: exact Arm N128 table bits.
 * Sixteen fixed eight-entry shards per field use64-bit shuffles.
 * Arithmetic/special paths are unchanged; new emission/accuracy/ABI/G5 pending.
 * See REGISTER_EXP_PLAN.md. */
/* Fresh parameterized host e-width adaptation; old source SHA256 33be43e36792b9ecce7a47a496fadf09fa90f4443798a9b902be45a24d086255.
 * Private pointer ABI only; software mask is not a GNU masked-vector ABI. */
#define PW_LANES 8
#define PW_ALL ((1u<<PW_LANES)-1u)
/* Four-lane adaptation of Arm optimized-routines v26.01 exp.c/math_err.c.
 * Copyright (c) 2018-2025, Arm Limited. SPDX-License-Identifier: MIT
 * Commit649ccc8411e7c4862965710f25c570d854a1483f; exact data/license retained.
 * Preserve the upstream tiny-input and compensated large-result branches.
 * Host-only research, no scalar exp delegation or target _ZGV exports.
 */
#include "e_algorithms.h"
#include "math_config.h"
#include <string.h>
typedef double pw_f64v __attribute__((vector_size(PW_LANES*8)));
typedef unsigned long long pw_u64v __attribute__((vector_size(PW_LANES*8)));
_Static_assert(EXP_TABLE_BITS==7 && EXP_POLY_ORDER==5 && EXP_USE_TOINT_NARROW==0 && EXP_POLY_WIDE==0,"unsupported upstream configuration");
/* Exact original table words reconstructed as64-bit constants; no integer narrowing. */
typedef long long v8di __attribute__((vector_size(64)));
static const pw_u64v pw_exp_tail_0 __attribute__((aligned(64))) = {
  0x0000000000000000ULL, 0x3c9b3b4f1a88bf6eULL, 0xbc7160139cd8dc5dULL, 0xbc905e7a108766d1ULL, 0x3c8cd2523567f613ULL, 0xbc8bce8023f98efaULL, 0x3c60f74e61e6c861ULL, 0x3c90a3e45b33d399ULL
};
static const pw_u64v pw_exp_tail_1 __attribute__((aligned(64))) = {
  0x3c979aa65d837b6dULL, 0x3c8eb51a92fdeffcULL, 0x3c3ebe3d702f9cd1ULL, 0xbc6a033489906e0bULL, 0xbc9556522a2fbd0eULL, 0xbc5080ef8c4eea55ULL, 0xbc91c923b9d5f416ULL, 0x3c80d3e3e95c55afULL
};
static const pw_u64v pw_exp_tail_2 __attribute__((aligned(64))) = {
  0xbc801b15eaa59348ULL, 0xbc8f1ff055de323dULL, 0x3c8b898c3f1353bfULL, 0xbc96d99c7611eb26ULL, 0x3c9aecf73e3a2f60ULL, 0xbc8fe782cb86389dULL, 0x3c8a6f4144a6c38dULL, 0x3c807a05b0e4047dULL
};
static const pw_u64v pw_exp_tail_3 __attribute__((aligned(64))) = {
  0x3c968efde3a8a894ULL, 0x3c875e18f274487dULL, 0x3c80472b981fe7f2ULL, 0xbc96b87b3f71085eULL, 0x3c82f7e16d09ab31ULL, 0xbc3d219b1a6fbffaULL, 0x3c8b3782720c0ab4ULL, 0x3c6e149289cecb8fULL
};
static const pw_u64v pw_exp_tail_4 __attribute__((aligned(64))) = {
  0x3c834d754db0abb6ULL, 0x3c864201e2ac744cULL, 0x3c8fdd395dd3f84aULL, 0xbc86a3803b8e5b04ULL, 0xbc924aedcc4b5068ULL, 0xbc9907f81b512d8eULL, 0xbc71d1e83e9436d2ULL, 0xbc991919b3ce1b15ULL
};
static const pw_u64v pw_exp_tail_5 __attribute__((aligned(64))) = {
  0x3c859f48a72a4c6dULL, 0xbc9312607a28698aULL, 0xbc58a78f4817895bULL, 0xbc7c2c9b67499a1bULL, 0x3c4363ed60c2ac11ULL, 0x3c9666093b0664efULL, 0x3c6ecce1daa10379ULL, 0x3c93ff8e3f0f1230ULL
};
static const pw_u64v pw_exp_tail_6 __attribute__((aligned(64))) = {
  0x3c7690cebb7aafb0ULL, 0x3c931dbdeb54e077ULL, 0xbc8f94340071a38eULL, 0xbc87deccdc93a349ULL, 0xbc78dec6bd0f385fULL, 0xbc861246ec7b5cf6ULL, 0x3c93350518fdd78eULL, 0x3c7b98b72f8a9b05ULL
};
static const pw_u64v pw_exp_tail_7 __attribute__((aligned(64))) = {
  0x3c9063e1e21c5409ULL, 0x3c34c7855019c6eaULL, 0x3c9432e62b64c035ULL, 0xbc8ce44a6199769fULL, 0xbc8c33c53bef4da8ULL, 0xbc845378892be9aeULL, 0xbc93cedd78565858ULL, 0x3c5710aa807e1964ULL
};
static const pw_u64v pw_exp_tail_8 __attribute__((aligned(64))) = {
  0xbc93b3efbf5e2228ULL, 0xbc6a12ad8734b982ULL, 0xbc6367efb86da9eeULL, 0xbc80dc3d54e08851ULL, 0xbc781f647e5a3ecfULL, 0xbc86ee4ac08b7db0ULL, 0xbc8619321e55e68aULL, 0x3c909ccb5e09d4d3ULL
};
static const pw_u64v pw_exp_tail_9 __attribute__((aligned(64))) = {
  0xbc7b32dcb94da51dULL, 0x3c94ecfd5467c06bULL, 0x3c65ebe1abd66c55ULL, 0xbc88a1c52fb3cf42ULL, 0xbc9369b6f13b3734ULL, 0xbc805e843a19ff1eULL, 0xbc94d450d872576eULL, 0x3c90ad675b0e8a00ULL
};
static const pw_u64v pw_exp_tail_10 __attribute__((aligned(64))) = {
  0x3c8db72fc1f0eab4ULL, 0xbc65b6609cc5e7ffULL, 0x3c7bf68359f35f44ULL, 0xbc93091fa71e3d83ULL, 0xbc5da9b88b6c1e29ULL, 0xbc6c23f97c90b959ULL, 0xbc92434322f4f9aaULL, 0xbc85ca6cd7668e4bULL
};
static const pw_u64v pw_exp_tail_11 __attribute__((aligned(64))) = {
  0x3c71affc2b91ce27ULL, 0x3c6dd235e10a73bbULL, 0xbc87c50422622263ULL, 0x3c8b1c86e3e231d5ULL, 0xbc91bbd1d3bcbb15ULL, 0x3c90cc319cee31d2ULL, 0x3c8469846e735ab3ULL, 0xbc82dfcd978e9db4ULL
};
static const pw_u64v pw_exp_tail_12 __attribute__((aligned(64))) = {
  0x3c8c1a7792cb3387ULL, 0xbc907b8f4ad1d9faULL, 0xbc55c3d956dcaebaULL, 0xbc90a40e3da6f640ULL, 0xbc68d6f438ad9334ULL, 0xbc91eee26b588a35ULL, 0x3c74ffd70a5fddcdULL, 0xbc91bdfbfa9298acULL
};
static const pw_u64v pw_exp_tail_13 __attribute__((aligned(64))) = {
  0x3c736eae30af0cb3ULL, 0x3c8ee3325c9ffd94ULL, 0x3c84e08fd10959acULL, 0x3c63cdaf384e1a67ULL, 0x3c676b2c6c921968ULL, 0xbc808a1883ccb5d2ULL, 0xbc8fad5d3ffffa6fULL, 0xbc900dae3875a949ULL
};
static const pw_u64v pw_exp_tail_14 __attribute__((aligned(64))) = {
  0x3c74a385a63d07a7ULL, 0xbc82919e2040220fULL, 0x3c8e5a50d5c192acULL, 0x3c843a59ac016b4bULL, 0xbc82d52107b43e1fULL, 0xbc892ab93b470dc9ULL, 0x3c74b604603a88d3ULL, 0x3c83c5ec519d7271ULL
};
static const pw_u64v pw_exp_tail_15 __attribute__((aligned(64))) = {
  0xbc8ff7128fd391f0ULL, 0xbc8dae98e223747dULL, 0x3c8ec3bc41aa2008ULL, 0x3c842b94c3a9eb32ULL, 0x3c8a64a931d185eeULL, 0xbc8e37bae43be3edULL, 0x3c77893b4d91cd9dULL, 0x3c5305c14160cc89ULL
};
static const pw_u64v pw_exp_scale_0 __attribute__((aligned(64))) = {
  0x3ff0000000000000ULL, 0x3feff63da9fb3335ULL, 0x3fefec9a3e778061ULL, 0x3fefe315e86e7f85ULL, 0x3fefd9b0d3158574ULL, 0x3fefd06b29ddf6deULL, 0x3fefc74518759bc8ULL, 0x3fefbe3ecac6f383ULL
};
static const pw_u64v pw_exp_scale_1 __attribute__((aligned(64))) = {
  0x3fefb5586cf9890fULL, 0x3fefac922b7247f7ULL, 0x3fefa3ec32d3d1a2ULL, 0x3fef9b66affed31bULL, 0x3fef9301d0125b51ULL, 0x3fef8abdc06c31ccULL, 0x3fef829aaea92de0ULL, 0x3fef7a98c8a58e51ULL
};
static const pw_u64v pw_exp_scale_2 __attribute__((aligned(64))) = {
  0x3fef72b83c7d517bULL, 0x3fef6af9388c8deaULL, 0x3fef635beb6fcb75ULL, 0x3fef5be084045cd4ULL, 0x3fef54873168b9aaULL, 0x3fef4d5022fcd91dULL, 0x3fef463b88628cd6ULL, 0x3fef3f49917ddc96ULL
};
static const pw_u64v pw_exp_scale_3 __attribute__((aligned(64))) = {
  0x3fef387a6e756238ULL, 0x3fef31ce4fb2a63fULL, 0x3fef2b4565e27cddULL, 0x3fef24dfe1f56381ULL, 0x3fef1e9df51fdee1ULL, 0x3fef187fd0dad990ULL, 0x3fef1285a6e4030bULL, 0x3fef0cafa93e2f56ULL
};
static const pw_u64v pw_exp_scale_4 __attribute__((aligned(64))) = {
  0x3fef06fe0a31b715ULL, 0x3fef0170fc4cd831ULL, 0x3feefc08b26416ffULL, 0x3feef6c55f929ff1ULL, 0x3feef1a7373aa9cbULL, 0x3feeecae6d05d866ULL, 0x3feee7db34e59ff7ULL, 0x3feee32dc313a8e5ULL
};
static const pw_u64v pw_exp_scale_5 __attribute__((aligned(64))) = {
  0x3feedea64c123422ULL, 0x3feeda4504ac801cULL, 0x3feed60a21f72e2aULL, 0x3feed1f5d950a897ULL, 0x3feece086061892dULL, 0x3feeca41ed1d0057ULL, 0x3feec6a2b5c13cd0ULL, 0x3feec32af0d7d3deULL
};
static const pw_u64v pw_exp_scale_6 __attribute__((aligned(64))) = {
  0x3feebfdad5362a27ULL, 0x3feebcb299fddd0dULL, 0x3feeb9b2769d2ca7ULL, 0x3feeb6daa2cf6642ULL, 0x3feeb42b569d4f82ULL, 0x3feeb1a4ca5d920fULL, 0x3feeaf4736b527daULL, 0x3feead12d497c7fdULL
};
static const pw_u64v pw_exp_scale_7 __attribute__((aligned(64))) = {
  0x3feeab07dd485429ULL, 0x3feea9268a5946b7ULL, 0x3feea76f15ad2148ULL, 0x3feea5e1b976dc09ULL, 0x3feea47eb03a5585ULL, 0x3feea34634ccc320ULL, 0x3feea23882552225ULL, 0x3feea155d44ca973ULL
};
static const pw_u64v pw_exp_scale_8 __attribute__((aligned(64))) = {
  0x3feea09e667f3bcdULL, 0x3feea012750bdabfULL, 0x3fee9fb23c651a2fULL, 0x3fee9f7df9519484ULL, 0x3fee9f75e8ec5f74ULL, 0x3fee9f9a48a58174ULL, 0x3fee9feb564267c9ULL, 0x3feea0694fde5d3fULL
};
static const pw_u64v pw_exp_scale_9 __attribute__((aligned(64))) = {
  0x3feea11473eb0187ULL, 0x3feea1ed0130c132ULL, 0x3feea2f336cf4e62ULL, 0x3feea427543e1a12ULL, 0x3feea589994cce13ULL, 0x3feea71a4623c7adULL, 0x3feea8d99b4492edULL, 0x3feeaac7d98a6699ULL
};
static const pw_u64v pw_exp_scale_10 __attribute__((aligned(64))) = {
  0x3feeace5422aa0dbULL, 0x3feeaf3216b5448cULL, 0x3feeb1ae99157736ULL, 0x3feeb45b0b91ffc6ULL, 0x3feeb737b0cdc5e5ULL, 0x3feeba44cbc8520fULL, 0x3feebd829fde4e50ULL, 0x3feec0f170ca07baULL
};
static const pw_u64v pw_exp_scale_11 __attribute__((aligned(64))) = {
  0x3feec49182a3f090ULL, 0x3feec86319e32323ULL, 0x3feecc667b5de565ULL, 0x3feed09bec4a2d33ULL, 0x3feed503b23e255dULL, 0x3feed99e1330b358ULL, 0x3feede6b5579fdbfULL, 0x3feee36bbfd3f37aULL
};
static const pw_u64v pw_exp_scale_12 __attribute__((aligned(64))) = {
  0x3feee89f995ad3adULL, 0x3feeee07298db666ULL, 0x3feef3a2b84f15fbULL, 0x3feef9728de5593aULL, 0x3feeff76f2fb5e47ULL, 0x3fef05b030a1064aULL, 0x3fef0c1e904bc1d2ULL, 0x3fef12c25bd71e09ULL
};
static const pw_u64v pw_exp_scale_13 __attribute__((aligned(64))) = {
  0x3fef199bdd85529cULL, 0x3fef20ab5fffd07aULL, 0x3fef27f12e57d14bULL, 0x3fef2f6d9406e7b5ULL, 0x3fef3720dcef9069ULL, 0x3fef3f0b555dc3faULL, 0x3fef472d4a07897cULL, 0x3fef4f87080d89f2ULL
};
static const pw_u64v pw_exp_scale_14 __attribute__((aligned(64))) = {
  0x3fef5818dcfba487ULL, 0x3fef60e316c98398ULL, 0x3fef69e603db3285ULL, 0x3fef7321f301b460ULL, 0x3fef7c97337b9b5fULL, 0x3fef864614f5a129ULL, 0x3fef902ee78b3ff6ULL, 0x3fef9a51fbc74c83ULL
};
static const pw_u64v pw_exp_scale_15 __attribute__((aligned(64))) = {
  0x3fefa4afa2a490daULL, 0x3fefaf482d8e67f1ULL, 0x3fefba1bee615a27ULL, 0x3fefc52b376bba97ULL, 0x3fefd0765b6e4540ULL, 0x3fefdbfdad9cbe14ULL, 0x3fefe7c1819e90d8ULL, 0x3feff3c22b8f71f1ULL
};

static __attribute__((always_inline)) inline void
pw_exp_register_lookup(pw_u64v ki,pw_u64v *tailbits,pw_u64v *sbits) {
  const pw_u64v keys=ki&127ULL,group=keys>>3;
  const v8di selector=(v8di)(keys&7ULL);
  pw_u64v tails={0},scales={0};
  {
    const pw_u64v keep=(pw_u64v)(group==0ULL);
    tails|=__builtin_shuffle(pw_exp_tail_0,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_0,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==1ULL);
    tails|=__builtin_shuffle(pw_exp_tail_1,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_1,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==2ULL);
    tails|=__builtin_shuffle(pw_exp_tail_2,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_2,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==3ULL);
    tails|=__builtin_shuffle(pw_exp_tail_3,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_3,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==4ULL);
    tails|=__builtin_shuffle(pw_exp_tail_4,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_4,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==5ULL);
    tails|=__builtin_shuffle(pw_exp_tail_5,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_5,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==6ULL);
    tails|=__builtin_shuffle(pw_exp_tail_6,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_6,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==7ULL);
    tails|=__builtin_shuffle(pw_exp_tail_7,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_7,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==8ULL);
    tails|=__builtin_shuffle(pw_exp_tail_8,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_8,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==9ULL);
    tails|=__builtin_shuffle(pw_exp_tail_9,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_9,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==10ULL);
    tails|=__builtin_shuffle(pw_exp_tail_10,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_10,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==11ULL);
    tails|=__builtin_shuffle(pw_exp_tail_11,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_11,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==12ULL);
    tails|=__builtin_shuffle(pw_exp_tail_12,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_12,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==13ULL);
    tails|=__builtin_shuffle(pw_exp_tail_13,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_13,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==14ULL);
    tails|=__builtin_shuffle(pw_exp_tail_14,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_14,selector)&keep;
  }
  {
    const pw_u64v keep=(pw_u64v)(group==15ULL);
    tails|=__builtin_shuffle(pw_exp_tail_15,selector)&keep;
    scales|=__builtin_shuffle(pw_exp_scale_15,selector)&keep;
  }
  *tailbits=tails;*sbits=scales;
}

static __attribute__((noinline)) void pw_core_exp(const uint64_t input[PW_LANES],uint64_t output[PW_LANES]) {
  uint64_t active[PW_LANES],small_input[PW_LANES]={0,0,0,0},nan_input[PW_LANES]={0};
  unsigned tiny=0,large_pos=0,large_neg=0,over=0,under=0,nan=0,posinf=0,neginf=0;
  for(unsigned i=0;i<PW_LANES;++i) {
    const uint64_t bits=input[i],mag=bits&UINT64_C(0x7fffffffffffffff);active[i]=bits;
    if(mag>=UINT64_C(0x7ff0000000000000)) {
      active[i]=0;
      if(mag>UINT64_C(0x7ff0000000000000)) {nan|=1u<<i;nan_input[i]=bits;}
      else if(bits>>63)neginf|=1u<<i;else posinf|=1u<<i;
    } else if(mag<UINT64_C(0x3c90000000000000)) {
      tiny|=1u<<i;small_input[i]=bits;active[i]=0;
    } else if(mag>=UINT64_C(0x4090000000000000)) {
      active[i]=0;if(bits>>63)under|=1u<<i;else over|=1u<<i;
    } else if(mag>=UINT64_C(0x4080000000000000)) {
      if(bits>>63)large_neg|=1u<<i;else large_pos|=1u<<i;
    }
  }
  pw_f64v x;memcpy(&x,active,sizeof x);
  pw_f64v z=x*__exp_data.invln2N,kd=z+__exp_data.shift;
  pw_u64v ki;memcpy(&ki,&kd,sizeof ki);kd=kd-__exp_data.shift;
  const pw_f64v r=x+kd*__exp_data.negln2hiN+kd*__exp_data.negln2loN;
  pw_u64v tailbits,sbits;
  pw_exp_register_lookup(ki,&tailbits,&sbits);
  sbits=sbits+(ki<<45);
  pw_f64v tail;memcpy(&tail,&tailbits,sizeof tail);
  const pw_f64v r2=r*r;
  const pw_f64v tmp=tail+r+r2*(__exp_data.poly[0]+r*__exp_data.poly[1])+r2*r2*(__exp_data.poly[2]+r*__exp_data.poly[3]);
  pw_u64v normal_bits=sbits;
  for(unsigned i=0;i<PW_LANES;++i)if((large_pos|large_neg)&(1u<<i))normal_bits[i]=UINT64_C(0x3ff0000000000000);
  pw_f64v scale;memcpy(&scale,&normal_bits,sizeof scale);
  const pw_f64v normal=scale+scale*tmp;memcpy(output,&normal,sizeof normal);
  if(large_pos) {
    pw_u64v bits=(pw_u64v){0}+(0x3ff0000000000000);
    pw_f64v t=(pw_f64v){0}+(0);
    for(unsigned i=0;i<PW_LANES;++i)if(large_pos&(1u<<i)){bits[i]=sbits[i]-(UINT64_C(1009)<<52);t[i]=tmp[i];}
    pw_f64v s;memcpy(&s,&bits,sizeof s);
    const pw_f64v y=0x1p1009*(s+s*t);uint64_t words[PW_LANES];memcpy(words,&y,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i)if(large_pos&(1u<<i))output[i]=words[i];
  }
  if(large_neg) {
    pw_u64v bits=(pw_u64v){0}+(0x3ff0000000000000);
    pw_f64v t=(pw_f64v){0}+(0);
    for(unsigned i=0;i<PW_LANES;++i)if(large_neg&(1u<<i)){bits[i]=sbits[i]+(UINT64_C(1022)<<52);t[i]=tmp[i];}
    pw_f64v s;memcpy(&s,&bits,sizeof s);pw_f64v y=s+s*t;
    unsigned subnormal=0;
    for(unsigned i=0;i<PW_LANES;++i)if((large_neg&(1u<<i)) && y[i]<1.0)subnormal|=1u<<i;
    if(subnormal) {
      pw_f64v lo=s-y+s*t;
      const pw_f64v hi=1.0+y;
      lo=1.0-hi+y+lo;
      const pw_f64v rounded=(hi+lo)-1.0;
      for(unsigned i=0;i<PW_LANES;++i)if(subnormal&(1u<<i))y[i]=rounded[i];
      /* Original explicit underflow effect, not a folded constant. */
      volatile double factor=0x1p-1022;
      volatile double force_underflow=factor*factor;(void)force_underflow;
    }
    const pw_f64v result=0x1p-1022*y;uint64_t words[PW_LANES];memcpy(words,&result,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i)if(large_neg&(1u<<i))output[i]=words[i];
  }
  if(tiny) {
    /* Crucially, original tiny inputs never reach the polynomial above. */
    pw_f64v s;memcpy(&s,small_input,sizeof s);const pw_f64v result=1.0+s;
    uint64_t words[PW_LANES];memcpy(words,&result,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i)if(tiny&(1u<<i))output[i]=words[i];
  }
  if(nan) {
    pw_f64v s;memcpy(&s,nan_input,sizeof s);const pw_f64v result=1.0+s;
    uint64_t words[PW_LANES];memcpy(words,&result,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i)if(nan&(1u<<i))output[i]=words[i];
  }
  if(over || under) {
    volatile double overflow_factor=0x1p769,underflow_factor=0x1p-767;
    pw_f64v factors=(pw_f64v){0}+(1);
    for(unsigned i=0;i<PW_LANES;++i) {
      if(over&(1u<<i))factors[i]=overflow_factor;
      if(under&(1u<<i))factors[i]=underflow_factor;
    }
    const pw_f64v result=factors*factors;uint64_t words[PW_LANES];memcpy(words,&result,sizeof words);
    for(unsigned i=0;i<PW_LANES;++i)if((over|under)&(1u<<i))output[i]=words[i];
  }
  for(unsigned i=0;i<PW_LANES;++i) {
    if(posinf&(1u<<i))output[i]=UINT64_C(0x7ff0000000000000);
    if(neginf&(1u<<i))output[i]=0;
  }
}

/* Bit snapshots support exact input/output or merge/output aliasing only.
 * Every full64B input/merge buffer is readable, even when inactive. */
static int pw_apply_exp(const uint64_t input[PW_LANES],unsigned active,
    const uint64_t merge[PW_LANES],uint64_t output[PW_LANES],int unsafe) {
  if(active&~PW_ALL)return 1;
  uint64_t saved[PW_LANES],pass[PW_LANES],neutral[PW_LANES],value[PW_LANES];
  memcpy(saved,input,64);memcpy(pass,merge,64);
  if(!active && !unsafe){memcpy(output,pass,64);return 0;}
  /* Keep software predicates in the same64-bit lanes as the payload.
   * This is exact integer selection; no floating arithmetic or side effects. */
  const pw_u64v lane_bits={1ULL,2ULL,4ULL,8ULL,16ULL,32ULL,64ULL,128ULL};
  const pw_u64v requested=(pw_u64v){0}+(unsigned long long)active;
  const pw_u64v result_mask=(pw_u64v)((requested&lane_bits)!=0ULL);
  const pw_u64v evaluated=(pw_u64v){0}+(unsigned long long)(unsafe?PW_ALL:active);
  const pw_u64v evaluate_mask=(pw_u64v)((evaluated&lane_bits)!=0ULL);
  pw_u64v saved_bits,pass_bits;memcpy(&saved_bits,saved,sizeof saved_bits);memcpy(&pass_bits,pass,sizeof pass_bits);
  const pw_u64v neutral_bits=(saved_bits&evaluate_mask);
  memcpy(neutral,&neutral_bits,sizeof neutral_bits);
  pw_core_exp(neutral,value);
  pw_u64v computed;memcpy(&computed,value,sizeof computed);
  const pw_u64v selected=(computed&result_mask)|(pass_bits&~result_mask);
  memcpy(value,&selected,sizeof selected);
  memcpy(output,value,64);return 0;
}
int phi_host_exp_register_e8(const uint64_t input[PW_LANES],unsigned active,
    const uint64_t merge[PW_LANES],uint64_t output[PW_LANES]) {
  return pw_apply_exp(input,active,merge,output,0);
}
#ifdef PW_ENABLE_NEGATIVE_CONTROL
int phi_host_exp_register_e8_unsafe_negative(const uint64_t input[PW_LANES],unsigned active,
    const uint64_t merge[PW_LANES],uint64_t output[PW_LANES]) {
  return pw_apply_exp(input,active,merge,output,1);
}
#endif
