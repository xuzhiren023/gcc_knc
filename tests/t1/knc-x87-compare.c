/* S2-05: pointer arguments isolate x87 comparison selection from the scalar
   transfer ABI.  Every function is SysV so the same emitted instructions can
   be exercised by the Cygwin host driver as a T1 check, never a card result.
   For eventual tools/card_run validation, compile this file with COMPARE_MAIN.
   COMPARE_DRIVER builds only the table driver, to link emitted assembly. */
#define FORMS(M, T, S) \
  M(T,S,eq, a == b,1) M(T,S,ne, a != b,1) \
  M(T,S,lt, a < b,0) M(T,S,le, a <= b,0) \
  M(T,S,gt, a > b,0) M(T,S,ge, a >= b,0) \
  M(T,S,isless,__builtin_isless(a,b),1) \
  M(T,S,islessequal,__builtin_islessequal(a,b),1) \
  M(T,S,isgreater,__builtin_isgreater(a,b),1) \
  M(T,S,isgreaterequal,__builtin_isgreaterequal(a,b),1) \
  M(T,S,islessgreater,__builtin_islessgreater(a,b),1) \
  M(T,S,isunordered,__builtin_isunordered(a,b),1) \
  M(T,S,isordered,!__builtin_isunordered(a,b),1) \
  M(T,S,unlt,!(a >= b),0) M(T,S,unle,!(a > b),0) \
  M(T,S,ungt,!(a <= b),0) M(T,S,unge,!(a < b),0)

#ifdef COMPARE_DRIVER
#define DEFINE(T,S,N,E,Q) \
  extern int __attribute__((sysv_abi)) cmp_##S##_##N(const T *, const T *);
#else
#define DEFINE(T,S,N,E,Q) \
  int __attribute__((noinline,noclone,sysv_abi)) \
  cmp_##S##_##N(const T *left, const T *right) \
  { T a = *left, b = *right; return E; }
#endif
FORMS(DEFINE,float,sf)
FORMS(DEFINE,double,df)
FORMS(DEFINE,long double,xf)

#if defined(COMPARE_MAIN) || defined(COMPARE_DRIVER)
#include <stdio.h>

/* Expected values come from integer ranks, independently of FP comparisons.
   The two zeros have the same rank. Index zero is a quiet NaN. */
static const int ranks[] = {0,0,0,-2,2,-1,1};
static int expected(unsigned form, unsigned i, unsigned j)
{
  int u = i == 0 || j == 0, l = ranks[i] < ranks[j];
  int e = ranks[i] == ranks[j], g = ranks[i] > ranks[j];
  const int values[] = {!u && e, u || !e, !u && l, !u && (l || e),
    !u && g, !u && (g || e), !u && l, !u && (l || e), !u && g,
    !u && (g || e), !u && !e, u, !u, u || l, u || l || e,
    u || g, u || g || e};
  return values[form];
}
#define ENTRY(T,S,N,E,Q) {cmp_##S##_##N, #N, Q},
#define TABLE(T,S,NAN,INF) \
static int table_##S(void) \
{ \
  typedef int (__attribute__((sysv_abi)) *compare)(const T *, const T *); \
  static const struct { compare fn; const char *name; int quiet; } ops[] = \
    { FORMS(ENTRY,T,S) }; \
  const T values[] = {NAN, -0.0L, +0.0L, -INF, INF, -3.0L, 2.0L}; \
  unsigned n,i,j,failures=0; \
  for(n=0;n<sizeof ops/sizeof ops[0];++n) \
    for(i=0;i<7;++i) for(j=0;j<7;++j) \
      { \
        unsigned short status; \
        int got, invalid_expected = !ops[n].quiet && (i==0 || j==0); \
        __asm__ volatile("fnclex" ::: "memory"); \
        got=ops[n].fn(&values[i],&values[j]); \
        __asm__ volatile("fnstsw %0" : "=a"(status) :: "memory"); \
        if(got!=expected(n,i,j) || (status&1)!=invalid_expected) \
          { \
            printf("FAIL " #S " %s %u %u got=%d expected=%d invalid=%u expected_invalid=%d\n", \
              ops[n].name,i,j,got,expected(n,i,j),status&1,invalid_expected); \
            ++failures; \
          } \
      } \
  printf("TABLE " #S " checks=%u failures=%u\n", \
         (unsigned)(sizeof ops/sizeof ops[0])*49,failures); \
  return failures!=0; \
}
TABLE(float,sf,__builtin_nanf(""),__builtin_inff())
TABLE(double,df,__builtin_nan(""),__builtin_inf())
TABLE(long double,xf,__builtin_nanl(""),__builtin_infl())
int main(void)
{
  int sf=table_sf(),df=table_df(),xf=table_xf();
  return sf || df || xf;
}
#endif
