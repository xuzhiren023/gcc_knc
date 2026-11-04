#include <stdio.h>
#include <fenv.h>
#include "knc-scalar-abi.h"
static double __attribute__((noinline)) callback(double x) { return x * 2; }

static int complex_values(void)
{
  _Complex float f = scalar_cf(__builtin_complex(1.25f, -3.5f));
  _Complex double d = scalar_cd(__builtin_complex(-2.5, 4.25));
  _Complex long double l = scalar_cld(
    __builtin_complex(1.25L + 0x1p-60L, -3.5L - 0x1p-60L));
  if (__real__ f != 1.75f || __imag__ f != -3.75f
      || __real__ d != -2.25 || __imag__ d != 3.75
      || __real__ l != 1.75L + 0x1p-60L
      || __imag__ l != -3.75L - 0x1p-60L)
    { puts("S3-15 complex ABI FAIL"); return 1; }
  printf("S3-15 complex ABI PASS: float=(%g,%g) double=(%g,%g) long-double=(%La,%La)\n",
         (double) __real__ f, (double) __imag__ f, __real__ d, __imag__ d,
         __real__ l, __imag__ l);
  return 0;
}

static int rounding_values(void)
{
  const int modes[] = { FE_TONEAREST, FE_DOWNWARD, FE_UPWARD, FE_TOWARDZERO };
  const char *names[] = { "nearest", "downward", "upward", "towardzero" };
  const double positive[] = { 1., 1., 0x1.0000000000001p0, 1. };
  const double negative[] = { -1., -0x1.0000000000001p0, -1., -1. };
  int original = fegetround(), failed = 0;
  unsigned int i;
  for (i = 0; i < 4; ++i)
    {
      double p, n;
      unsigned short before_cw, after_cw;
      unsigned int before_mxcsr, after_mxcsr;
      int mode;
      if (fesetround(modes[i])) { failed = 1; break; }
      __asm__ volatile ("fnstcw %0" : "=m" (before_cw));
      __asm__ volatile ("stmxcsr %0" : "=m" (before_mxcsr));
      mode = scalar_round(1., 0x1p-53, &p, &n);
      __asm__ volatile ("fnstcw %0" : "=m" (after_cw));
      __asm__ volatile ("stmxcsr %0" : "=m" (after_mxcsr));
      if (mode != modes[i] || fegetround() != modes[i]
          || p != positive[i] || n != negative[i]
          || ((before_cw >> 10) & 3) != i
          || ((before_mxcsr >> 13) & 3) != i
          || ((after_cw ^ before_cw) & 0xc00)
          || ((after_mxcsr ^ before_mxcsr) & 0x6000))
        { printf("S3-15 rounding %s FAIL: mode=%x p=%a n=%a\n", names[i], mode, p, n); failed = 1; }
      else
        printf("S3-15 rounding %s PASS: p=%a n=%a\n", names[i], p, n);
    }
  if (fesetround(original)) failed = 1;
  return failed;
}
int main(void)
{
  struct df d = { 2.5, 1.25f }, dr = scalar_df(d);
  struct ff f = { 1.25f, 3.5f }, fr = scalar_ff(f);
  if (scalar_f(1.25f) != 1.75f || scalar_d(2.5) != 2.75
      || scalar_mixed(1,2,3,4,5,6) != 321
      || scalar_ten_f(1,2,3,4,5,6,7,8,9,10) != 385
      || scalar_ten_d(1,2,3,4,5,6,7,8,9,10) != 385
      || dr.d != 2.75 || dr.f != 1.75f || fr.a != 1.5f || fr.b != 4.0f
      || scalar_callback(callback, 3.25) != 7.0)
    { puts("S2-02 scalar ABI FAIL"); return 1; }
  puts("S2-02 scalar ABI PASS");
  return complex_values() | rounding_values();
}
