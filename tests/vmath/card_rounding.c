/* S10-11: card qualification's worst lanes, checked against MPFR at 256 bits.
   Keep this driver on SSE so only the library's scalar evaluation changes. */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <mpfr.h>
#include "knc_vmath.h"

int main(void)
{
  static const struct {
    const char *name;
    uint64_t x, y;
  } cases[] = {
    {"sin", UINT64_C(0x7f13000000000003), 0},
    {"cos", UINT64_C(0x7a31000000000004), 0},
    {"tan", UINT64_C(0x5f54000000000002), 0},
    /* qualify_v1's first argument is atan2's numerator. */
    {"atan2", UINT64_C(0x41cfb07cd81b8f16), UINT64_C(0xc1b536c582cd6336)}
  };
  mpfr_t a, b, exact, error;
  mpfr_inits2(256, a, b, exact, error, (mpfr_ptr)0);
  int failed = 0;
  for (unsigned c = 0; c < sizeof cases / sizeof cases[0]; ++c) {
    double x, y;
    memcpy(&x, &cases[c].x, 8);
    memcpy(&y, &cases[c].y, 8);
    __knc_vmath_v8df vx, vy, result;
    for (int lane = 0; lane < 8; ++lane) { vx[lane] = x; vy[lane] = y; }
    mpfr_set_d(a, x, MPFR_RNDN);
    mpfr_set_d(b, y, MPFR_RNDN);
    switch (c) {
      case 0: result = __knc_vmath_sin_8(vx); mpfr_sin(exact, a, MPFR_RNDN); break;
      case 1: result = __knc_vmath_cos_8(vx); mpfr_cos(exact, a, MPFR_RNDN); break;
      case 2: result = __knc_vmath_tan_8(vx); mpfr_tan(exact, a, MPFR_RNDN); break;
      default: result = __knc_vmath_atan2_8(vx, vy); mpfr_atan2(exact, a, b, MPFR_RNDN);
    }
    double ulp = ldexp(1.0, (int)mpfr_get_exp(exact) - 53);
    for (int lane = 0; lane < 8; ++lane) {
      mpfr_sub_d(error, exact, result[lane], MPFR_RNDN);
      mpfr_abs(error, error, MPFR_RNDN);
      double distance = mpfr_get_d(error, MPFR_RNDU) / ulp;
      if (!isfinite(result[lane]) || distance > 1.0) failed = 1;
      if (lane == 0) {
        uint64_t bits;
        memcpy(&bits, &result[lane], 8);
        printf("%s out=0x%016llx ulp=%.9f %s\n", cases[c].name,
               (unsigned long long)bits, distance, distance <= 1.0 ? "PASS" : "FAIL");
      }
    }
  }
  mpfr_clears(a, b, exact, error, (mpfr_ptr)0);
  return failed;
}
