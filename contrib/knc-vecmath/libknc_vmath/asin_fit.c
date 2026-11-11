/* Chebyshev interpolation of f(z) = (asin(sqrt z)/sqrt z - 1)/z on [0, 0.25], N nodes, in MPFR;
   prints the monomial coefficients rounded to double and their largest relative error. */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <mpfr.h>
#define PREC 400
static void f(mpfr_t r, mpfr_t z) {
  mpfr_t s; mpfr_init2(s, PREC);
  mpfr_sqrt(s, z, MPFR_RNDN); mpfr_asin(r, s, MPFR_RNDN); mpfr_div(r, r, s, MPFR_RNDN);
  mpfr_sub_ui(r, r, 1, MPFR_RNDN); mpfr_div(r, r, z, MPFR_RNDN); mpfr_clear(s);
}
int main(int argc, char **argv) {
  int n = atoi(argv[1]);
  mpfr_t x[32], d[32], c[32], t, u, pi;
  mpfr_inits2(PREC, t, u, pi, (mpfr_ptr)0); mpfr_const_pi(pi, MPFR_RNDN);
  for (int k = 0; k < n; ++k) {
    mpfr_inits2(PREC, x[k], d[k], c[k], (mpfr_ptr)0);
    mpfr_mul_ui(t, pi, 2*k + 1, MPFR_RNDN); mpfr_div_ui(t, t, 2*n, MPFR_RNDN); mpfr_cos(t, t, MPFR_RNDN);
    mpfr_add_ui(t, t, 1, MPFR_RNDN); mpfr_div_ui(x[k], t, 8, MPFR_RNDN);
    f(d[k], x[k]);
  }
  for (int j = 1; j < n; ++j) for (int k = n - 1; k >= j; --k) {
    mpfr_sub(d[k], d[k], d[k-1], MPFR_RNDN); mpfr_sub(t, x[k], x[k-j], MPFR_RNDN); mpfr_div(d[k], d[k], t, MPFR_RNDN); }
  /* Newton form to monomials: p = d[n-1]; p = p (z - x[k]) + d[k]. */
  for (int k = 0; k < n; ++k) mpfr_set_ui(c[k], 0, MPFR_RNDN);
  mpfr_set(c[0], d[n-1], MPFR_RNDN);
  for (int k = n - 2; k >= 0; --k) {
    for (int i = n - 1; i >= 1; --i) { mpfr_mul(t, c[i], x[k], MPFR_RNDN); mpfr_sub(c[i], c[i-1], t, MPFR_RNDN); }
    mpfr_mul(t, c[0], x[k], MPFR_RNDN); mpfr_sub(c[0], d[k], t, MPFR_RNDN);
  }
  double cd[32], worst = 0;
  for (int k = 0; k < n; ++k) cd[k] = mpfr_get_d(c[k], MPFR_RNDN);
  for (int i = 1; i <= 4000; ++i) {
    mpfr_set_ui(t, i, MPFR_RNDN); mpfr_div_ui(t, t, 16000, MPFR_RNDN);
    mpfr_set_d(u, cd[n-1], MPFR_RNDN);
    for (int k = n - 2; k >= 0; --k) { mpfr_mul(u, u, t, MPFR_RNDN); mpfr_add_d(u, u, cd[k], MPFR_RNDN); }
    f(pi, t); mpfr_sub(u, u, pi, MPFR_RNDN); mpfr_div(u, u, pi, MPFR_RNDN);
    double e = fabs(mpfr_get_d(u, MPFR_RNDN)); if (e > worst) worst = e;
  }
  printf("n=%d worst relative error 2^%.2f\n", n, log2(worst));
  for (int k = 0; k < n; ++k) printf("%a,%s", cd[k], k % 4 == 3 ? "\n" : " ");
  printf("\n");
  return 0;
}
