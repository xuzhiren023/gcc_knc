/* S7-05: explicit calls preserve the donor SF/TF register ABI.
   Alias versions are from knc-libgcc-donor.exports; soft-fp uses IEEE binary128. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <fenv.h>
#include <stdint.h>

typedef float Q __attribute__((mode(TF)));
typedef _Complex float CQ __attribute__((mode(TC)));
typedef union { Q q; uint64_t w[2]; } Bits;
extern float __addsf3(float,float), __subsf3(float,float), __mulsf3(float,float);
extern float __divsf3(float,float), __negsf2(float), __floatsisf(int);
extern float __floatunsisf(unsigned);
extern int __fixsfsi(float), __eqsf2(float,float), __nesf2(float,float);
extern int __gesf2(float,float), __gtsf2(float,float), __lesf2(float,float);
extern int __ltsf2(float,float), __unordsf2(float,float);
extern Q __extenddftf2(double), __extendsftf2(float), __addtf3(Q,Q);
extern Q __subtf3(Q,Q), __multf3(Q,Q), __divtf3(Q,Q), __negtf2(Q);
extern double __trunctfdf2(Q);
extern float __trunctfsf2(Q);
extern int __fixtfsi(Q), __eqtf2(Q,Q), __unordtf2(Q,Q);
extern Q old_powi(Q,int);
extern CQ old_mul(Q,Q,Q,Q), old_div(Q,Q,Q,Q);
extern int old_gt(Q,Q), old_lt(Q,Q), old_ne(Q,Q);
__asm__(".symver old_powi,__powitf2@GCC_4.0.0");
__asm__(".symver old_mul,__multc3@GCC_4.0.0");
__asm__(".symver old_div,__divtc3@GCC_4.0.0");
__asm__(".symver old_gt,__gttf2@GCC_3.0");
__asm__(".symver old_lt,__lttf2@GCC_3.0");
__asm__(".symver old_ne,__netf2@GCC_3.0");

static void check(int ok, const char *what)
{
  if (!ok) { fprintf(stderr,"FAIL %s\n",what); exit(1); }
}
static Q bits(uint64_t hi, uint64_t lo)
{ Bits x; x.w[0]=lo; x.w[1]=hi; return x.q; }
static int same(Q x, uint64_t hi, uint64_t lo)
{ Bits a; a.q=x; return a.w[0]==lo && a.w[1]==hi; }

int main(void)
{
  Q one=bits(0x3fff000000000000ULL,0), two=bits(0x4000000000000000ULL,0);
  Q zero=bits(0,0), half_ulp=bits(0x3f8e000000000000ULL,0);
  float nan; uint32_t n=0x7fc00000U; memcpy(&nan,&n,4);
  check(__addsf3(2,3)==5 && __subsf3(7,3)==4 && __mulsf3(2,3)==6
        && __divsf3(6,2)==3 && __negsf2(2)==-2, "SF arithmetic");
  check(__floatsisf(-17)==-17 && __floatunsisf(17)==17
        && __fixsfsi(-17.75f)==-17, "SF conversion");
  check(__eqsf2(2,2)==0 && __nesf2(2,3)!=0 && __gesf2(3,2)>=0
        && __gtsf2(3,2)>0 && __lesf2(2,3)<=0 && __ltsf2(2,3)<0
        && __unordsf2(nan,2)!=0, "SF comparison");
  puts("PASS SF interfaces");
  check(__trunctfdf2(__addtf3(one,two))==3
        && __trunctfdf2(__subtf3(two,one))==1
        && __trunctfdf2(__multf3(two,two))==4
        && __trunctfsf2(__divtf3(two,two))==1
        && __fixtfsi(__negtf2(two))==-2
        && __eqtf2(__extenddftf2(2),__extendsftf2(2))==0, "TF interfaces");
  puts("PASS TF interfaces");
  {
    CQ m=old_mul(one,two,two,one), d=old_div(one,two,one,zero);
    check(old_gt(two,one)>0 && old_lt(one,two)<0 && old_ne(one,two)!=0
          && __trunctfdf2(old_powi(two,3))==8
          && __trunctfdf2(__real__ m)==0 && __trunctfdf2(__imag__ m)==5
          && __trunctfdf2(__real__ d)==1 && __trunctfdf2(__imag__ d)==2,
          "six compatibility aliases");
  }
  puts("PASS six version aliases");
  {
    struct cpu { unsigned vendor,type,subtype,features; } before, *model;
    int (*init)(void);
    void *h=dlopen("libgcc_s.so.1",RTLD_NOW);
    check(h!=0,"dlopen libgcc");
    model=(struct cpu *)dlvsym(h,"__cpu_model","GCC_4.8.0");
    init=(int (*)(void))dlvsym(h,"__cpu_indicator_init","GCC_4.8.0");
    check(model && init && sizeof(*model)==16,"CPU ABI");
    before=*model;
    check(before.vendor!=0,"CPU constructor before main");
    check(init()==0 && !memcmp(&before,model,16),"CPU initializer idempotence");
    dlclose(h);
  }
  puts("PASS CPU object and initializer");
  {
    int modes[]={FE_TONEAREST,FE_DOWNWARD,FE_UPWARD,FE_TOWARDZERO};
    unsigned i;
    for(i=0;i<4;i++) {
      Q r;
      check(fesetround(modes[i])==0 && feclearexcept(FE_ALL_EXCEPT)==0,"fenv setup");
      r=__addtf3(one,half_ulp);
      check(same(r,0x3fff000000000000ULL,i==2?1:0),"binary128 rounding");
      check(fetestexcept(FE_ALL_EXCEPT)==FE_INEXACT,"rounding inexact");
    }
    check(fesetround(FE_TONEAREST)==0,"restore rounding");
  }
  puts("PASS binary128 four rounding modes");
  {
    Q r;
    feclearexcept(FE_ALL_EXCEPT); r=__divtf3(zero,zero);
    check(__unordtf2(r,r)!=0 && (fetestexcept(FE_INVALID)!=0),"invalid");
    feclearexcept(FE_ALL_EXCEPT); r=__divtf3(one,zero);
    check(same(r,0x7fff000000000000ULL,0) && fetestexcept(FE_ALL_EXCEPT)==FE_DIVBYZERO,"divide by zero");
    feclearexcept(FE_ALL_EXCEPT);
    r=__multf3(bits(0x7ffeffffffffffffULL,~(uint64_t)0),two);
    check(same(r,0x7fff000000000000ULL,0)
          && fetestexcept(FE_ALL_EXCEPT)==(FE_OVERFLOW|FE_INEXACT),"overflow");
    feclearexcept(FE_ALL_EXCEPT); r=__divtf3(bits(0,1),two);
    check(same(r,0,0) && fetestexcept(FE_ALL_EXCEPT)==(FE_UNDERFLOW|FE_INEXACT),"underflow");
  }
  puts("PASS binary128 exceptions");
  return 0;
}
