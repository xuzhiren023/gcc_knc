/* GCC 16 additions: signatures from libgcc2.h, soft-fp and hardcfr.c/strub.c.
   Use explicit calls so the shared provider must supply every supported export. */
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
typedef float Q __attribute__((mode(TF)));
typedef __int128 I;
typedef unsigned long Limb;
extern I __divmodti4(I,I,I *);
extern void __mulbitint3(Limb *,int,const Limb *,int,const Limb *,int);
extern void __divmodbitint4(Limb *,int,Limb *,int,const Limb *,int,const Limb *,int);
extern void __fixsfbitint(Limb *,int,float), __fixdfbitint(Limb *,int,double);
extern void __fixtfbitint(Limb *,int,Q);
extern float __floatbitintsf(const Limb *,int);
extern double __floatbitintdf(const Limb *,int);
extern Q __floatbitinttf(const Limb *,int), __extenddftf2(double);
extern double __trunctfdf2(Q);
extern void __hardcfr_check(size_t,const unsigned *,const unsigned *);
extern void __strub_enter(void **), __strub_update(void **), __strub_leave(void **);
static void check(int ok,const char *s)
{ if(!ok) { fprintf(stderr,"FAIL %s\n",s); exit(1); } }
__attribute__((noinline)) static void deeper(void **mark)
{
  volatile char pad[1024]; pad[0]=7;
  __strub_update(mark);
  __asm__ volatile("" : : "m"(pad));
}
int main(void)
{
  I rem=0, q=__divmodti4(-85,7,&rem);
  Limb a[3]={84,0,0}, b[3]={7,0,0}, p[3]={0}, d[3]={0}, r[3]={0};
  Limb sf[3]={0}, df[3]={0}, tf[3]={0};
  check(q==-12 && rem==-1,"divmodti4");
  puts("PASS new divmodti4");
  __mulbitint3(p,192,a,192,b,192);
  __divmodbitint4(d,192,r,192,a,192,b,192);
  check(p[0]==588 && !p[1] && !p[2] && d[0]==12 && !d[1] && !d[2]
        && !r[0] && !r[1] && !r[2],"bitint arithmetic");
  __fixsfbitint(sf,192,84.75f); __fixdfbitint(df,192,84.75);
  __fixtfbitint(tf,192,__extenddftf2(84.75));
  check(sf[0]==84 && !sf[1] && !sf[2] && df[0]==84 && !df[1] && !df[2]
        && tf[0]==84 && !tf[1] && !tf[2],"bitint from float");
  check(__floatbitintsf(a,192)==84 && __floatbitintdf(a,192)==84
        && __trunctfdf2(__floatbitinttf(a,192))==84,"bitint to float");
  puts("PASS eight new bitint helpers");
  {
    /* One visited block, predecessor ENTRY and successor EXIT use its own bit. */
    unsigned visited[]={1}, cfg[]={1,0,0,1,0,0};
    __hardcfr_check(1,visited,cfg);
  }
  puts("PASS new hardcfr helper");
  {
    void *mark, *initial;
    __strub_enter(&mark); initial=mark;
    check(mark!=0,"strub enter"); deeper(&mark);
    check((unsigned long)mark<(unsigned long)initial,"strub update");
    __strub_leave(&mark);
  }
  puts("PASS three new strub helpers");
  return 0;
}
