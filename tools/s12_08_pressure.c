/* S12-08: original, bounded diagnostics for storage versus register pressure.
   No reassociation, fast math, or replacement of benchmark initialization. */
#define _GNU_SOURCE
#include <stddef.h>

#ifndef DRIVER
#define JOIN_(a, b) a##b
#define JOIN(a, b) JOIN_(a, b)
#define FN(a) JOIN(a, SUFFIX)

/* Independent output elements; deliberately retain legal alias checks. */
void FN(independent)(unsigned n, const double *a, const double *b,
                     const unsigned *ix, double *out)
{
  (void)ix;
  for (unsigned i = 0; i < n; ++i)
    out[i] += a[i] * b[i];
}

/* Each output keeps its original t order. Sources have a column stride. */
void FN(dense_update)(unsigned n, const double *a, const double *b,
                      const unsigned *ix, double *out)
{
  (void)ix;
  for (unsigned t = 0; t < n; ++t)
    for (unsigned row = 0; row < n; ++row)
      for (unsigned col = 0; col < n; ++col)
        out[(size_t)row*n+col] += a[(size_t)row*n+t] * b[(size_t)col*n+t];
}

void FN(dense_recurrence)(unsigned n, const double *a, const double *b,
                          const unsigned *ix, double *out)
{
  (void)ix;
  for (unsigned row = 0; row < n; ++row)
    for (unsigned col = 0; col < n; ++col) {
      double sum = out[(size_t)row*n+col];
      for (unsigned k = 0; k < n; ++k)
        sum -= a[(size_t)row*n+k] * b[(size_t)k*n+col];
      out[(size_t)row*n+col] = sum;
    }
}

void FN(contiguous)(unsigned n, const double *a, const double *b,
                    const unsigned *ix, double *out)
{
  (void)ix;
  double sum = out[0];
  for (unsigned i = 0; i < n; ++i)
    sum -= a[i] * b[i];
  out[0] = sum;
}

void FN(indexed)(unsigned n, const double *a, const double *b,
                 const unsigned *ix, double *out)
{
  double sum = out[0];
  for (unsigned i = 0; i < n; ++i)
    sum += a[i] * b[ix[i]];
  out[0] = sum;
}

#else
#include <math.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

typedef void (*kernel)(unsigned, const double *, const double *,
                       const unsigned *, double *);
#define DECL(name) \
  extern void name##_base(unsigned, const double *, const double *, const unsigned *, double *); \
  extern void name##_scalar(unsigned, const double *, const double *, const unsigned *, double *)
DECL(independent);
DECL(dense_update);
DECL(dense_recurrence);
DECL(contiguous);
DECL(indexed);

static double now(void)
{
  struct timespec t;
  if (clock_gettime(CLOCK_MONOTONIC, &t)) exit(2);
  return (double)t.tv_sec + t.tv_nsec * 1e-9;
}

/* Powers of two keep every product and sum exact in these bounded cases.
   This is a live-out/order diagnostic, not exceptional-FP qualification. */
static void initialize(size_t size, double *a, double *b, unsigned *ix, double *out)
{
  for (size_t i = 0; i < size; ++i) {
    a[i] = (double)((int)(i % 13) - 6) / 16.0;
    b[i] = (double)((int)(i % 17) - 8) / 32.0;
    ix[i] = (unsigned)((i * 73 + 19) % size);
    out[i] = 1.0;
  }
}

static double sample(kernel fn, unsigned n, size_t size, unsigned repeats,
                     double *a, double *b, unsigned *ix, double *out,
                     const double *expected)
{
  double start = now();
  for (unsigned r = 0; r < repeats; ++r) {
    initialize(size, a, b, ix, out);
    fn(n, a, b, ix, out);
    if (memcmp(out, expected, size * sizeof(*out))) {
      fprintf(stderr, "FAIL live-out comparison\n");
      exit(1);
    }
  }
  return now() - start;
}

int main(void)
{
  const struct {
    const char *name;
    unsigned n;
    size_t size;
    kernel fn[2];
  } cases[] = {
    {"independent", 8192, 8192, {independent_base, independent_scalar}},
    {"dense-update", 128, 16384, {dense_update_base, dense_update_scalar}},
    {"dense-recurrence", 128, 16384, {dense_recurrence_base, dense_recurrence_scalar}},
    {"contiguous-recurrence", 8192, 8192, {contiguous_base, contiguous_scalar}},
    {"indexed-recurrence", 8192, 8192, {indexed_base, indexed_scalar}}
  };
  cpu_set_t cpus;
  CPU_ZERO(&cpus);
  if (sched_getaffinity(0, sizeof(cpus), &cpus) || CPU_COUNT(&cpus) != 1) {
    fprintf(stderr, "single-core timing diagnostic requires --threads 1\n");
    return 2;
  }
  alarm(50);
  setvbuf(stdout, NULL, _IOLBF, 0);
  double *a, *b, *out, *expected;
  unsigned *ix;
  if (posix_memalign((void **)&a, 64, 16384 * sizeof(*a)) ||
      posix_memalign((void **)&b, 64, 16384 * sizeof(*b)) ||
      posix_memalign((void **)&out, 64, 16384 * sizeof(*out)) ||
      posix_memalign((void **)&expected, 64, 16384 * sizeof(*expected)) ||
      posix_memalign((void **)&ix, 64, 16384 * sizeof(*ix))) return 2;
  printf("S12-08 cpu=%d pairs=AB,BA,AB baseline=-O2 scalar=-O2,no-tree-vectorize\n", sched_getcpu());
  for (unsigned c = 0; c < sizeof(cases)/sizeof(cases[0]); ++c) {
    unsigned n = cases[c].n;
    size_t size = cases[c].size;
    initialize(size, a, b, ix, expected);
    cases[c].fn[1](n, a, b, ix, expected);
    double elapsed = sample(cases[c].fn[0], n, size, 1, a, b, ix, out, expected);
    double target = 0.05 / (elapsed > 1e-6 ? elapsed : 1e-6);
    unsigned repeats = target > 256 ? 256 : target < 1 ? 1 : (unsigned)target;
    for (unsigned pair = 0; pair < 3; ++pair) {
      double seconds[2];
      for (unsigned turn = 0; turn < 2; ++turn) {
        unsigned variant = turn ^ (pair & 1);
        seconds[variant] = sample(cases[c].fn[variant], n, size, repeats,
                                  a, b, ix, out, expected);
      }
      printf("case=%s pair=%u repeats=%u base=%.9f scalar=%.9f check=PASS\n",
             cases[c].name, pair, repeats, seconds[0], seconds[1]);
    }
  }
  free(ix); free(expected); free(out); free(b); free(a);
  puts("PASS all live-outs; timings include initialization and checks");
  return 0;
}
#endif
