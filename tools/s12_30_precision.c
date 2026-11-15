#ifdef LEGAL_PROOF
/* Lead's 2026-11-14 Step 1: compiler-legal lookahead, no nnz ABI. */
#define _GNU_SOURCE
#include <stddef.h>
#define LEGAL_MIN_ROWS 16384
#define LEGAL_DISTANCE 32
#define LEGAL_ROW_LOOKAHEAD 3
struct matrix {
  int rows;
  const int *row, *col, *count;
  const double *val, *x;
  const int *const *cols;
  const double *const *vals;
};
typedef void (*legal_kernel)(const struct matrix *, double *);
#ifndef DRIVER
#define CAT_(a,b) a##b
#define CAT(a,b) CAT_(a,b)
#define FN(n) CAT(PREFIX,n)
static inline void hint(const double *p)
{
#ifdef HOST_MODEL
  __builtin_prefetch(p,0,3);
#else
  /* R27 p.641, verified hint semantics, early architectural specification,
     not a production measurement. This does not legalize index loads. */
  __asm__ volatile ("vprefetch0 (%0)" : : "r"(p));
#endif
}
static __attribute__((always_inline)) inline void csr_body(
    const struct matrix *a, double *out, int pf)
{
  for (int i = 0; i < a->rows; ++i) {
    int end = a->row[i+1], bound = end;
    if (pf && a->rows-i > LEGAL_ROW_LOOKAHEAD)
      bound = a->row[i+LEGAL_ROW_LOOKAHEAD+1];
    double sum = 0;
    for (int j = a->row[i]; j < end; ++j) {
      /* Widen subtraction; the guard also proves j+32 representable.
         Every index in [row[i],bound) is read by some row i..i+R,
         even with decreasing bounds. No assumed terminal nnz. */
      if (pf && (long long)bound-j > LEGAL_DISTANCE)
        hint(a->x + a->col[j+LEGAL_DISTANCE]);
      sum += a->val[j] * a->x[a->col[j]];
    }
    out[i] = sum;
  }
}
static __attribute__((always_inline)) inline void hpcg_body(
    const struct matrix *a, double *out, int pf)
{
  for (int i = 0; i < a->rows; ++i) {
    const int *col = a->cols[i], *future = NULL;
    const double *val = a->vals[i];
    int n = a->count[i], next = 0;
    if (pf && a->rows-i > 1) {
      next = a->count[i+1];
      future = a->cols[i+1];
    }
    double sum = 0;
    for (int j = 0; j < n; ++j) {
      if (pf && j < next) hint(a->x + future[j]);
      sum += val[j] * a->x[col[j]];
    }
    out[i] = sum;
  }
}
#ifdef COMPILER_PROOF
/* All four TUs compile the same unhinted source.  Only compiler/options
   differ; no handwritten hint or policy is present in this proof. */
void FN(csr_scalar)(const struct matrix *a, double *out) { csr_body(a,out,0); }
void FN(hpcg_scalar)(const struct matrix *a, double *out) { hpcg_body(a,out,0); }
legal_kernel const FN(legal)[2][1] = {
  {FN(csr_scalar)}, {FN(hpcg_scalar)}
};
#else
void FN(csr_scalar)(const struct matrix *a, double *out) { csr_body(a,out,0); }
void FN(csr_hint)(const struct matrix *a, double *out) { csr_body(a,out,1); }
void FN(csr_policy)(const struct matrix *a, double *out)
{
  if (a->rows >= LEGAL_MIN_ROWS) csr_body(a,out,1);
  else csr_body(a,out,0);
}
void FN(hpcg_scalar)(const struct matrix *a, double *out) { hpcg_body(a,out,0); }
void FN(hpcg_hint)(const struct matrix *a, double *out) { hpcg_body(a,out,1); }
void FN(hpcg_policy)(const struct matrix *a, double *out)
{
  if (a->rows >= LEGAL_MIN_ROWS) hpcg_body(a,out,1);
  else hpcg_body(a,out,0);
}
legal_kernel const FN(legal)[2][3] = {
  {FN(csr_scalar), FN(csr_hint), FN(csr_policy)},
  {FN(hpcg_scalar), FN(hpcg_hint), FN(hpcg_policy)}
};
#endif /* COMPILER_PROOF */
#else
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sched.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <sys/resource.h>
#ifdef COMPILER_PROOF
extern legal_kernel const donor_legal[2][1], knc_legal[2][1];
extern legal_kernel const enabled_legal[2][1], fast_legal[2][1];
static legal_kernel const (*tables[])[1] = {
  donor_legal, knc_legal, enabled_legal, fast_legal
};
static const char *compilers[] = {
  "donor-off", "knc-switch-off", "knc-switch-on", "knc-switch-on-contract-fast"
};
static const char *routes[] = {"compiler"};
#else
extern legal_kernel const donor_legal[2][3], knc_legal[2][3], fast_legal[2][3];
static legal_kernel const (*tables[])[3] = {donor_legal, knc_legal, fast_legal};
static const char *compilers[] = {"donor-off", "knc-off", "knc-contract-fast"};
static const char *routes[] = {"scalar", "legal-hint", "legal-policy"};
#endif
static const char *layouts[] = {"CSR", "HPCG-pointers"};
static uint32_t rng;
static unsigned long checks;
static int failures;
static void die(const char *s) { perror(s); exit(2); }
static uint32_t random32(void) { rng = rng*1664525u + 1013904223u; return rng; }
static uint64_t bits(double d) { uint64_t u; memcpy(&u,&d,8); return u; }
static void *alloc(size_t bytes)
{
  void *p = NULL; if (posix_memalign(&p,64,bytes ? bytes : 64)) die("alloc"); return p;
}
struct guard { void *base; size_t bytes; };
static void *guarded(size_t bytes, struct guard *g)
{
  size_t page = sysconf(_SC_PAGESIZE), usable = (bytes+page-1)/page*page;
  g->bytes = usable+page;
  g->base = mmap(NULL,g->bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
  if (g->base == MAP_FAILED || mprotect((char *)g->base+usable,page,PROT_NONE)) die("guard");
  return (char *)g->base+usable-bytes;
}
static void release(struct guard *g) { if (munmap(g->base,g->bytes)) die("munmap"); }
static void compare(double got, double want, int row)
{
  ++checks;
  if (bits(got) != bits(want)) {
    if (failures++ < 8) printf("FAIL row=%d got=%016" PRIx64 " want=%016" PRIx64 "\n",
                              row,bits(got),bits(want));
  }
}
static void reference(const struct matrix *a, int layout, double *out)
{
  for (int i = 0; i < a->rows; ++i) {
    int begin = layout ? 0 : a->row[i];
    int end = layout ? a->count[i] : a->row[i+1];
    const int *c = layout ? a->cols[i] : a->col;
    const double *v = layout ? a->vals[i] : a->val;
    long double sum = 0;
    for (int j = begin; j < end; ++j) sum += (long double)v[j]*a->x[c[j]];
    out[i] = (double)sum;
  }
}
/* Each kernel gets every fixture in its own child: a bad lookahead faults
   without hiding the remaining compiler/contraction/layout results. */
static void guarded_cases(int layout, legal_kernel fn)
{
  const int sizes[] = {0,1,2,4,7,LEGAL_MIN_ROWS,LEGAL_MIN_ROWS+1};
  for (int n = 1; n <= 33; ++n) for (int shape = 0; shape < 3; ++shape)
    for (unsigned z = 0; z < sizeof sizes/sizeof sizes[0]; ++z) {
      int rows = sizes[z], active = rows < 7 ? rows : 7;
      struct guard gr, gc, gv, gn, gcp, gvp;
      int *row = guarded((rows+1)*sizeof *row,&gr);
      int *count = guarded(rows*sizeof *count,&gn);
      const int **cols = guarded(rows*sizeof *cols,&gcp);
      const double **vals = guarded(rows*sizeof *vals,&gvp);
      /* The active rows sit at the array end, exercising final lookahead
         and both policy arms without allocating a huge matrix fixture. */
      int nonmonotone[] = {0,1,2,1,3,2,3,3};
      for (int i = 0; i <= rows; ++i) {
        int r = i-(rows-active);
        row[i] = r <= 0 ? 0 : n*(shape == 2 ? nonmonotone[r] :
                                (shape == 1 && r == active ? r-1 : r));
      }
      int max = 0;
      for (int i = 0; i <= rows; ++i) if (row[i] > max) max = row[i];
      int *c = guarded(max*sizeof *c,&gc);
      double *v = guarded(max*sizeof *v,&gv), x[67];
      for (int i = 0; i < 67; ++i) x[i] = (int)(random32()%9)-4;
      for (int j = 0; j < max; ++j) { c[j] = random32()%67; v[j] = (int)(random32()%7)-3; }
      /* HPCG row allocations are independent, each ending at its own
         guard. Zero-count rows point directly at PROT_NONE. */
      struct guard *cg = alloc(rows*sizeof *cg), *vg = alloc(rows*sizeof *vg);
      for (int i = 0; i < rows; ++i) {
        count[i] = row[i+1] > row[i] ? row[i+1]-row[i] : 0;
        if (layout && count[i]) {
          int *ci = guarded(count[i]*sizeof *ci,&cg[i]);
          double *vi = guarded(count[i]*sizeof *vi,&vg[i]);
          for (int j = 0; j < count[i]; ++j) { ci[j] = c[row[i]+j]; vi[j] = v[row[i]+j]; }
          cols[i] = ci; vals[i] = vi;
        } else { cols[i] = c+max; vals[i] = v+max; }
      }
      struct matrix a = {rows,row,c,count,v,x,cols,vals};
      double *out = alloc(rows*sizeof *out), *want = alloc(rows*sizeof *want);
      reference(&a,layout,want);
      fn(&a,out);
      for (int i = 0; i < rows; ++i) compare(out[i],want[i],i);
      if (layout) for (int i = 0; i < rows; ++i) if (count[i]) { release(&cg[i]); release(&vg[i]); }
      free(cg); free(vg); free(out); free(want);
      release(&gr); release(&gc); release(&gv); release(&gn); release(&gcp); release(&gvp);
    }
}
static void correctness(void)
{
  for (int layout = 0; layout < 2; ++layout)
    for (unsigned t = 0; t < sizeof tables/sizeof tables[0]; ++t)
    for (unsigned k = 0; k < sizeof routes/sizeof routes[0]; ++k) {
      fflush(stdout);
      pid_t child = fork(); if (child < 0) die("fork");
      if (!child) {
        struct rlimit limit = {0,0}; setrlimit(RLIMIT_CORE,&limit);
        guarded_cases(layout,tables[t][layout][k]);
        printf("GUARDS %s %s/%s comparisons=%lu failures=%d\n",
               layouts[layout],compilers[t],routes[k],checks,failures);
        _exit(failures ? 1 : 0);
      }
      int status; if (waitpid(child,&status,0) != child) die("waitpid");
      ++checks;
      if (!WIFEXITED(status) || WEXITSTATUS(status)) {
        ++failures;
        printf("FAIL guard child %s %s/%s status=%d\n",layouts[layout],compilers[t],routes[k],status);
      }
    }
}
static double now(void)
{
  struct timespec ts; if (clock_gettime(CLOCK_MONOTONIC,&ts)) die("clock");
  return ts.tv_sec+ts.tv_nsec*1.e-9;
}
static void pin(void)
{
  cpu_set_t grant, one;
  if (sched_getaffinity(0,sizeof grant,&grant)) die("affinity");
  int cpu = -1;
  printf("AFFINITY granted=");
  for (int i = 0; i < CPU_SETSIZE; ++i) if (CPU_ISSET(i,&grant)) {
    printf("%d,",i); if (cpu < 0) cpu = i;
  }
  if (cpu < 0) exit(2);
  CPU_ZERO(&one); CPU_SET(cpu,&one);
  if (sched_setaffinity(0,sizeof one,&one)) die("pin");
  printf(" selected=%d single-core-timing\n",cpu);
}
static volatile double sink;
static double sample_time(legal_kernel fn, const struct matrix *a,
                          double *out, int *batch, uint64_t *calls)
{
  double seconds = 0; *calls = 0;
  do {
    double start = now();
    for (int j = 0; j < *batch; ++j) fn(a,out);
    double part = now()-start; sink = out[a->rows-1];
    seconds += part; *calls += *batch;
    if (part < 0.25 && *batch < 33554432) *batch *= 2;
  } while (seconds < 0.5);
  return seconds;
}
static void performance(void)
{
  const int row_sizes[] = {32,14000,32768}, rhs_sizes[] = {4096,14000,2097152};
  const char *sets[] = {"cache-sized","CG-A-sized","memory-sized"};
  for (int set = 0; set < 3; ++set) for (int n = 13; n <= 27; n += 14)
    for (int packed = 0; packed < 2; ++packed) {
      int rows = row_sizes[set], nx = rhs_sizes[set], nz = rows*n;
      int *row = alloc((rows+1)*sizeof *row), *c = alloc(nz*sizeof *c);
      int *count = alloc(rows*sizeof *count);
      const int **cols = alloc(rows*sizeof *cols);
      const double **vals = alloc(rows*sizeof *vals);
      double *v = alloc(nz*sizeof *v), *x = alloc(nx*sizeof *x);
      double *out = alloc(rows*sizeof *out), *want = alloc(rows*sizeof *want);
      for (int i = 0; i <= rows; ++i) row[i] = i*n;
      for (int i = 0; i < nx; ++i) x[i] = (int)(random32()%9)-4;
      int base = 0;
      for (int j = 0; j < nz; ++j) {
        if (j%8 == 0) base = (random32()%(nx/8))*8;
        c[j] = packed ? base+j%8 : random32()%nx;
        v[j] = (int)(random32()%7)-3;
      }
      /* Independent per-row allocations, with a shuffled physical row
         order. Pointer/count loads and layout costs are inside timing. */
      int *perm = alloc(rows*sizeof *perm);
      for (int i = 0; i < rows; ++i) perm[i] = i;
      for (int i = rows-1; i > 0; --i) {
        int j = random32()%(i+1), tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp;
      }
      for (int r = 0; r < rows; ++r) {
        int i = perm[r];
        int *ci = alloc(n*sizeof *ci); double *vi = alloc(n*sizeof *vi);
        memcpy(ci,c+i*n,n*sizeof *ci); memcpy(vi,v+i*n,n*sizeof *vi);
        cols[i] = ci; vals[i] = vi; count[i] = n;
      }
      struct matrix a = {rows,row,c,count,v,x,cols,vals};
      for (int layout = 0; layout < 2; ++layout) {
        reference(&a,layout,want);
#ifdef COMPILER_PROOF
        const int compiler_ids[] = {0,1,2,3}, route_ids[] = {0,0,0,0};
#else
        const int compiler_ids[] = {0,1,1,1}, route_ids[] = {0,0,1,2};
#endif
        int before = failures, batch[4] = {1,1,1,1};
        for (int id = 0; id < 4; ++id) {
          tables[compiler_ids[id]][layout][route_ids[id]](&a,out);
          for (int i = 0; i < rows; ++i) compare(out[i],want[i],i);
        }
        if (failures != before) exit(1);
        printf("CASE %s %s n=%d rows=%d rhs_bytes=%zu packed=%d policy=%s min_seconds=0.5 samples=5\n",
               sets[set],layouts[layout],n,rows,nx*sizeof *x,packed,
               rows >= LEGAL_MIN_ROWS ? "hint" : "scalar");
        for (int sample = 0; sample < 5; ++sample) {
          double seconds[4], per_call[4]; uint64_t calls[4];
          for (int j = 0; j < 4; ++j) {
            int id = sample%2 ? 3-j : j;
            seconds[id] = sample_time(tables[compiler_ids[id]][layout][route_ids[id]],&a,out,&batch[id],&calls[id]);
            per_call[id] = seconds[id]/calls[id];
            for (int i = 0; i < rows; ++i) compare(out[i],want[i],i);
          }
          for (int id = 0; id < 4; ++id)
            printf("TIME sample=%d %s/%s seconds=%.9f calls=%" PRIu64
                   " seconds_per_call=%.12g speedup_vs_knc=%.6f speedup_vs_donor=%.6f\n",
                   sample,compilers[compiler_ids[id]],routes[route_ids[id]],seconds[id],calls[id],per_call[id],
                   per_call[1]/per_call[id],per_call[0]/per_call[id]);
        }
      }
      for (int i = 0; i < rows; ++i) { free((void *)cols[i]); free((void *)vals[i]); }
      free(perm); free(cols); free(vals); free(count); free(row); free(c); free(v); free(x); free(out); free(want);
    }
}
int main(int argc, char **argv)
{
  setvbuf(stdout,NULL,_IOLBF,0);
  if (argc < 2 || argc > 3 || (argc == 3 && strcmp(argv[2],"--correctness"))) return 2;
  char *end; rng = strtoul(argv[1],&end,0); if (*end || end == argv[1]) return 2;
  printf("S12-30 LEGAL seed=%u R=%d distance=%d policy_rows=%d no-nnz-ABI\n",
         rng,LEGAL_ROW_LOOKAHEAD,LEGAL_DISTANCE,LEGAL_MIN_ROWS);
#ifdef HOST_MODEL
  puts("HOST MODEL: correctness only; no native performance evidence");
#endif
  alarm(570);
  correctness();
  printf("CORRECTNESS children=%lu failures=%d\n",checks,failures);
  if (failures) return 1;
  if (argc == 2) { pin(); performance(); }
  printf("%s S12-30 legal comparisons_and_children=%lu failures=%d\n",
         failures ? "FAIL" : "PASS",checks,failures);
  return failures ? 1 : 0;
}
#endif /* DRIVER */
#elif defined(PHASE2_T1)
/* Compiler-only probes: no hints in the eligible reductions.  The
   available bound is the current row/end, never an assumed CSR nnz. */
void sparse_rows(int rows, const int *row, const int *col,
                 const double *val, const double *x, double *out)
{
  for (int i = 0; i < rows; ++i) {
    double sum = 0;
    for (int j = row[i]; j < row[i+1]; ++j)
      sum += val[j] * x[col[j]];
    out[i] = sum;
  }
}
double sparse_slice(int begin, int end, const int *col,
                    const double *val, const double *x)
{
  double sum = 0;
  for (int j = begin; j < end; ++j)
    sum += val[j] * x[col[j]];
  return sum;
}
void sparse_hpcg(int rows, const int *count, const int *const *cols,
                 const double *const *vals, const double *x, double *out)
{
  for (int i = 0; i < rows; ++i) {
    const int *col = cols[i];
    const double *val = vals[i];
    double sum = 0;
    for (int j = 0; j < count[i]; ++j)
      sum += val[j] * x[col[j]];
    out[i] = sum;
  }
}
/* int output may change a later row bound; no cross-row speculation. */
void alias_bounds(int rows, const int *row, const int *col,
                  const double *val, const double *x, int *out)
{
  for (int i = 0; i < rows; ++i) {
    double sum = 0;
    for (int j = row[i]; j < row[i+1]; ++j)
      sum += val[j] * x[col[j]];
    out[i] = (int)sum;
  }
}
/* Executable scanner controls, including a deliberately row-local hint
   that must NOT satisfy the short-row cross-row acceptance check. */
#define CSR_CONTROL(NAME, LOOK) \
void NAME(int rows, const int *row, const int *col, const double *x) \
{ \
  for (int i = 0; i < rows; ++i) \
    for (int j = row[i]; j < row[i+1]; ++j) \
      if (rows-i > LOOK) { \
        int bound = row[i+LOOK+1]; \
        if ((long long)bound-j > 32) \
          __builtin_prefetch(x + col[j+32], 0, 3); \
      } \
}
CSR_CONTROL(explicit_csr, 3)
CSR_CONTROL(explicit_rowlocal, 0)
void explicit_hpcg(int rows, const int *count, const int *const *cols,
                   const double *x)
{
  for (int i = 0; i < rows; ++i)
    for (int j = 0; j < count[i]; ++j)
      if (rows-i > 1 && j < count[i+1])
        __builtin_prefetch(x + cols[i+1][j], 0, 3);
}
void explicit_loop(int n, const int *col, const double *x)
{
  for (int j = 0; j < n; ++j)
    __builtin_prefetch(x + col[j], 0, 3);
}
double volatile_indices(int end, const volatile int *col,
                        const double *val, const double *x)
{
  double sum = 0;
  for (int j = 0; j < end; ++j)
    sum += val[j] * x[col[j]];
  return sum;
}
/* An early exit makes even an in-row speculative ordinary index load unsafe. */
double sentinel_slice(int end, const int *col,
                      const double *val, const double *x)
{
  double sum = 0;
  for (int j = 0; j < end; ++j) {
    if (val[j] == 0) break;
    sum += val[j] * x[col[j]];
  }
  return sum;
}
/* Scanner controls: distinguish an indirect hint from a stream hint. */
void explicit_indirect(int j, int end, const int *col, const double *x)
{
  if ((long long)end - j > 32)
    __builtin_prefetch(x + col[j+32], 0, 3);
}
void explicit_stream(int j, const int *col, const double *x)
{
  __builtin_prefetch(col + j + 32, 0, 3);
  __builtin_prefetch(x + j + 32, 0, 3);
}
#else
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
/* Fixed lookahead: 360 estimated instructions / about 11 instructions per
   scalar nonzero, rounded to 32. This is a hypothesis, not measured latency;
   see docs/research/knc-costs.md and s12-30-phase1.md. */
#define DISTANCE 32
static inline void indirect(int j, int nnz, const int *col, const double *x)
{
  if (nnz-j > DISTANCE) {
    const double *future = x + col[j+DISTANCE];
#ifdef HOST_MODEL
    __builtin_prefetch(future,0,3);
#else
    /* R27 p.641, verified architectural hint semantics (early KNC spec,
       not a production measurement): only the hint may address protected x. */
    __asm__ volatile ("vprefetch0 (%0)" : : "r"(future));
#endif
  }
}
void FN(prefetch)(ARGS)
{
  for (int i = 0; i < rows; ++i) {
    double sum = 0;
    for (int j = row[i]; j < row[i+1]; ++j) {
      indirect(j,nnz,col,x);
      sum += val[j] * x[col[j]];
    }
    out[i] = sum;
  }
}

#ifdef HOST_MODEL
/* Fixture model only. This code is never linked into a card binary. */
static void FN(products)(const int *c, const double *v, const double *x,
                         double *p, int n)
{
  for (int i = 0; i < n; ++i) {
    volatile double rounded = v[i] * x[c[i]];
    p[i] = rounded;
  }
}
#else
#define STR_(s) #s
#define STR(s) STR_(s)
/* One call handles up to 16 products as two eight-FP64 vectors. The same
   file-scope inline assembly is assembled for donor/off, KNC/off and fast.
   A regular call exposes register clobbers even to the scalar-only donor.
   p has 64-byte alignment and space for 16 doubles; 1 <= n <= 16.
   R27 pp.297-299,349-354,361-366,399-401: verified instruction semantics,
   early KNC specification, not a production performance measurement.
   R03 pp.15-22: verified ABI, independent of production stepping. */
extern void FN(products)(const int *, const double *, const double *, double *, int);
__asm__(
  ".text\n.local " STR(FN(products)) "\n"
  ".type " STR(FN(products)) ",@function\n"
  STR(FN(products)) ":\n"
  "movq %rcx,%r11\n"
  "1:\n"
  "movl $8,%ecx\n"
  "cmpl %ecx,%r8d\n"
  "jge 5f\n"
  "movl %r8d,%ecx\n"
  "5:\n"
  "movl $1,%r9d\n"
  "shll %cl,%r9d\n"
  "decl %r9d\n"
  "kmov %r9d,%k1\n"
  "kmov %r9d,%k2\n"
  "vloadunpackld (%rdi),%zmm0{%k1}\n"
  /* Do not issue a high-line load unless that line contains active data. */
  "movl %edi,%eax\n"
  "andl $63,%eax\n"
  "leal (%rax,%rcx,4),%eax\n"
  "cmpl $64,%eax\n"
  "jle 2f\n"
  "vloadunpackhd 64(%rdi),%zmm0{%k1}\n"
  "2:\n"
  "vloadunpacklpd (%rsi),%zmm2{%k1}\n"
  "movl %esi,%eax\n"
  "andl $63,%eax\n"
  "leal (%rax,%rcx,8),%eax\n"
  "cmpl $64,%eax\n"
  "jle 3f\n"
  "vloadunpackhpd 64(%rsi),%zmm2{%k1}\n"
  "3:\n"
  "vgatherdpd (%rdx,%zmm0,8),%zmm1{%k2}\n"
  "jknzd 3b,%k2\n"
  "vmulpd %zmm2,%zmm1,%zmm1{%k1}\n"
  "vmovapd %zmm1,(%r11){%k1}\n"
  "subl $8,%r8d\n"
  "jle 4f\n"
  "addq $32,%rdi\n"
  "addq $64,%rsi\n"
  "addq $64,%r11\n"
  "jmp 1b\n"
  "4: ret\n"
  ".size " STR(FN(products)) ",.-" STR(FN(products)) "\n"
);
#endif

static __attribute__((always_inline)) inline void vector_fold(ARGS, int pf)
{
  double p[16] __attribute__((aligned(64)));
  for (int i = 0; i < rows; ++i) {
    /* Preserve the x87 accumulator across helper calls without FP64 spills. */
    long double sum = 0;
    for (int j = row[i]; j < row[i+1];) {
      int n = row[i+1]-j;
      if (n > 16) n = 16;
      if (pf) for (int k = 0; k < n; ++k) indirect(j+k,nnz,col,x);
      FN(products)(col+j,val+j,x,p,n);
      for (int k = 0; k < n; ++k) sum += p[k];
      j += n;
    }
    out[i] = (double)sum;
  }
}
void FN(gather)(ARGS) { vector_fold(rows,row,col,val,x,out,nnz,0); }
void FN(combined)(ARGS) { vector_fold(rows,row,col,val,x,out,nnz,1); }
kernel const FN(routes)[4] = {FN(scalar), FN(gather), FN(prefetch), FN(combined)};

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
    for (int t = 0; t < 3; ++t) for (int k = 0; k < 4; ++k) if (tables[t][k]) {
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
static double sample_time(kernel fn, int *batch, uint64_t *calls, int rows,
                          int *row, int *c, double *v, double *x, double *out)
{
  double seconds = 0;
  *calls = 0;
  do {
    double part = timed(fn,*batch,rows,row,c,v,x,out);
    seconds += part;
    *calls += *batch;
    if (part < 0.25 && *batch < 33554432) *batch *= 2;
  } while (seconds < 0.5);
  return seconds;
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
      int batch[8] = {1,1,1,1,1,1,1,1};
      printf("CASE %s n=%d rows=%d rhs_bytes=%zu packed=%d min_seconds=0.5 samples=5\n",
             memory ? "memory-sized" : "cache-sized",length,rows,nx*sizeof *x,packed);
      for (int sample = 0; sample < 5; ++sample) {
        double seconds[8], per_call[8];
        uint64_t calls[8];
        for (int j = 0; j < 8; ++j) {
          int id = sample%2 ? 7-j : j;
          seconds[id] = sample_time(tables[id/4][id%4],&batch[id],&calls[id],
                                    rows,row,c,v,x,out);
          per_call[id] = seconds[id]/calls[id];
          for (int r = 0; r < rows; ++r) compare("post-timing",id/4,id%4,length,out[r],want[r],0);
        }
        for (int id = 0; id < 8; ++id)
          printf("TIME sample=%d %s/%s seconds=%.9f calls=%" PRIu64
                 " seconds_per_call=%.12g speedup_vs_knc=%.6f speedup_vs_donor=%.6f\n",
                 sample,compilers[id/4],routes[id%4],seconds[id],calls[id],per_call[id],
                 per_call[4]/per_call[id],per_call[0]/per_call[id]);
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
#ifdef HOST_MODEL
  puts("HOST MODEL ONLY: scalar FP64 products, no IMCI execution, no performance evidence");
#else
  puts("NATIVE: A/A+B IMCI FP64 products, ordered x87 long-double fold; B lookahead=32");
#endif
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
#endif /* PHASE2_T1 */
