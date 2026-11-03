/* S2-07: explicit runtime calls keep these probes from being constant folded.
   Print exact integer and IEEE binary64 results for a donor/card comparison. */
#include <stdio.h>

typedef __int128 I;
typedef unsigned __int128 U;
typedef float Q __attribute__((mode(TF)));
extern I __divti3(I, I), __modti3(I, I);
extern U __udivti3(U, U), __umodti3(U, U);
extern double __floattidf(I), __floatuntidf(U);
extern I __fixdfti(double);
extern U __fixunsdfti(double);
extern Q __extenddftf2(double), __addtf3(Q, Q), __multf3(Q, Q), __divtf3(Q, Q);
extern double __trunctfdf2(Q);

static void integer(U value)
{
  printf(" %016llx%016llx", (unsigned long long)(value >> 64),
         (unsigned long long)value);
}

static void floating(double value)
{
  union { double d; unsigned long long u; } bits;
  bits.d = value;
  printf(" %016llx", bits.u);
}

int main(void)
{
  volatile U dividends[] = {84, ((U)1 << 100) + 123456789,
                            ((U)1 << 126) - 1, (U)-1};
  volatile U divisors[] = {7, ((U)1 << 64) + 3, 65537, ((U)1 << 100) + 17};
  unsigned int n;
  for (n = 0; n < 4; ++n)
    {
      U a = dividends[n], b = divisors[n];
      I s = (I)(a >> 1), t = (I)b;
      if (n & 1) s = -s;
      if (n & 2) t = -t;
      printf("libgcc integer %u", n);
      integer((U)__divti3(s, t));
      integer((U)__modti3(s, t));
      integer(__udivti3(a, b));
      integer(__umodti3(a, b));
      floating(__floattidf(s));
      floating(__floatuntidf(a));
      putchar('\n');
    }
  {
    volatile double a = 0x1.23456789abcdep+100;
    volatile double b = -0x1.23456789abcdep+100;
    Q x = __extenddftf2(a), y = __extenddftf2(b);
    printf("libgcc softfp");
    integer((U)__fixdfti(b));
    integer(__fixunsdfti(a));
    floating(__trunctfdf2(x));
    floating(__trunctfdf2(__addtf3(x, y)));
    floating(__trunctfdf2(__multf3(x, __extenddftf2(2.0))));
    floating(__trunctfdf2(__divtf3(x, __extenddftf2(2.0))));
    floating(__trunctfdf2(__divtf3(__extenddftf2(1.0), __extenddftf2(3.0))));
    floating(__trunctfdf2(__divtf3(__extenddftf2(1.0), __extenddftf2(0.0))));
    floating(__trunctfdf2(__divtf3(__extenddftf2(0.0), __extenddftf2(0.0))));
    floating(__trunctfdf2(__multf3(__extenddftf2(0x1p1023), __extenddftf2(2.0))));
    floating(__trunctfdf2(__divtf3(__extenddftf2(0x1p-1022), __extenddftf2(3.0))));
    putchar('\n');
  }
  return 0;
}
