/* S12-30: reduced legality gate for materializing vector products.
   S12-07's saved donor/knc gcc.s keeps fmull results in x87 until faddp.
   This test isolates the extra product rounding, without gather or timing.
   It deliberately does not change the floating-point control word. */
#include <stddef.h>

#ifndef DRIVER
#define CAT_(a,b) a##b
#define CAT(a,b) CAT_(a,b)
#define FN(n) CAT(PREFIX,n)

void FN(scalar)(int n, const int *col, const double *a,
                const double *x, double *out)
{
  double sum = 0;
  for (int j = 0; j < n; ++j)
    sum += a[j] * x[col[j]];
  *out = sum;
}

void FN(products)(int n, const int *col, const double *a,
                  const double *x, double *out)
{
  /* Model the double-precision product boundary in Route A. Volatile
     makes that boundary observable even when this probe is scalarized.
     The additions retain exactly the original source order. */
  volatile double products[32];
  for (int j = 0; j < n; ++j)
    products[j] = a[j] * x[col[j]];
  double sum = 0;
  for (int j = 0; j < n; ++j)
    sum += products[j];
  *out = sum;
}
#else
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <inttypes.h>

typedef void (*kernel)(int, const int *, const double *, const double *, double *);
#define DECL(p) \
  extern void p##scalar(int,const int*,const double*,const double*,double*); \
  extern void p##products(int,const int*,const double*,const double*,double*);
#ifdef HOST_MODEL
DECL(host_)
static kernel kernels[][2] = {{host_scalar, host_products}};
static const char *names[] = {"host-x87-model"};
#else
DECL(donor_)
DECL(knc_)
static kernel kernels[][2] = {{donor_scalar, donor_products},
                              {knc_scalar, knc_products}};
static const char *names[] = {"gcc-5.1.1", "gcc-knc"};
#endif

int main(void)
{
  int failures = 0;
  int col[32] = {0, 1};
  double a[32] = {-1.0, 0x1.0000002p0};
  double x[2] = {1.0, 0x1.ffffffcp-1};
  const int lengths[] = {2, 13, 27};
  /* Exact second product: (1+2^-27)(1-2^-27) = 1-2^-54.
     Rounding that product to double first yields 1, so cancellation
     yields zero instead of -2^-54 when extended products are retained.
     The remaining entries add zero; all indices remain in bounds. */
  for (size_t v = 0; v < sizeof kernels / sizeof kernels[0]; ++v)
    for (size_t k = 0; k < sizeof lengths / sizeof lengths[0]; ++k) {
      double scalar, products;
      uint64_t s, p;
      kernels[v][0](lengths[k], col, a, x, &scalar);
      kernels[v][1](lengths[k], col, a, x, &products);
      memcpy(&s, &scalar, sizeof s);
      memcpy(&p, &products, sizeof p);
      int equal = s == p;
      printf("%s %s row=%d scalar=%016" PRIx64 " products=%016" PRIx64 "\n",
             equal ? "PASS" : "FAIL", names[v], lengths[k], s, p);
      failures += !equal;
    }
  puts("This is a product-rounding legality gate, not a gather performance test.");
  return failures ? 1 : 0;
}
#endif
