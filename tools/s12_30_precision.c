#ifdef LEGAL_PROOF
/* Lead's 2026-11-14 Step 1: compiler-legal lookahead, no nnz ABI. */
#define _GNU_SOURCE
#include <stddef.h>
#ifndef LEGAL_MIN_ROWS
#define LEGAL_MIN_ROWS 16384 /* the compiler's default cutoff */
#endif
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
struct shape {
  const char *count;
  const int *const *cols;
  const double *const *vals;
  double *const *diag;
};
typedef void (*shape_kernel)(int, int, const struct shape *, const double *, double *);
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
/* The generated slots compile unhinted C.  The manual slot is the policy
   in hand-written form: the legal hints run only when the nest has
   LEGAL_MIN_ROWS rows (a lone loop: iterations) and the first indices of
   its first three rows (a lone loop: its first three indices) are each
   more than LEGAL_NEAR elements apart.  Stencil and banded rows start a
   few elements apart and keep the unhinted code; random rows do not.  The
   first index of a row is read only if that row is nonempty, a per-row
   pointer only if its count is positive, and nothing below LEGAL_MIN_ROWS. */
#ifndef MANUAL_PROOF
#define MANUAL_PROOF 0
#endif
#define LEGAL_NEAR 8 /* one 64-byte line of FP64 values */
/* One-time host defects in the manual slot: 1 samples below the row
   cutoff, 2 reads the first index of rows it has not found nonempty.  */
#ifndef SAMPLE_SEED
#define SAMPLE_SEED 0
#endif
int FN(arm); /* manual slot: 1 when the last call took the hinted arm */
/* Control slot, switch off: the plain nest twice in one function, as a
   versioned nest is, selected by a flag that is never set.  The copy that
   never runs negates its store so that the two cannot be merged.  It
   separates the cost of sharing a function from the cost of the policy. */
#ifndef TWIN_PROOF
#define TWIN_PROOF 0
#endif
volatile int FN(twin);
static inline int far(int a, int b)
{
  long long d = (long long)b-a;
  return d > LEGAL_NEAR || d < -LEGAL_NEAR;
}
/* Rows FIRST, FIRST+STEP, FIRST+2*STEP of an N-row interval.  OK holds
   any proof the later counts need (bytes disjoint from the stores). */
#define ROWS_RANDOM(count, cols, first, step, n, ok) __extension__ ({ \
  long long a_ = (first), s_ = (step); \
  int far_ = 0; \
  if ((SAMPLE_SEED == 1 || (n) >= LEGAL_MIN_ROWS) && (ok) \
      && (SAMPLE_SEED == 2 || ((count)[a_] > 0 && (count)[a_+s_] > 0 \
                               && (count)[a_+2*s_] > 0))) \
    far_ = far((cols)[a_][0],(cols)[a_+s_][0]) \
           && far((cols)[a_+s_][0],(cols)[a_+2*s_][0]); \
  far_; })
/* Match the raw-argument T1 probes.  */
static __attribute__((always_inline)) inline void csr_rows(int rows,
    const int *row, const int *col, const double *val, const double *x,
    double *out, int pf)
{
  for (int i = 0; i < rows; ++i) {
    int end = row[i+1], bound = end;
    if (pf == 1 && rows-i > LEGAL_ROW_LOOKAHEAD)
      bound = row[i+LEGAL_ROW_LOOKAHEAD+1];
    double sum = 0;
    for (int j = row[i]; j < end; ++j) {
      if (pf == 1 && (long long)bound-j > LEGAL_DISTANCE)
        hint(x+col[j+LEGAL_DISTANCE]);
      sum += val[j]*x[col[j]];
    }
    out[i] = pf == 2 ? -sum : sum;
  }
}
static __attribute__((noinline,noclone)) void FN(csr_raw)(int rows,
    const int *row, const int *col, const double *val, const double *x, double *out)
{
#if MANUAL_PROOF
  FN(arm) = 0;
  if ((SAMPLE_SEED == 1 || rows >= LEGAL_MIN_ROWS)
      && (SAMPLE_SEED == 2 || (row[0] < row[1] && row[1] < row[2] && row[2] < row[3])))
    FN(arm) = far(col[row[0]],col[row[1]]) && far(col[row[1]],col[row[2]]);
  if (FN(arm)) { csr_rows(rows,row,col,val,x,out,1); return; }
#endif
#if TWIN_PROOF
  if (FN(twin)) { csr_rows(rows,row,col,val,x,out,2); return; }
#endif
  csr_rows(rows,row,col,val,x,out,0);
}
static __attribute__((always_inline)) inline void hpcg_rows(int rows,
    const int *count, const int *const *cols, const double *const *vals,
    const double *x, double *out, int pf)
{
  for (int i = 0; i < rows; ++i) {
    const int *col = cols[i], *future = NULL;
    const double *val = vals[i];
    int n = count[i], next = 0;
    if (pf == 1 && rows-i > 1 && (next = count[i+1]) > 0) future = cols[i+1];
    double sum = 0;
    for (int j = 0; j < n; ++j) {
      if (pf == 1 && j < next) hint(x+future[j]);
      sum += val[j]*x[col[j]];
    }
    out[i] = pf == 2 ? -sum : sum;
  }
}
static __attribute__((noinline,noclone)) void FN(hpcg_raw)(int rows,
    const int *count, const int *const *cols, const double *const *vals,
    const double *x, double *out)
{
#if MANUAL_PROOF
  FN(arm) = ROWS_RANDOM(count,cols,0,1,rows,1);
  if (FN(arm)) { hpcg_rows(rows,count,cols,vals,x,out,1); return; }
#endif
#if TWIN_PROOF
  if (FN(twin)) { hpcg_rows(rows,count,cols,vals,x,out,2); return; }
#endif
  hpcg_rows(rows,count,cols,vals,x,out,0);
}
void FN(csr_scalar)(const struct matrix *a, double *out)
{ FN(csr_raw)(a->rows,a->row,a->col,a->val,a->x,out); }
void FN(hpcg_scalar)(const struct matrix *a, double *out)
{ FN(hpcg_raw)(a->rows,a->count,a->cols,a->vals,a->x,out); }
static __attribute__((always_inline)) inline double lone_sum(int end,
    const int *col, const double *val, const double *x, int pf)
{
  double sum = 0;
  for (int j = 0; j < end; ++j) {
    if (pf && (long long)end-j > LEGAL_DISTANCE)
      hint(x+col[j+LEGAL_DISTANCE]);
    sum += val[j]*x[col[j]];
  }
  return sum;
}
void FN(lone_scalar)(const struct matrix *a, double *out)
{
  const int *col = a->col;
  const double *val = a->val, *x = a->x;
  int end = a->count[0];
#if MANUAL_PROOF
  FN(arm) = (SAMPLE_SEED == 1 || end >= LEGAL_MIN_ROWS)
            && far(col[0],col[1]) && far(col[1],col[2]);
  if (FN(arm)) { out[0] = lone_sum(end,col,val,x,1); return; }
#endif
  out[0] = lone_sum(end,col,val,x,0);
}
legal_kernel const FN(legal)[3][1] = {
  {FN(csr_scalar)}, {FN(hpcg_scalar)}, {FN(lone_scalar)}
};
/* Application-form kernels, as the T1 struct probes: byte counts and
   pointer tables through a struct, a worker interval, subtract folds and
   a backward sweep.  SHAPE_SEED is a one-time host defect: a next-row hint
   with no test that the count bytes are disjoint from the stored vector. */
#ifndef SHAPE_SEED
#define SHAPE_SEED 0
#endif
/* The count bytes of rows [BEGIN,ROWS) against the elements stored.  */
static inline int disjoint(const char *count, const double *stored,
                           int begin, int rows)
{
  const char *low = (const char *)(stored+begin), *high = (const char *)(stored+rows);
  return count+rows <= low || high <= count+begin;
}
static __attribute__((always_inline)) inline void spmv_rows(int begin,
    int rows, const struct shape *m, const double *x, double *out, int pf)
{
  for (int i = begin; i < rows; ++i) {
    double sum = 0;
    const double *const cur_vals = m->vals[i];
    const int *const cur_inds = m->cols[i];
    const int cur_nnz = m->count[i];
    const int *future = NULL;
    int next = 0;
    if (pf && rows-i > 1 && (next = m->count[i+1]) > 0)
      future = m->cols[i+1];
    for (int j = 0; j < cur_nnz; ++j) {
      if (pf && j < next) hint(x+future[j]);
      sum += cur_vals[j] * x[cur_inds[j]];
    }
    out[i] = sum;
  }
}
void FN(shape_spmv)(int begin, int rows, const struct shape *m,
                    const double *x, double *out)
{
#if MANUAL_PROOF
  FN(arm) = ROWS_RANDOM(m->count,m->cols,begin,1,(long long)rows-begin,
                        disjoint(m->count,out,begin,rows));
  if (FN(arm)) { spmv_rows(begin,rows,m,x,out,1); return; }
#endif
  spmv_rows(begin,rows,m,x,out,SHAPE_SEED);
}
/* DOWN sweeps rows-1..0 and looks ahead to row i-1.  Manual slot only:
   the generated slots keep the two sweeps in the T1 probe form below.  */
static __attribute__((always_inline)) inline void sweep_rows(int rows,
    const struct shape *m, const double *rhs, double *x, int down)
{
  for (int i = down ? rows-1 : 0; down ? i >= 0 : i < rows; i += down ? -1 : 1) {
    const double *const cur_vals = m->vals[i];
    const int *const cur_inds = m->cols[i];
    const int cur_nnz = m->count[i];
    const double diag = m->diag[i][0];
    const int *future = NULL;
    int next = 0;
    if ((down ? i > 0 : rows-i > 1)
        && (next = m->count[down ? i-1 : i+1]) > 0)
      future = m->cols[down ? i-1 : i+1];
    double sum = rhs[i];
    for (int j = 0; j < cur_nnz; ++j) {
      if (j < next) hint(x+future[j]);
      sum -= cur_vals[j] * x[cur_inds[j]];
    }
    sum += x[i] * diag;
    x[i] = sum / diag;
  }
}
void FN(shape_forward)(int begin, int rows, const struct shape *m,
                       const double *rhs, double *x)
{
  (void)begin;
#if MANUAL_PROOF
  FN(arm) = ROWS_RANDOM(m->count,m->cols,0,1,rows,disjoint(m->count,x,0,rows));
  if (FN(arm)) { sweep_rows(rows,m,rhs,x,0); return; }
#endif
  for (int i = 0; i < rows; ++i) {
    const double *const cur_vals = m->vals[i];
    const int *const cur_inds = m->cols[i];
    const int cur_nnz = m->count[i];
    const double diag = m->diag[i][0];
    double sum = rhs[i];
    for (int j = 0; j < cur_nnz; ++j)
      sum -= cur_vals[j] * x[cur_inds[j]];
    sum += x[i] * diag;
    x[i] = sum / diag;
  }
}
void FN(shape_backward)(int begin, int rows, const struct shape *m,
                        const double *rhs, double *x)
{
  (void)begin;
#if MANUAL_PROOF
  FN(arm) = ROWS_RANDOM(m->count,m->cols,(long long)rows-1,-1,rows,
                        disjoint(m->count,x,0,rows));
  if (FN(arm)) { sweep_rows(rows,m,rhs,x,1); return; }
#endif
  for (int i = rows - 1; i >= 0; --i) {
    const double *const cur_vals = m->vals[i];
    const int *const cur_inds = m->cols[i];
    const int cur_nnz = m->count[i];
    const double diag = m->diag[i][0];
    double sum = rhs[i];
    for (int j = 0; j < cur_nnz; ++j)
      sum -= cur_vals[j] * x[cur_inds[j]];
    sum += x[i] * diag;
    x[i] = sum / diag;
  }
}
shape_kernel const FN(shapes)[3] = {
  FN(shape_spmv), FN(shape_forward), FN(shape_backward)
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
/* Slot 4 is the default-on compiler with the row cutoff lowered to its
   minimum, so the hinted arm also runs on the small guard fixtures and at
   every size of the cutoff grid.  The last slot is the hand-written
   policy; its decision is read after it has run.  */
enum { DONOR, OFF, ON, FAST, MIN4, TWIN, MANUAL, SLOTS };
extern legal_kernel const donor_legal[3][1], knc_legal[3][1], enabled_legal[3][1];
extern legal_kernel const fast_legal[3][1], min4_legal[3][1], twin_legal[3][1];
extern legal_kernel const manual_legal[3][1];
static legal_kernel const (*tables[])[1] = {
  donor_legal, knc_legal, enabled_legal, fast_legal, min4_legal, twin_legal,
  manual_legal
};
static const char *compilers[] = {
  "donor-off", "knc-switch-off", "knc-switch-on", "knc-switch-on-contract-fast",
  "knc-switch-on-min4", "knc-switch-off-two-nests", "knc-handwritten-policy"
};
static const char *routes[] = {"compiler"};
extern shape_kernel const donor_shapes[3], knc_shapes[3], enabled_shapes[3];
extern shape_kernel const fast_shapes[3], min4_shapes[3], twin_shapes[3];
extern shape_kernel const manual_shapes[3];
static shape_kernel const *shape_tables[] = {
  donor_shapes, knc_shapes, enabled_shapes, fast_shapes, min4_shapes, twin_shapes,
  manual_shapes
};
extern int manual_arm;
static const char *shape_names[] = {"struct-spmv", "struct-forward", "struct-backward"};
#else
extern legal_kernel const donor_legal[2][3], knc_legal[2][3], fast_legal[2][3];
static legal_kernel const (*tables[])[3] = {donor_legal, knc_legal, fast_legal};
static const char *compilers[] = {"donor-off", "knc-off", "knc-contract-fast"};
static const char *routes[] = {"scalar", "legal-hint", "legal-policy"};
#endif
static const char *layouts[] = {"CSR", "HPCG-pointers", "lone-loop"};
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
  for (int n = 1; n <= 33; ++n) for (int shape = 0; shape < 4; ++shape)
    for (unsigned z = 0; z < sizeof sizes/sizeof sizes[0]; ++z) {
      int rows = sizes[z], active = rows < 7 ? rows : 7;
      struct guard gr, gc, gv, gn, gcp, gvp;
      int *row = guarded((rows+1)*sizeof *row,&gr);
      int *count = guarded(rows*sizeof *count,&gn);
      const int **cols = guarded(rows*sizeof *cols,&gcp);
      const double **vals = guarded(rows*sizeof *vals,&gvp);
      /* The active rows sit at the array end, exercising final lookahead
         and both policy arms without allocating a huge matrix fixture.
         Shapes 0-2 of a long fixture start with three n-entry rows, the
         rows a locality sample reads.  Shape 3 starts with four empty
         rows bounded at the end of col: reading the first index of an
         empty sampled row faults. */
      int lead = shape < 3 && rows-active >= 3 ? 3 : 0;
      int base = shape == 3 && rows-active < 4 ? 4 : rows-active;
      int nonmonotone[] = {0,1,2,1,3,2,3,3};
      for (int i = 0; i <= rows; ++i) {
        int r = i-base;
        row[i] = i < lead ? i*n :
                 lead*n + (r <= 0 ? 0 : n*(shape == 2 ? nonmonotone[r] :
                                           (shape == 1 && r == active ? r-1 : r)));
      }
      int max = 0;
      for (int i = 0; i <= rows; ++i) if (row[i] > max) max = row[i];
      for (int i = 0; shape == 3 && i <= 3 && i <= rows; ++i) row[i] = max;
      int *c = guarded(max*sizeof *c,&gc);
      double *v = guarded(max*sizeof *v,&gv), x[67];
      for (int i = 0; i < 67; ++i) x[i] = (int)(random32()%9)-4;
      for (int j = 0; j < max; ++j) { c[j] = random32()%67; v[j] = (int)(random32()%7)-3; }
      /* Sampled rows start far apart, so the hinted arm runs; every
         fourth length starts them on one line and keeps the plain arm. */
      for (int k = 0; rows >= 4 && k < 3; ++k)
        if (row[k] < row[k+1]) c[row[k]] = n%4 == 3 ? 5+k : 33*k;
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
        failures = 0; /* report this kernel alone, not earlier children */
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
#ifdef COMPILER_PROOF
static void lone_cases(legal_kernel fn)
{
  /* Below four iterations a three-index sample would cross the guard.  */
  const int sizes[] = {0,1,2,3,4,5,32,33,16383,16384,16385};
  for (unsigned z = 0; z < 2*sizeof sizes/sizeof sizes[0]; ++z) {
    int n = sizes[z/2], row[] = {0,n};
    struct guard gc, gv;
    int *col = guarded(n*sizeof *col,&gc);
    double *val = guarded(n*sizeof *val,&gv), x[67], out, want;
    for (int i = 0; i < 67; ++i) x[i] = (int)(random32()%9)-4;
    for (int j = 0; j < n; ++j) { col[j] = random32()%67; val[j] = (int)(random32()%7)-3; }
    for (int j = 0; j < 3 && j < n; ++j) col[j] = z%2 ? 5+j : 33*j;
    struct matrix a = {1,row,col,&n,val,x,NULL,NULL};
    reference(&a,0,&want);
    fn(&a,&out); compare(out,want,0);
    release(&gc); release(&gv);
  }
}
static void lone_guards(void)
{
  for (unsigned t = 0; t < sizeof tables/sizeof tables[0]; ++t) {
    fflush(stdout);
    pid_t child = fork(); if (child < 0) die("fork");
    if (!child) {
      struct rlimit limit = {0,0}; setrlimit(RLIMIT_CORE,&limit);
      failures = 0;
      lone_cases(tables[t][2][0]);
      printf("GUARDS %s %s/%s comparisons=%lu failures=%d\n",
             layouts[2],compilers[t],routes[0],checks,failures);
      _exit(failures ? 1 : 0);
    }
    int status; if (waitpid(child,&status,0) != child) die("waitpid");
    ++checks;
    if (!WIFEXITED(status) || WEXITSTATUS(status)) {
      ++failures;
      printf("FAIL guard child %s %s/%s status=%d\n",layouts[2],compilers[t],routes[0],status);
    }
  }
}
/* Application-form fixtures.  LOW puts the tables after a guard page, so
   a row below the first faults; otherwise they end at one, so a row past
   the last faults.  Small integers, unit values and +-1 diagonals keep
   every product, sum and quotient exact. */
static void *edge(size_t bytes, struct guard *g, int low)
{
  if (!low) return guarded(bytes,g);
  size_t page = sysconf(_SC_PAGESIZE), usable = (bytes+page-1)/page*page;
  g->bytes = usable+page;
  g->base = mmap(NULL,g->bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
  if (g->base == MAP_FAILED || mprotect(g->base,page,PROT_NONE)) die("guard");
  return (char *)g->base+page;
}
static void shape_reference(int kind, int begin, int rows, const struct shape *m,
                            const double *in, double *out)
{
  for (int k = begin; k < rows; ++k) {
    int i = kind == 2 ? rows-1-k : k, n = m->count[i];
    if (!kind) {
      long double sum = 0;
      for (int j = 0; j < n; ++j) sum += (long double)m->vals[i][j]*in[m->cols[i][j]];
      out[i] = (double)sum;
    } else {
      long double diag = m->diag[i][0], sum = in[i];
      for (int j = 0; j < n; ++j) sum -= (long double)m->vals[i][j]*out[m->cols[i][j]];
      sum += out[i]*diag;
      out[i] = (double)(sum/diag);
    }
  }
}
/* The kernel sees rows [begin,begin+rows) of tables biased by -begin. */
#define BIAS(p,b) ((void *)((uintptr_t)(p)-(uintptr_t)(b)*sizeof *(p)))
static void shape_cases(int kind, shape_kernel fn, void *trap)
{
  const int lengths[] = {1,13,27,33}, sizes[] = {1,2,7,LEGAL_MIN_ROWS,LEGAL_MIN_ROWS+1};
  const int vary[2][7] = {{1,0,1,2,1,1,2},{2,1,1,2,1,0,1}};
  for (unsigned l = 0; l < 4; ++l) for (int shape = 0; shape < 3; ++shape)
    for (unsigned z = 0; z < sizeof sizes/sizeof sizes[0]; ++z)
      for (int low = 0; low < 2; ++low) {
        int rows = sizes[z], active = rows < 7 ? rows : 7;
        int first = low ? 0 : rows-active, begin = kind ? 0 : 5;
        /* A sweep's vector extends past its rows, so that three first
           indices can lie far apart even in a seven-row fixture.  */
        int nx = kind ? rows+67 : 67, near = (l+z)%4 == 3;
        struct guard gn, gc, gv, gd;
        char *count = edge(rows,&gn,low);
        const int **cols = edge(rows*sizeof *cols,&gc,low);
        const double **vals = edge(rows*sizeof *vals,&gv,low);
        double **diag = edge(rows*sizeof *diag,&gd,low);
        struct guard *cg = alloc(rows*sizeof *cg), *vg = alloc(rows*sizeof *vg);
        double *x = alloc(nx*sizeof *x), *rhs = alloc(rows*sizeof *rhs);
        double *dv = alloc(rows*sizeof *dv);
        size_t out = (kind ? nx : rows)*sizeof(double);
        double *got = alloc(out), *want = alloc(out);
        for (int i = 0; i < nx; ++i) x[i] = (int)(random32()%9)-4;
        for (int i = 0; i < rows; ++i) {
          /* K < 3: one of the three rows a locality sample reads, in
             sweep order.  Shape 0 leaves those outside the active rows
             empty behind the protected page; the other shapes fill them. */
          int r = i-first, k = kind == 2 ? rows-1-i : i;
          count[i] = r < 0 || r >= active ? 0 : lengths[l]*(shape ? vary[shape-1][r] : 1);
          if (rows >= 4 && k < 3 && shape && (r < 0 || r >= active)) count[i] = lengths[l];
          rhs[i] = (int)(random32()%9)-4; dv[i] = i&1 ? -1 : 1; diag[i] = &dv[i];
          cols[i] = trap; vals[i] = trap;
          if (count[i]) {
            int *ci = guarded(count[i]*sizeof *ci,&cg[i]);
            double *vi = guarded(count[i]*sizeof *vi,&vg[i]);
            for (int j = 0; j < count[i]; ++j) { ci[j] = random32()%nx; vi[j] = (int)(random32()%3)-1; }
            if (rows >= 4 && k < 3) ci[0] = near ? 5+k : 33*k;
            cols[i] = ci; vals[i] = vi;
          }
        }
        struct shape m = {BIAS(count,begin),BIAS(cols,begin),BIAS(vals,begin),BIAS(diag,begin)};
        if (kind) { memcpy(want,x,out); memcpy(got,x,out); }
        shape_reference(kind,begin,begin+rows,&m,kind ? rhs : x,BIAS(want,begin));
        fn(begin,begin+rows,&m,kind ? rhs : x,BIAS(got,begin));
        for (int i = 0; i < rows; ++i) compare(got[i],want[i],i);
        for (int i = 0; i < rows; ++i) if (count[i]) { release(&cg[i]); release(&vg[i]); }
        free(cg); free(vg); free(x); free(rhs); free(dv); free(got); free(want);
        release(&gn); release(&gc); release(&gv); release(&gd);
      }
}
/* The byte counts live inside the vector the nest stores.  Row HOT has
   five zero-valued entries and its store clears the count of the row that
   follows it in sweep order, which was 27 until then and whose index
   pointer is a protected page.  The program never enters that row; a
   next-row hint taken from the stale count faults.  The first three rows
   in sweep order hold one zero-valued entry each, far apart, so that a
   locality sample alone would choose the hinted arm; their count bytes
   lie in an element that is stored unchanged after they are read. */
static void shape_overlap(int kind, shape_kernel fn, void *trap)
{
  enum { HOT = 3 };
  int rows = LEGAL_MIN_ROWS, index[5] = {0,1,2,3,4};
  static const int apart[3] = {0,4096,8192};
  size_t bias = 7*HOT+(kind == 2);
  double zero[5] = {0}, *stored[2], hot;
  const int **cols = alloc(rows*sizeof *cols);
  const double **vals = alloc(rows*sizeof *vals);
  double **diag = alloc(rows*sizeof *diag), one = 1;
  double *in = alloc(rows*sizeof *in);
  for (int i = 0; i < rows; ++i) { cols[i] = trap; vals[i] = trap; diag[i] = &one; in[i] = 0; }
  cols[HOT] = index; vals[HOT] = zero;
  for (int k = 0; k < 3; ++k) {
    int i = kind == 2 ? rows-1-k : k;
    cols[i] = &apart[k]; vals[i] = zero;
  }
  for (int pass = 0; pass < 2; ++pass) {
    unsigned char *bytes = alloc(rows*sizeof(double));
    memset(bytes,0,rows*sizeof(double));
    bytes[bias+HOT] = 5; bytes[bias+HOT+(kind == 2 ? -1 : 1)] = 27;
    for (int k = 0; k < 3; ++k) bytes[bias+(kind == 2 ? rows-1-k : k)] = 1;
    stored[pass] = (double *)bytes;
    memcpy(&hot,bytes+HOT*sizeof hot,sizeof hot);
    /* SpMV reads a separate nonnegative vector; a sweep cancels the stored
       denormal exactly, so both store +0.0 over the stale count. */
    for (int i = 0; kind == 0 && i < 5; ++i) in[i] = i;
    if (kind) in[HOT] = -hot;
    struct shape m = {(const char *)bytes+bias,cols,vals,diag};
    if (pass) fn(0,rows,&m,in,stored[1]);
    else shape_reference(kind,0,rows,&m,in,stored[0]);
  }
  compare(stored[0][HOT],0.0,HOT);
  for (int i = 0; i < rows; ++i) compare(stored[1][i],stored[0][i],i);
  free(stored[0]); free(stored[1]); free(cols); free(vals); free(diag); free(in);
}
static void shape_guards(void)
{
  size_t page = sysconf(_SC_PAGESIZE);
  void *trap = mmap(NULL,page,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
  if (trap == MAP_FAILED) die("trap");
  for (unsigned t = 0; t < sizeof shape_tables/sizeof shape_tables[0]; ++t)
    for (int kind = 0; kind < 3; ++kind) for (int overlap = 0; overlap < 2; ++overlap) {
      fflush(stdout);
      pid_t child = fork(); if (child < 0) die("fork");
      if (!child) {
        struct rlimit limit = {0,0}; setrlimit(RLIMIT_CORE,&limit);
        failures = 0;
        if (overlap) shape_overlap(kind,shape_tables[t][kind],trap);
        else shape_cases(kind,shape_tables[t][kind],trap);
        printf("SHAPES %s %s %s comparisons=%lu failures=%d\n",shape_names[kind],
               overlap ? "count-in-stored-vector" : "guards",compilers[t],checks,failures);
        _exit(failures ? 1 : 0);
      }
      int status; if (waitpid(child,&status,0) != child) die("waitpid");
      ++checks;
      if (!WIFEXITED(status) || WEXITSTATUS(status)) {
        ++failures;
        printf("FAIL shape child %s %s %s status=%d\n",shape_names[kind],
               overlap ? "count-in-stored-vector" : "guards",compilers[t],status);
      }
    }
}
#endif
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
#ifdef COMPILER_PROOF
    /* Keep half-second samples close to their minimum so the expanded
       threshold grid fits the lead's single ten-minute card window. */
    if (part < 0.025 && *batch < 33554432) *batch *= 2;
#else
    if (part < 0.25 && *batch < 33554432) *batch *= 2;
#endif
  } while (seconds < 0.5);
  return seconds;
}
#ifdef COMPILER_PROOF
static int timing; /* 0 under --correctness: verify and decide, no clock */
/* The hand-written policy must take the arm the case was built for.  */
static void decision(const char *label, const char *form, int rows, int n, int expect)
{
  ++checks;
  printf("DECISION %s %s n=%d rows=%d handwritten-policy=%s expected=%s\n",label,form,n,rows,
         manual_arm ? "hint" : "scalar",expect ? "hint" : "scalar");
  if (manual_arm != expect) { ++failures; printf("FAIL decision %s %s\n",label,form); }
}
/* IDS always holds the switch-off build.  The largest cutoff-grid cases
   leave the donor out to fit the card window; its ratio then prints 0.  */
static void print_times(int sample, const int *ids, int count,
                        const double *seconds, const uint64_t *calls)
{
  double off = 0, donor = 0;
  for (int j = 0; j < count; ++j) {
    if (ids[j] == OFF) off = seconds[j]/calls[j];
    if (ids[j] == DONOR) donor = seconds[j]/calls[j];
  }
  for (int j = 0; j < count; ++j) {
    double per = seconds[j]/calls[j];
    printf("TIME sample=%d %s seconds=%.9f calls=%" PRIu64
           " seconds_per_call=%.12g speedup_vs_knc=%.6f speedup_vs_donor=%.6f\n",
           sample,compilers[ids[j]],seconds[j],calls[j],per,off/per,donor/per);
  }
}
/* PATTERN 0: uniformly random columns.  1: the 27-point stencil of a
   104-cubed grid.  2: ascending columns.  Every slot runs the same
   matrix, so the work per call is the same; only the call count that
   fills half a second differs.  */
static void compiler_case(const char *label, int layout, int rows, int n,
                          int nx, int pattern, const int *ids, int count, int expect)
{
  int nz = rows*n;
  long long nnz = 0;
  int *row = alloc((rows+1)*sizeof *row), *c = alloc(nz*sizeof *c);
  int *counts = alloc(rows*sizeof *counts);
  const int **cols = alloc(rows*sizeof *cols);
  const double **vals = alloc(rows*sizeof *vals);
  double *v = alloc(nz*sizeof *v), *x = alloc(nx*sizeof *x);
  double *out = alloc(rows*sizeof *out), *want = alloc(rows*sizeof *want);
  for (int i = 0; i <= rows; ++i) row[i] = i*n;
  for (int i = 0; i < nx; ++i) x[i] = (int)(random32()%9)-4;
  for (int i = 0; i < rows; ++i) {
    counts[i] = n; cols[i] = c+i*n; vals[i] = v+i*n;
    if (pattern == 1) {
      int ix = i%104, iy = i/104%104, iz = i/(104*104), k = 0;
      for (int dz = -1; dz <= 1; ++dz)
        for (int dy = -1; dy <= 1; ++dy)
          for (int dx = -1; dx <= 1; ++dx)
            if (ix+dx >= 0 && ix+dx < 104 && iy+dy >= 0 && iy+dy < 104
                && iz+dz >= 0 && iz+dz < 104) {
              c[i*n+k] = i+dx+104*dy+104*104*dz;
              v[i*n+k++] = dx || dy || dz ? -1 : 26;
            }
      counts[i] = k;
    } else for (int j = 0; j < n; ++j) {
      c[i*n+j] = pattern ? (i*n+j)%nx : (int)(random32()%nx);
      v[i*n+j] = (int)(random32()%7)-3;
    }
    nnz += counts[i];
  }
  /* Random pointer layout retains independent shuffled row allocations;
     the stencil uses contiguous row storage with genuine boundary counts. */
  int *perm = alloc(rows*sizeof *perm);
  for (int i = 0; i < rows; ++i) perm[i] = i;
  if (layout == 1 && !pattern) {
    for (int i = rows-1; i > 0; --i) {
      int j = random32()%(i+1), t = perm[i]; perm[i] = perm[j]; perm[j] = t;
    }
    for (int r = 0; r < rows; ++r) {
      int i = perm[r]; int *ci = alloc(n*sizeof *ci); double *vi = alloc(n*sizeof *vi);
      memcpy(ci,c+i*n,n*sizeof *ci); memcpy(vi,v+i*n,n*sizeof *vi);
      cols[i] = ci; vals[i] = vi;
    }
  }
  struct matrix a = {rows,row,c,counts,v,x,cols,vals};
  reference(&a,layout == 1,want);
  /* The timed slots, then the hand-written policy for its decision; the
     guard suites have already run every slot.  */
  for (int j = 0; j <= count; ++j) {
    tables[j < count ? ids[j] : MANUAL][layout][0](&a,out);
    for (int i = 0; i < rows; ++i) compare(out[i],want[i],i);
  }
  if (failures) exit(1);
  decision(label,layouts[layout],rows,n,expect);
  printf("CASE %s %s n=%d rows=%d nnz=%lld rhs_bytes=%zu columns=%s default_policy=%s min_seconds=0.5 samples=5\n",
         label,layouts[layout],n,rows,nnz,nx*sizeof *x,
         pattern == 1 ? "stencil" : pattern ? "ascending" : "random",
         expect ? "hint" : "scalar");
  int batch[SLOTS];
  for (int j = 0; j < SLOTS; ++j) batch[j] = 1;
  for (int sample = 0; timing && sample < 5; ++sample) {
    double seconds[SLOTS]; uint64_t calls[SLOTS];
    for (int j = 0; j < count; ++j) {
      int k = sample%2 ? count-1-j : j;
      seconds[k] = sample_time(tables[ids[k]][layout][0],&a,out,&batch[k],&calls[k]);
      for (int i = 0; i < rows; ++i) compare(out[i],want[i],i);
    }
    print_times(sample,ids,count,seconds,calls);
  }
  if (layout == 1 && !pattern)
    for (int i = 0; i < rows; ++i) { free((void *)cols[i]); free((void *)vals[i]); }
  free(perm); free(cols); free(vals); free(counts); free(row); free(c); free(v); free(x); free(out); free(want);
}
/* The same stencil in the application form: byte counts, pointer tables
   and a pointer to each row's diagonal.  A sweep restarts from the same
   vector before every call, outside the clock.  The values are inexact,
   so every slot is compared bit for bit with the switch-off build; the
   long-double reference is reported, not judged.  */
static void shape_case(int kind)
{
  enum { G = 104 };
  int rows = G*G*G;
  size_t bytes = rows*sizeof(double);
  long long nnz = 0;
  char *count = alloc(rows);
  int *c = alloc((size_t)rows*27*sizeof *c);
  double *v = alloc((size_t)rows*27*sizeof *v);
  const int **cols = alloc(rows*sizeof *cols);
  const double **vals = alloc(rows*sizeof *vals);
  double **diag = alloc(rows*sizeof *diag);
  double *in = alloc(bytes), *start = alloc(bytes), *work = alloc(bytes);
  double *base = alloc(bytes), *want = alloc(bytes);
  for (int i = 0; i < rows; ++i) {
    int ix = i%G, iy = i/G%G, iz = i/(G*G), k = 0;
    cols[i] = c+(size_t)i*27; vals[i] = v+(size_t)i*27;
    for (int dz = -1; dz <= 1; ++dz)
      for (int dy = -1; dy <= 1; ++dy)
        for (int dx = -1; dx <= 1; ++dx)
          if (ix+dx >= 0 && ix+dx < G && iy+dy >= 0 && iy+dy < G
              && iz+dz >= 0 && iz+dz < G) {
            if (!dx && !dy && !dz) diag[i] = &v[(size_t)i*27+k];
            c[(size_t)i*27+k] = i+dx+G*dy+G*G*dz;
            v[(size_t)i*27+k++] = dx || dy || dz ? -1 : 26;
          }
    count[i] = k; nnz += k;
    in[i] = (int)(random32()%9)-4; start[i] = (int)(random32()%9)-4;
  }
  struct shape m = {count,cols,vals,diag};
  int unlike = 0;
  memcpy(want,start,bytes);
  shape_reference(kind,0,rows,&m,in,want);
  memcpy(base,start,bytes);
  shape_tables[OFF][kind](0,rows,&m,in,base);
  for (int i = 0; i < rows; ++i) unlike += bits(base[i]) != bits(want[i]);
  for (int t = 0; t < SLOTS; ++t) {
    memcpy(work,start,bytes);
    shape_tables[t][kind](0,rows,&m,in,work);
    for (int i = 0; i < rows; ++i) compare(work[i],base[i],i);
  }
  if (failures) exit(1);
  decision("stencil-104-cubed",shape_names[kind],rows,27,0);
  printf("CASE stencil-104-cubed %s n=27 rows=%d nnz=%lld rhs_bytes=%zu columns=stencil default_policy=scalar"
         " reference_mismatches=%d min_seconds=0.5 samples=5\n",shape_names[kind],rows,nnz,bytes,unlike);
  static const int ids[] = {DONOR,OFF,ON};
  for (int sample = 0; timing && sample < 5; ++sample) {
    double seconds[3]; uint64_t calls[3];
    for (int j = 0; j < 3; ++j) {
      int k = sample%2 ? 2-j : j;
      seconds[k] = 0; calls[k] = 0;
      do {
        memcpy(work,start,bytes);
        double begin = now();
        shape_tables[ids[k]][kind](0,rows,&m,in,work);
        seconds[k] += now()-begin; ++calls[k];
      } while (seconds[k] < 0.5);
      for (int i = 0; i < rows; ++i) compare(work[i],base[i],i);
    }
    print_times(sample,ids,3,seconds,calls);
  }
  free(count); free(c); free(v); free(cols); free(vals); free(diag);
  free(in); free(start); free(work); free(base); free(want);
}
static void performance(void)
{
  static const int plain[] = {DONOR,OFF,ON}, twin[] = {DONOR,OFF,ON,TWIN};
  static const int forced[] = {DONOR,OFF,ON,MIN4,TWIN}, pair[] = {OFF,ON};
  static const int square[] = {14000,32768,65536,131072,262144};
  /* Nests far below any cutoff: the plain arm against switch-off.  */
  for (int layout = 0; layout < 2; ++layout)
    for (int n = 13; n <= 27; n += 14)
      compiler_case("small",layout,32,n,4096,0,twin,4,0);
  /* Cutoff grid: one x element per row, uniformly random columns.  Below
     the default cutoff the min4 slot shows what the hint would do and the
     two-nest control what sharing a function costs; above it the policy
     hints, and only switch-off and switch-on are timed.  */
  for (unsigned z = 0; z < sizeof square/sizeof square[0]; ++z)
    for (int layout = 0; layout < 2; ++layout)
      for (int n = 13; n <= 27; n += 14) {
        int hinted = square[z] >= LEGAL_MIN_ROWS;
        compiler_case("square",layout,square[z],n,square[z],0,
                      hinted ? pair : forced,hinted ? 2 : 5,hinted);
      }
  /* Reported control: many rows over a 32 KiB x, which no row count sees. */
  for (int layout = 0; layout < 2; ++layout)
    compiler_case("small-x",layout,32768,13,4096,0,plain,3,1);
  compiler_case("stencil-104-cubed",1,104*104*104,27,104*104*104,1,plain,3,0);
  for (int kind = 0; kind < 3; ++kind) shape_case(kind);
  compiler_case("lone-memory",2,1,262144,2097152,0,plain,3,1);
  compiler_case("lone-ascending",2,1,262144,2097152,2,plain,3,0);
}
#else
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
#endif
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
#ifdef COMPILER_PROOF
  lone_guards();
  shape_guards();
#endif
  printf("CORRECTNESS children=%lu failures=%d\n",checks,failures);
  if (failures) return 1;
#ifdef COMPILER_PROOF
  /* --correctness still builds every case, checks every slot and the
     hand-written decisions; only the clock is skipped.  */
  timing = argc == 2;
  if (timing) pin();
  performance();
#else
  if (argc == 2) { pin(); performance(); }
#endif
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
/* Reduced application shapes: byte counts and pointer tables arrive through
   a struct, and each row's value pointer, index pointer and int count are
   loaded to locals before the inner loop, so the field loads hoist out of
   the nest and only the per-row loads remain in it.  The SpMV start models
   an outlined worker's assigned interval.  The sweeps finish each row with
   the diagonal update and store into the vector they read.
   These are compiler probes, not a numerical application implementation. */
struct sparse_matrix_probe {
  const char *count;
  const int *const *cols;
  const double *const *vals;
  double *const *diag;
};
void sparse_struct_spmv(int begin, int rows, const struct sparse_matrix_probe *m,
                        const double *x, double *out)
{
  for (int i = begin; i < rows; ++i) {
    double sum = 0;
    const double *const cur_vals = m->vals[i];
    const int *const cur_inds = m->cols[i];
    const int cur_nnz = m->count[i];
    for (int j = 0; j < cur_nnz; ++j)
      sum += cur_vals[j] * x[cur_inds[j]];
    out[i] = sum;
  }
}
void sparse_struct_forward(int rows, const struct sparse_matrix_probe *m,
                           const double *rhs, double *x)
{
  for (int i = 0; i < rows; ++i) {
    const double *const cur_vals = m->vals[i];
    const int *const cur_inds = m->cols[i];
    const int cur_nnz = m->count[i];
    const double diag = m->diag[i][0];
    double sum = rhs[i];
    for (int j = 0; j < cur_nnz; ++j)
      sum -= cur_vals[j] * x[cur_inds[j]];
    sum += x[i] * diag;
    x[i] = sum / diag;
  }
}
void sparse_struct_backward(int rows, const struct sparse_matrix_probe *m,
                            const double *rhs, double *x)
{
  for (int i = rows - 1; i >= 0; --i) {
    const double *const cur_vals = m->vals[i];
    const int *const cur_inds = m->cols[i];
    const int cur_nnz = m->count[i];
    const double diag = m->diag[i][0];
    double sum = rhs[i];
    for (int j = 0; j < cur_nnz; ++j)
      sum -= cur_vals[j] * x[cur_inds[j]];
    sum += x[i] * diag;
    x[i] = sum / diag;
  }
}
/* Scanner control for the struct nests: a hand-written next-row hint with
   no reduction.  It must scan as indirect through the ->cols field load,
   and the compiler must not report a transformation of it. */
void explicit_struct(int rows, const struct sparse_matrix_probe *m,
                     const double *x)
{
  for (int i = 0; i < rows; ++i) {
    const int cur_nnz = m->count[i];
    for (int j = 0; j < cur_nnz; ++j)
      if (rows-i > 1 && j < m->count[i+1])
        __builtin_prefetch(x + m->cols[i+1][j], 0, 3);
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
