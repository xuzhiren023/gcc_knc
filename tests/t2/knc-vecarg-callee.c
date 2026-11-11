#include "knc-vecarg.h"

/* Subtraction and distinct weights expose swapped or lost arguments. */
v16sf vecarg_sf(v16sf a, v16sf b) { return a - b; }
v8df vecarg_df(v8df a, v8df b) { return a - b; }
v16si vecarg_si(v16si a, v16si b) { return a - b; }
v8di vecarg_di(v8di a, v8di b) { return a - b; }

v8df vecarg_mixed(int i, float f, v8df a, double d, v16si b, long j, v8df c)
{
  v8df r = a - c * 2 + (i * 1000 + j * 100 + f * 10 + d);
  r[1] += b[5];
  return r;
}

v16sf vecarg_ten(v16sf a0, v16sf a1, v16sf a2, v16sf a3, v16sf a4, v16sf a5,
                 v16sf a6, v16sf a7, v16sf a8, v16sf a9)
{
  return a0 + a1 * 2 + a2 * 3 + a3 * 4 + a4 * 5 + a5 * 6 + a6 * 7 + a7 * 8
         + a8 * 9 + a9 * 10;
}

v8di vecarg_stack(double d0, double d1, double d2, double d3, double d4,
                  double d5, double d6, double d7, long g0, long g1, long g2,
                  long g3, long g4, long g5, long g6, v8di v, char c, v8di w)
{
  return v - w * 2 + (long long) (d0 + d7 * 10 + g0 * 100 + g6 * 1000 + c);
}
