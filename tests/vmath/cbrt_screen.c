/* S10-12: exercise the actual qualifier screen against MPFR while modeling
   the MPSS cbrtl negative-remainder table-address fault on the host. */
#define _GNU_SOURCE
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

static long double checked_cbrtl(long double x) {
  int exponent;
  frexpl(fabsl(x), &exponent);
  if (isfinite(x) && x != 0 && exponent % 3 < 0) {
    fprintf(stderr, "FAIL: MPSS cbrtl negative table offset for %La (exponent %d)\n",
            x, exponent);
    exit(1);
  }
  return cbrtl(x);
}

#define cbrtl checked_cbrtl
#define main qualifier_main
#include "qualify_v1.c"
#undef main
#undef cbrtl

int main(void) {
  mpfr_t reference;
  mpfr_init2(reference, 256);
  unsigned checked = 0;
  for (unsigned i = 0; i < sizeof functions / sizeof *functions; ++i) {
    if (functions[i].id != CBRT) continue;
    f = &functions[i];
    for (int e = f->single ? -149 : -1074; e <= (f->single ? 127 : 1023); ++e)
      for (int sign = -1; sign <= 1; sign += 2) {
        /* Include the first crashing special-grid input, then all exponent
           residues, subnormals, and both signs across the input format. */
        double a = checked == 0 ? 1e-5 : sign * ldexp(1.5, e);
        if (f->single) a = (float)a;
        mpfr_set_d(reference, a, MPFR_RNDN);
        mpfr_cbrt(reference, reference, MPFR_RNDN);
        double out = f->single ? (double)mpfr_get_flt(reference, MPFR_RNDN)
                              : mpfr_get_d(reference, MPFR_RNDN);
        struct special special = annex_f(a, 0);
        long double screened = screen_error(a, 0, out, special);
        long double exact_ulp = exact_error(a, 0, out, special);
        if (!isfinite(screened) || screened < 0 || fabsl(screened - exact_ulp) > 0.01L) {
          fprintf(stderr, "FAIL: %s x=%a screen=%Lf exact=%Lf\n",
                  f->name, a, screened, exact_ulp);
          return 1;
        }
        ++checked;
      }
  }
  mpfr_clear(reference);
  printf("PASS: %u cbrt/cbrtf screen cases; MPFR error difference <= 0.01 ULP\n", checked);
  return 0;
}
