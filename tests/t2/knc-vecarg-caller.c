#include <stdio.h>
#include "knc-vecarg.h"

#define S8(b) { b, b + 1, b + 2, b + 3, b + 4, b + 5, b + 6, b + 7 }
#define S16(b) { b, b + 1, b + 2, b + 3, b + 4, b + 5, b + 6, b + 7, b + 8, \
  b + 9, b + 10, b + 11, b + 12, b + 13, b + 14, b + 15 }
static int failed;
#define CHECK(name, type, got, want) do { \
    type g = (got), w = (want); \
    for (unsigned k = 0; k < sizeof g / sizeof g[0]; ++k) \
      if (g[k] != w[k]) \
        { printf("S10-01 %s FAIL lane %u\n", name, k); failed = 1; break; } \
  } while (0)

int main(void)
{
  v16sf f1 = S16(1.f), f2 = S16(100.f), t[10], ten = { 0 };
  v8df d1 = S8(1.), d2 = S8(100.), mixed;
  v16si i1 = S16(1), i2 = S16(100);
  v8di q1 = S8((1LL << 40)), q2 = S8(100LL);

  CHECK("sf", v16sf, vecarg_sf(f1, f2), f1 - f2);
  CHECK("df", v8df, vecarg_df(d1, d2), d1 - d2);
  CHECK("si", v16si, vecarg_si(i1, i2), i1 - i2);
  CHECK("di", v8di, vecarg_di(q1, q2), q1 - q2);

  mixed = d1 - d2 * 2 + (7 * 1000 + 9 * 100 + 0.5f * 10 + 0.25);
  mixed[1] += i1[5];
  CHECK("mixed", v8df, vecarg_mixed(7, 0.5f, d1, 0.25, i1, 9, d2), mixed);

  for (int n = 0; n < 10; ++n)
    {
      t[n] = f1 * (float) (n + 1) + f2;
      ten += t[n] * (float) (n + 1);
    }
  CHECK("ten", v16sf, vecarg_ten(t[0], t[1], t[2], t[3], t[4], t[5], t[6],
                                  t[7], t[8], t[9]), ten);

  CHECK("stack", v8di,
        vecarg_stack(1, 0, 0, 0, 0, 0, 0, 2, 3, 0, 0, 0, 0, 0, 4, q1, 5, q2),
        q1 - q2 * 2 + 4326);
  puts(failed ? "S10-01 vector ABI FAIL" : "S10-01 vector ABI PASS");
  return failed;
}
