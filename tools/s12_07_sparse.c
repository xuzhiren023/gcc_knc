/* Independent ordered sparse-loop diagnostic for S12-07. No card launch here. */
#define _GNU_SOURCE
#include <stddef.h>
#ifndef DRIVER
#define CAT_(a,b) a##b
#define CAT(a,b) CAT_(a,b)
#define FN(n) CAT(PREFIX,n)
#define ARGS int n, const long long *row, const double *a, const int *col, \
  double *x, const double *rhs, double *y

void FN(spmv)(ARGS)
{
  for (int i = 0; i < n; ++i) {
    double s = 0.0;
    for (long long j = row[i]; j < row[i+1]; ++j)
      s += a[j] * x[col[j]];
    y[i] = s;
  }
}

void FN(symgs)(ARGS)
{
  for (int pass = 0; pass < 2; ++pass)
    for (int k = 0; k < n; ++k) {
      int i = pass ? n-1-k : k;
      double s = rhs[i];
      for (long long j = row[i]; j < row[i+1]; ++j)
        s -= a[j] * x[col[j]];
      /* The first entry is the diagonal, also included in the ordered sum. */
      s += x[i] * a[row[i]];
      x[i] = s / a[row[i]];
    }
  for (int i = 0; i < n; ++i) y[i] = x[i];
}

void FN(contiguous)(ARGS)
{
  for (int i = 0; i < n; ++i) {
    double s = 0.0;
    for (long long j = row[i]; j < row[i+1]; ++j)
      s += a[j] * x[j];
    y[i] = s;
  }
}
#else
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <unistd.h>
#include <sched.h>

typedef void (*kernel)(int, const long long *, const double *, const int *,
                       double *, const double *, double *);
#define DECL(p) \
  extern void p##spmv(int,const long long*,const double*,const int*,double*,const double*,double*); \
  extern void p##symgs(int,const long long*,const double*,const int*,double*,const double*,double*); \
  extern void p##contiguous(int,const long long*,const double*,const int*,double*,const double*,double*); \
  extern void p##cg(int,const long long*,const double*,const int*,double*,const double*,double*);
DECL(donor_)
DECL(knc_)
DECL(nosched_)
DECL(nopf_)
static kernel kernels[4][4] = {
  {donor_cg, donor_spmv, donor_symgs, donor_contiguous},
  {knc_cg, knc_spmv, knc_symgs, knc_contiguous},
  {nosched_cg, nosched_spmv, nosched_symgs, nosched_contiguous},
  {nopf_cg, nopf_spmv, nopf_symgs, nopf_contiguous}
};
static const char *variants[] = {"donor", "knc", "nosched", "nopf"};
static const char *names[] = {"cg", "spmv", "symgs", "contiguous"};
static double now(void) {
  struct timespec t;
  if (clock_gettime(CLOCK_MONOTONIC, &t)) exit(2);
  return t.tv_sec + t.tv_nsec * 1.e-9;
}
static void *alloc(size_t bytes) {
  void *p = NULL;
  if (posix_memalign(&p, 64, bytes)) exit(2);
  return p;
}
static void pages(void *p) {
  FILE *f = fopen("/proc/self/smaps", "r");
  char line[256]; unsigned long lo, hi; int active = 0;
  if (!f) { puts("PAGES unavailable"); return; }
  while (fgets(line, sizeof line, f)) {
    if (sscanf(line, "%lx-%lx", &lo, &hi) == 2)
      active = (uintptr_t)p >= lo && (uintptr_t)p < hi;
    if (active && (!strncmp(line, "KernelPageSize:", 15) ||
                   !strncmp(line, "MMUPageSize:", 12) ||
                   !strncmp(line, "AnonHugePages:", 14)))
      printf("PAGES %s", line);
  }
  fclose(f);
}
int main(void) {
  cpu_set_t cpus;
  setvbuf(stdout, NULL, _IOLBF, 0);
  alarm(180); /* Hard bound: one serial diagnostic, including validation. */
  if (sched_getaffinity(0, sizeof cpus, &cpus) || CPU_COUNT(&cpus) != 1) {
    fputs("FAIL: single-core timing requires exactly one granted CPU\n", stderr);
    return 2;
  }
  printf("CLOCK monotonic CPU %d\n", sched_getcpu());
  for (int size = 0; size < 2; ++size)
    for (int kind = 0; kind < 4; ++kind)
      for (int layout = 0; layout < (kind == 3 ? 1 : 2); ++layout) {
        int n = size ? 8192 : 32;
        int degree = (kind == 1 || kind == 2) ? 27 : 128;
        size_t nnz = (size_t)n * degree;
        size_t nx = size ? 2097152 : 4096;
        long long *row = alloc((n+1) * sizeof *row);
        int *col = alloc(nnz * sizeof *col);
        double *a = alloc(nnz * sizeof *a), *x = alloc(nx * sizeof *x);
        double *initial = alloc(nx * sizeof *initial);
        double *rhs = alloc(n * sizeof *rhs), *y = alloc(n * sizeof *y);
        double *expected = alloc(n * sizeof *expected);
        for (size_t j = 0; j < nx; ++j) initial[j] = ((int)(j%31)-15) / 32.0;
        for (int i = 0; i <= n; ++i) row[i] = (long long)i * degree;
        for (int i = 0; i < n; ++i) {
          rhs[i] = ((i%17)-8) / 16.0;
          for (int j = 0; j < degree; ++j) {
            size_t k = row[i] + j;
            /* Vary occupied lines without changing either accumulation order. */
            unsigned int group = (unsigned int)(i*degree + j/8);
            col[k] = layout ? (int)((k*104729u + 17u) % nx)
                            : (int)(((group*104729u) % (nx/8))*8 + j%8);
            a[k] = (j%7-3) / 256.0;
          }
          if (kind == 2) { col[row[i]] = i; a[row[i]] = 2.0; }
        }
        printf("CASE %s %s %s nnz=%zu xbytes=%zu\n", size ? "memory" : "cache",
               names[kind], layout ? "spread" : "packed", nnz, nx*sizeof *x);
        pages(x);
        /* Validate every output, with identical starting state for each compiler. */
        for (int v = 0; v < 4; ++v) {
          memcpy(x, initial, nx*sizeof *x);
          kernels[v][kind](n,row,a,col,x,rhs,y);
          if (!v) memcpy(expected,y,n*sizeof *y);
          else if (memcmp(expected,y,n*sizeof *y)) {
            printf("FAIL output %s %s\n", names[kind], variants[v]); return 1;
          }
        }
        /* Calibrate once per case; all paired variants do identical work. */
        int reps = 1;
        double elapsed;
        do {
          memcpy(x, initial, nx*sizeof *x);
          double start = now();
          for (int r = 0; r < reps; ++r) kernels[0][kind](n,row,a,col,x,rhs,y);
          elapsed = now()-start;
          if (elapsed < .02) reps *= 2;
        } while (elapsed < .02 && reps < 1048576);
        for (int sample = 0; sample < 3; ++sample)
          for (int order = 0; order < 4; ++order) {
            int v = sample%2 ? 3-order : order;
            memcpy(x, initial, nx*sizeof *x);
            double start = now();
            for (int r = 0; r < reps; ++r) kernels[v][kind](n,row,a,col,x,rhs,y);
            elapsed = now()-start;
            if (!v) memcpy(expected,y,n*sizeof *y);
            printf("TIME variant=%s sample=%d reps=%d seconds=%.9f\n",
                   variants[v],sample,reps,elapsed);
          }
        /* Check repeated updates too, outside timing and in a fixed order. */
        for (int v = 0; v < 4; ++v) {
          memcpy(x, initial, nx*sizeof *x);
          for (int r = 0; r < reps; ++r) kernels[v][kind](n,row,a,col,x,rhs,y);
          if (!v) memcpy(expected,y,n*sizeof *y);
          else if (memcmp(expected,y,n*sizeof *y)) {
            printf("FAIL repeated output %s %s\n", names[kind], variants[v]); return 1;
          }
        }
        puts("PASS ordered output comparison");
        free(row); free(col); free(a); free(x); free(initial);
        free(rhs); free(y); free(expected);
      }
  puts("PASS S12-07 diagnostic complete");
  return 0;
}
#endif
