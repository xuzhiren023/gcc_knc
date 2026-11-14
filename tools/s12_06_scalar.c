/* Original phase-one diagnostics. The integer recurrence is modulo 2^46,
   split at bit 23 to expose the four FP/int/FP round trips in scalar code.
   No vendor implementation or benchmark code is incorporated. */
#define _GNU_SOURCE
#include <math.h>
#include <stdint.h>

#if defined(CALLEE)
double memory_boundary(double x)
{
  /* Force an x87 computation and both memory bridges in an opaque callee.
     Adding zero is exact for our finite negative log inputs only. */
  volatile double zero = 0.0;
  return x + zero;
}
#elif !defined(DRIVER)
double recurrence_step(double *state, const double *multiplier)
{
  double ah = (int)(*multiplier * 0x1p-23);
  double al = *multiplier - ah * 0x1p23;
  double sh = (int)(*state * 0x1p-23);
  double sl = *state - sh * 0x1p23;
  double cross = ah * sl + al * sh;
  double carry = (int)(cross * 0x1p-23);
  double low = cross - carry * 0x1p23;
  double product = low * 0x1p23 + al * sl;
  double quotient = (int)(product * 0x1p-46);
  *state = product - quotient * 0x1p46;
  return *state * 0x1p-46;
}

void recurrence(int n, const double *p, const double *q,
                const double *logs, double *out)
{
  double state = 314159265.0, multiplier = 1220703125.0, sum = 0;
  (void)p; (void)q; (void)logs;
  for (int i = 0; i < n; ++i) sum += recurrence_step(&state, &multiplier);
  out[0] = state; out[1] = sum;
}

void conversion(int n, const double *p, const double *q,
                const double *logs, double *out)
{
  double sum = 0;
  (void)q; (void)logs;
  for (int i = 0; i < n; ++i)
    sum += (double)(int)(p[i] * 1024.0 + sum * 0x1p-20);
  out[0] = sum;
}

void scalar_control(int n, const double *p, const double *q,
                    const double *logs, double *out)
{
  double sum = 0;
  (void)q; (void)logs;
  for (int i = 0; i < n; ++i) sum = sum * 0.5 + p[i];
  out[0] = sum;
}

#else
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

enum { N = 2048, CASES = 8, REPEATS = 3, MAX_ROUNDS = 1024 };
typedef void (*kernel)(int, const double *, const double *, const double *, double *);
static const char *names[CASES] = {
  "transform_log", "transform_table", "transform_identity", "transform_memory",
  "recurrence", "conversion", "scalar_control", "vector_control"
};
static kernel functions[2][CASES];
static pthread_barrier_t barrier;
struct worker {
  int cpu, failed, rounds[CASES];
  double seconds[CASES][REPEATS][2];
};

static double now(void)
{
  struct timespec t;
  if (clock_gettime(CLOCK_MONOTONIC, &t)) abort();
  return t.tv_sec + 1.e-9 * t.tv_nsec;
}
static double *array(void)
{
  void *p = NULL;
  if (posix_memalign(&p, 64, N * sizeof(double))) abort();
  memset(p, 0, N * sizeof(double));
  return p;
}
static int equal(const double *a, const double *b, int count, double tolerance)
{
  for (int i = 0; i < count; ++i)
    if (!isfinite(a[i]) || !isfinite(b[i]) ||
        fabs(a[i] - b[i]) > tolerance * (1 + fabs(b[i]))) return 0;
  return 1;
}
static double measure(kernel f, int rounds, double *p, double *q,
                      double *logs, double *out)
{
  double start = now();
  for (int r = 0; r < rounds; ++r) f(N, p, q, logs, out);
  return now() - start;
}
static void *work(void *arg)
{
  struct worker *w = arg;
  cpu_set_t one;
  CPU_ZERO(&one); CPU_SET(w->cpu, &one);
  if (pthread_setaffinity_np(pthread_self(), sizeof one, &one)) abort();
  double *p = array(), *q = array(), *logs = array(), *out = array();
  double *reference = array(), *other = array();
  uint32_t state = 12345;
  for (int i = 0; i < N; ++i) {
    state = state * 1664525u + 1013904223u;
    p[i] = ((state >> 16) + 0.5) * 0x1p-16;
    state = state * 1664525u + 1013904223u;
    q[i] = ((state >> 16) + 0.5) * 0x1p-16;
    double u = 2*p[i]-1, v = 2*q[i]-1, radius = u*u+v*v;
    logs[i] = log(radius);
  }
  functions[0][0](N, p, q, logs, reference);
  for (int c = 0; c < CASES; ++c) {
    int count = c < 4 ? 18 : c == 4 ? 2 : c == 7 ? N : 1;
    functions[0][c](N, p, q, logs, out);
    functions[1][c](N, p, q, logs, other);
    if (!equal(out, other, count, 1.e-12)) w->failed = 1;
    if (c < 4 && (!equal(out, reference, 2, 1.e-12) ||
                  !equal(out+2, reference+2, 16, 0))) w->failed = 1;
    if (c == 4) {
      uint64_t seed = 314159265;
      double sum = 0;
      for (int i = 0; i < N; ++i) {
        seed = (seed * UINT64_C(1220703125)) & ((UINT64_C(1)<<46)-1);
        sum += seed * 0x1p-46;
      }
      if (out[0] != (double)seed || fabs(out[1]-sum) > 1.e-10) w->failed = 1;
    }
    if (c == 5) {
      uint64_t sum = 0;
      /* p is an odd integer / 2^17. Evaluate the feedback and truncation
         entirely as integers, independently of the tested FP conversion. */
      for (int i = 0; i < N; ++i)
        sum += (((uint64_t)(p[i]*0x1p17) << 13) + sum) >> 20;
      if (out[0] != (double)sum) w->failed = 1;
    }
    if (c == 7)
      for (int i = 0; i < N; ++i) if (out[i] != p[i]+q[i]) w->failed = 1;
    /* Same fixed work for both compilers; calibrate only before paired timing.
       All granted CPUs enter every timed cell together. */
    int rounds = 1;
    while (rounds < MAX_ROUNDS) {
      if (measure(functions[1][c], rounds, p, q, logs, out) >= 0.1) break;
      rounds *= 2;
    }
    w->rounds[c] = rounds;
    for (int r = 0; r < REPEATS; ++r) {
      for (int order = 0; order < 2; ++order) {
        int compiler = (r + order) % 2;
        pthread_barrier_wait(&barrier);
        w->seconds[c][r][compiler] = measure(functions[compiler][c], rounds,
                                            p, q, logs, out);
      }
    }
  }
  free(p); free(q); free(logs); free(out); free(reference); free(other);
  return NULL;
}

int main(void)
{
  cpu_set_t granted;
  pthread_t threads[CPU_SETSIZE];
  struct worker *workers = calloc(CPU_SETSIZE, sizeof *workers);
  const char *libs[] = {"./scalar-donor.so", "./scalar-knc.so"};
  alarm(1500);
  if (!workers || sched_getaffinity(0, sizeof granted, &granted)) return 2;
  int total = CPU_COUNT(&granted), used = 0, failed = 0;
  if (!total || pthread_barrier_init(&barrier, NULL, total)) return 2;
  for (int cc = 0; cc < 2; ++cc) {
    void *lib = dlopen(libs[cc], RTLD_NOW | RTLD_LOCAL);
    if (!lib) { fprintf(stderr, "%s\n", dlerror()); return 2; }
    for (int c = 0; c < CASES; ++c) {
      *(void **)(&functions[cc][c]) = dlsym(lib, names[c]);
      if (!functions[cc][c]) return 2;
    }
  }
  printf("S12_06_BEGIN workers=%d samples=%d repeats=%d\n", total, N, REPEATS);
  fflush(stdout);
  for (int cpu = 0; cpu < CPU_SETSIZE; ++cpu) if (CPU_ISSET(cpu, &granted)) {
    workers[used].cpu = cpu;
    if (pthread_create(&threads[used], NULL, work, &workers[used])) return 2;
    ++used;
  }
  for (int i = 0; i < total; ++i) {
    pthread_join(threads[i], NULL);
    failed |= workers[i].failed;
    for (int c = 0; c < CASES; ++c)
      for (int r = 0; r < REPEATS; ++r)
        printf("S12_06_PAIR cpu=%d case=%s pair=%d rounds=%d donor=%.9g knc=%.9g\n",
               workers[i].cpu, names[c], r, workers[i].rounds[c],
               workers[i].seconds[c][r][0], workers[i].seconds[c][r][1]);
  }
  printf("S12_06_CHECK %s\n", failed ? "FAIL" : "PASS");
  free(workers);
  return failed;
}
#endif
