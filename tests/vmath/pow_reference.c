/* The pow oracle of both qualifiers (S10-06), linked with -Wl,--wrap=powl: the C99 Annex F
   (F.9.4.4) special cases from this table, and the libm powl only for x > 0 finite, y finite.
   The card's glibc powl returns a NaN for x < 0 with an integer |y| >= 2^63 (every such double
   or float is even), which failed 8,487,977 correct powf lanes and 15,745,251 pow lanes on the
   card (2026-11-11), so negative x goes through powl(-x,y) and the parity of y here. */
#include <math.h>

long double __real_powl(long double, long double);
long double __wrap_powl(long double, long double);

long double __wrap_powl(long double x, long double y) {
  if (y == 0 || x == 1) return 1;
  if (isnan(x) || isnan(y)) return x + y;
  int integer = isfinite(y) && floorl(y) == y, odd = integer && fmodl(y, 2) != 0;
  if (x == 0) {
    if (y < 0) return odd ? copysignl(INFINITY, x) : INFINITY;
    return odd ? x : 0;
  }
  if (isinf(y)) {
    long double a = fabsl(x);
    if (a == 1) return 1;
    return (a < 1) == (y < 0) ? INFINITY : 0;
  }
  if (isinf(x)) {
    long double r = y < 0 ? 0 : INFINITY;
    return x < 0 && odd ? -r : r;
  }
  if (x < 0) {
    if (!integer) return NAN;
    long double r = __real_powl(-x, y);
    return odd ? -r : r;
  }
  return __real_powl(x, y);
}
