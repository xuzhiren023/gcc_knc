/* S12-30 phase-one harness. Compile DRIVER and kernels as separate TUs.
   No LTO: all matrix data is generated at run time in the driver.
   nnz bounds the accessible col/val arrays, independently of the row slice. */
#define _GNU_SOURCE
#include <stddef.h>
#define ARGS int rows, const int *row, const int *col, const double *val, \
  const double *x, double *out, int nnz
typedef void (*kernel)(ARGS);

#ifndef DRIVER
#define CAT_(a,b) a##b
#define CAT(a,b) CAT_(a,b)
#define FN(n) CAT(PREFIX,n)
void FN(scalar)(ARGS)
{
  (void)nnz;
  for (int i = 0; i < rows; ++i) {
    double sum = 0;
    for (int j = row[i]; j < row[i+1]; ++j)
      sum += val[j] * x[col[j]];
    out[i] = sum;
  }
}
/* RED: absent routes are failures, not scalar fallbacks. */
kernel const FN(routes)[4] = {FN(scalar), NULL, NULL, NULL};

#ifdef SEED_TREES
/* Deliberate order mutations, never timed. Volatile stores impose the
   named intermediate precision. Products in the order cases are exact. */
#define TREE(NAME, TYPE) \
void NAME(ARGS) { \
  (void)nnz; \
  for (int r = 0; r < rows; ++r) { \
    volatile TYPE p[64] = {0}; \
    for (int j = row[r]; j < row[r+1]; ++j) \
      p[j-row[r]] = val[j] * x[col[j]]; \
    for (int step = 1; step < 64; step *= 2) \
      for (int j = 0; j < 64; j += 2*step) p[j] = p[j] + p[j+step]; \
    out[r] = p[0]; \
  } \
}
TREE(seed_tree53, double)
TREE(seed_tree64, long double)
#endif

#else
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include <string.h>
#include <math.h>
#include <float.h>
#include <time.h>
#include <unistd.h>
#include <sched.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <sys/resource.h>

extern kernel const donor_routes[4], knc_routes[4], fast_routes[4];
extern void seed_tree53(ARGS), seed_tree64(ARGS);
static const char *compilers[] = {"donor-off", "knc-off", "knc-contract-fast"};
static const char *routes[] = {"scalar", "A", "B", "A+B"};
static kernel const *tables[] = {donor_routes, knc_routes, fast_routes};
static int failures, details;
static unsigned long checks;
static uint32_t rng;

static void die(const char *s) { perror(s); exit(2); }
static uint32_t random32(void) { rng = rng * 1664525u + 1013904223u; return rng; }
static uint64_t bits(double x) { uint64_t u; memcpy(&u, &x, 8); return u; }
static double reference(int n, const int *c, const double *v, const double *x)
{
  long double s = 0;
  for (int j = 0; j < n; ++j) s += (long double)v[j] * (long double)x[c[j]];
  return (double)s;
}
static void compare(const char *what, int compiler, int route, int n,
                    double got, double want, int inexact)
{
  ++checks;
  uint64_t a = bits(got), b = bits(want);
  /* Inexact fixtures are positive finite numbers; bit distance is ULPs. */
  uint64_t distance = a > b ? a-b : b-a;
  if ((!inexact && a != b) || (inexact && (!isfinite(got) || distance > 1))) {
    ++failures;
    if (details++ < 8)
      printf("FAIL %s %s/%s n=%d got=%016" PRIx64 " want=%016" PRIx64 "\n",
             what, compilers[compiler], routes[route], n, a, b);
  }
}
static void check_one(const char *what, int n, int *c, double *v, double *x,
                      int inexact)
{
  int row[] = {0,n};
  double want = reference(n,c,v,x), baseline[2];
  for (int t = 0; t < 2; ++t) {
    tables[t][0](1,row,c,v,x,&baseline[t],n);
    compare(what,t,0,n,baseline[t],want,inexact);
  }
  for (int t = 0; t < (inexact ? 3 : 2); ++t)
    for (int k = t == 2 ? 0 : 1; k < 4; ++k) if (tables[t][k]) {
      double got;
      tables[t][k](1,row,c,v,x,&got,n);
      compare(what,t,k,n,got,want,inexact);
      if (!inexact)
        for (int b = 0; b < 2; ++b) compare("scalar-twin",t,k,n,got,baseline[b],0);
    }
}
static void exact_and_inexact(void)
{
  int c[33]; double v[33], x[67];
  for (int n = 1; n <= 33; ++n) {
    for (int j = 0; j < 67; ++j) x[j] = (int)(random32()%9)-4;
    for (int j = 0; j < n; ++j) { c[j] = random32()%67; v[j] = (int)(random32()%7)-3; }
    check_one("exact",n,c,v,x,0);
    for (int trial = 0; trial < 8; ++trial) {
      for (int j = 0; j < 67; ++j) x[j] = 0.5 + (random32()%10007)/10009.0;
      for (int j = 0; j < n; ++j) { c[j] = random32()%67; v[j] = 0.5+(random32()%10037)/10039.0; }
      check_one("inexact-1ULP",n,c,v,x,1);
    }
  }
}
static void order_cases(int seed)
{
  const int lengths[] = {13,16,17,27,32,33};
  int c[33]; double v[33], x[] = {1.0};
  int caught[2] = {0,0};
  for (int j = 0; j < 33; ++j) c[j] = 0;
  /* Sweep placements within and across chunks. The twins have in-order
     answers 0 and 1 under both 53- and 64-bit accumulators. */
  for (unsigned z = 0; z < sizeof lengths/sizeof lengths[0]; ++z) {
    int n = lengths[z], row[] = {0,n};
    for (int a = 0; a < n-2; ++a) for (int b = a+1; b < n-1; ++b)
      for (int d = b+1; d < n; ++d) for (int twin = 0; twin < 2; ++twin) {
        memset(v,0,sizeof v);
        v[a] = 0x1p70; v[b] = twin ? -0x1p70 : 1.0; v[d] = twin ? 1.0 : -0x1p70;
        if (!seed) check_one("order-twin",n,c,v,x,0);
        else {
          kernel mutants[] = {seed_tree53,seed_tree64};
          for (int t = 0; t < 2; ++t) if (!caught[t]) {
            double got;
            mutants[t](1,row,c,v,x,&got,n);
            int before = failures;
            compare(t ? "seed-tree64" : "seed-tree53",0,1,n,got,twin ? 1.0 : 0.0,0);
            caught[t] = failures != before;
          }
        }
      }
  }
  if (seed) {
    printf("MUTATION tree53_caught=%d tree64_caught=%d\n",caught[0],caught[1]);
    if (!caught[0] || !caught[1]) exit(2);
  }
}
static void *guarded(size_t bytes, size_t page, void **mapping)
{
  if (bytes > page) { fprintf(stderr,"guard allocation too large\n"); exit(2); }
  char *p = mmap(NULL,2*page,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
  if (p == MAP_FAILED || mprotect(p+page,page,PROT_NONE)) die("guard mmap");
  *mapping = p;
  return p+page-bytes;
}
static void bounds_cases(void)
{
  size_t page = sysconf(_SC_PAGESIZE);
  for (int n = 1; n <= 33; ++n) for (int future = 0; future < 2; ++future) {
    /* Case 0 ends both ordinary-load streams at PROT_NONE. Case 1 has
       accessible future index/value entries pointing to protected x;
       those x addresses may be prefetched but must never be loaded. */
    int nnz = n + (future ? 64 : 0), row[] = {0,n};
    void *mc, *mv, *mx;
    int *c = guarded(nnz*sizeof *c,page,&mc);
    double *v = guarded(nnz*sizeof *v,page,&mv);
    double *x = guarded(page,page,&mx);
    x[0] = 1;
    for (int j = 0; j < nnz; ++j) { c[j] = j < n ? 0 : page/sizeof *x; v[j] = 1; }
    for (int t = 0; t < 2; ++t) for (int k = 0; k < 4; ++k) if (tables[t][k]) {
      fflush(stdout);
      pid_t child = fork();
      if (child < 0) die("fork");
      if (!child) {
        struct rlimit limit = {0,0}; setrlimit(RLIMIT_CORE,&limit);
        double got; tables[t][k](1,row,c,v,x,&got,nnz);
        _exit(bits(got) == bits((double)n) ? 0 : 1);
      }
      int status; if (waitpid(child,&status,0) != child) die("waitpid");
      ++checks;
      if (!WIFEXITED(status) || WEXITSTATUS(status)) {
        ++failures;
        if (details++ < 8) printf("FAIL bounds %s/%s n=%d future=%d status=%d\n",
                                  compilers[t],routes[k],n,future,status);
      }
    }
    munmap(mc,2*page); munmap(mv,2*page); munmap(mx,2*page);
  }
}
static double now(void)
{
  struct timespec ts;
  if (clock_gettime(CLOCK_MONOTONIC,&ts)) die("clock_gettime");
  return ts.tv_sec + ts.tv_nsec*1.e-9;
}
static void *alloc(size_t bytes)
{
  void *p = NULL; if (posix_memalign(&p,64,bytes)) die("posix_memalign"); return p;
}
static void pin(void)
{
  cpu_set_t grant, one, actual;
  if (sched_getaffinity(0,sizeof grant,&grant)) die("getaffinity");
  int cpu = -1;
  printf("AFFINITY granted=");
  for (int c = 0; c < CPU_SETSIZE; ++c) if (CPU_ISSET(c,&grant)) {
    printf("%d,",c); if (cpu < 0) cpu = c;
  }
  if (cpu < 0) exit(2);
  CPU_ZERO(&one); CPU_SET(cpu,&one);
  if (sched_setaffinity(0,sizeof one,&one) || sched_getaffinity(0,sizeof actual,&actual)) die("pin");
  if (CPU_COUNT(&actual) != 1 || !CPU_ISSET(cpu,&actual)) exit(2);
  printf(" selected=%d single-core-timing page=%ld\n",cpu,sysconf(_SC_PAGESIZE));
}
static volatile double sink;
static double timed(kernel fn, int repeat, int rows, int *row, int *c,
                    double *v, double *x, double *out)
{
  double start = now();
  for (int j = 0; j < repeat; ++j) fn(rows,row,c,v,x,out,row[rows]);
  double elapsed = now()-start; sink = out[rows-1]; return elapsed;
}
static void performance(void)
{
  for (int memory = 0; memory < 2; ++memory) for (int length = 13; length <= 27; length += 14)
    for (int packed = 0; packed < 2; ++packed) {
      int rows = memory ? 8192 : 32, nx = memory ? 2097152 : 4096;
      int nnz = rows*length;
      int *row = alloc((rows+1)*sizeof *row), *c = alloc(nnz*sizeof *c);
      double *v = alloc(nnz*sizeof *v), *x = alloc(nx*sizeof *x);
      double *out = alloc(rows*sizeof *out), *want = alloc(rows*sizeof *want);
      for (int i = 0; i <= rows; ++i) row[i] = i*length;
      for (int i = 0; i < nx; ++i) x[i] = (int)(random32()%9)-4;
      int base = 0;
      for (int j = 0; j < nnz; ++j) {
        if (j%8 == 0) base = (random32()%(nx/8))*8;
        c[j] = packed ? base+j%8 : random32()%nx;
        v[j] = (int)(random32()%7)-3;
      }
      donor_routes[0](rows,row,c,v,x,want,nnz);
      int before = failures;
      for (int t = 0; t < 2; ++t) for (int k = 0; k < 4; ++k) {
        tables[t][k](rows,row,c,v,x,out,nnz);
        for (int r = 0; r < rows; ++r) compare("timing-input",t,k,length,out[r],want[r],0);
      }
      if (failures != before) return;
      int repeat = 1;
      double elapsed;
      do {
        elapsed = timed(knc_routes[0],repeat,rows,row,c,v,x,out);
        if (elapsed < 0.03 && repeat < 1048576) repeat *= 2; else break;
      } while (1);
      printf("CASE %s n=%d rows=%d rhs_bytes=%zu packed=%d repeat=%d\n",
             memory ? "memory-sized" : "cache-sized",length,rows,nx*sizeof *x,packed,repeat);
      for (int sample = 0; sample < 3; ++sample) {
        double seconds[8];
        for (int j = 0; j < 8; ++j) {
          int id = sample%2 ? 7-j : j;
          seconds[id] = timed(tables[id/4][id%4],repeat,rows,row,c,v,x,out);
          for (int r = 0; r < rows; ++r) compare("post-timing",id/4,id%4,length,out[r],want[r],0);
        }
        for (int id = 0; id < 8; ++id)
          printf("TIME sample=%d %s/%s seconds=%.9f speedup_vs_knc=%.6f speedup_vs_donor=%.6f\n",
                 sample,compilers[id/4],routes[id%4],seconds[id],seconds[4]/seconds[id],seconds[0]/seconds[id]);
      }
      free(row); free(c); free(v); free(x); free(out); free(want);
    }
}
int main(int argc, char **argv)
{
  setvbuf(stdout,NULL,_IOLBF,0);
  if (argc < 2 || argc > 3) { fprintf(stderr,"usage: %s SEED [--seed-tree|--correctness]\n",argv[0]); return 2; }
  char *end; unsigned long seed = strtoul(argv[1],&end,0);
  if (*end || end == argv[1]) return 2;
  rng = (uint32_t)seed;
  if (argc == 3 && strcmp(argv[2],"--seed-tree") && strcmp(argv[2],"--correctness")) return 2;
  printf("S12-30 seed=%u LDBL_MANT_DIG=%d fp-contract=off; fast=contraction-only\n",rng,LDBL_MANT_DIG);
  if (LDBL_MANT_DIG < 64) { puts("INFRA long double oracle needs >=64 bits"); return 2; }
  if (argc == 3 && !strcmp(argv[2],"--seed-tree")) { order_cases(1); return failures ? 1 : 2; }
  alarm(1100);
  int missing = 0;
  for (int t = 0; t < 3; ++t) for (int k = 0; k < 4; ++k) if (!tables[t][k]) {
    printf("FAIL missing route %s/%s\n",compilers[t],routes[k]); ++failures; ++missing;
  }
  exact_and_inexact(); order_cases(0); bounds_cases();
  printf("CORRECTNESS comparisons=%lu failures=%d missing=%d\n",checks,failures,missing);
  if (failures) { puts("FAIL phase-one: timing requires every route and all correctness checks"); return 1; }
  if (argc == 2) { pin(); performance(); }
  printf("%s S12-30 phase-one comparisons=%lu failures=%d\n",failures ? "FAIL" : "PASS",checks,failures);
  return failures ? 1 : 0;
}
#endif
