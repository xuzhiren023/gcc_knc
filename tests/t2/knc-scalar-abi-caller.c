#include <stdio.h>
#include "knc-scalar-abi.h"
static double __attribute__((noinline)) callback(double x) { return x * 2; }
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
  return 0;
}
