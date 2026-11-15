// S12-31 diagnostic: HPCG 3.1 sparse kernels built several ways, and the cost
// of padding executed before a short inner loop.  Single-core timing.
// Usage: s12-31-bench [nx=104] [samples=5] [microbench rows=100000]
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#ifdef __linux__
#include <sched.h>
#endif
#include "SparseMatrix.hpp"
#include "Vector.hpp"

#ifdef __CYGWIN__
#define ASMABI __attribute__((sysv_abi))
#else
#define ASMABI
#endif

typedef int (*spmv_fn)(const SparseMatrix &, Vector &, Vector &);
typedef int (*symgs_fn)(const SparseMatrix &, const Vector &, Vector &);
typedef void (*mb_fn)(long, long, const double *, const double *, const int *, double *) ASMABI;

extern "C" {
#define X(v) \
  int v##_spmv(const SparseMatrix &, Vector &, Vector &); \
  int v##_symgs(const SparseMatrix &, const Vector &, Vector &);
#include "s12_31_hpcg.inc"
#undef X
#define X(v) void mb_##v(long, long, const double *, const double *, const int *, double *) ASMABI;
#include "s12_31_mb.inc"
#undef X
}

static const struct { const char *name; spmv_fn spmv; symgs_fn symgs; } hpcg[] = {
#define X(v) {#v, v##_spmv, v##_symgs},
#include "s12_31_hpcg.inc"
#undef X
};
static const struct { const char *name; mb_fn fn; } mb[] = {
#define X(v) {#v, mb_##v},
#include "s12_31_mb.inc"
#undef X
};
enum { NH = sizeof hpcg / sizeof hpcg[0], NM = sizeof mb / sizeof mb[0], MAXS = 9 };

static double now() {
  struct timespec t;
  clock_gettime(CLOCK_MONOTONIC, &t);
  return t.tv_sec + 1e-9 * t.tv_nsec;
}

static double median(const double *v, int n) {
  double s[MAXS];
  std::copy(v, v + n, s);
  std::sort(s, s + n);
  return n % 2 ? s[n / 2] : 0.5 * (s[n / 2 - 1] + s[n / 2]);
}

// Same allocation order and contents as GenerateProblem_ref and the serial
// SetupHalo_ref: all index rows, then all value rows, then all global rows.
static void build(SparseMatrix & A, int nx, Vector & b, Vector & x, Vector & xexact) {
  local_int_t n = nx * nx * nx;
  char * nonzerosInRow = new char[n];
  global_int_t ** mtxIndG = new global_int_t*[n];
  local_int_t ** mtxIndL = new local_int_t*[n];
  double ** matrixValues = new double*[n];
  double ** matrixDiagonal = new double*[n];
  InitializeVector(b, n);
  InitializeVector(x, n);
  InitializeVector(xexact, n);
  A.localToGlobalMap.resize(n);
  for (local_int_t i = 0; i < n; ++i) mtxIndL[i] = new local_int_t[27];
  for (local_int_t i = 0; i < n; ++i) matrixValues[i] = new double[27];
  for (local_int_t i = 0; i < n; ++i) mtxIndG[i] = new global_int_t[27];
  local_int_t nnz = 0;
  for (int iz = 0; iz < nx; iz++)
    for (int iy = 0; iy < nx; iy++)
      for (int ix = 0; ix < nx; ix++) {
        local_int_t row = iz * nx * nx + iy * nx + ix;
        A.localToGlobalMap[row] = row;
        char count = 0;
        double * v = matrixValues[row];
        global_int_t * g = mtxIndG[row];
        for (int sz = -1; sz <= 1; sz++)
          if (iz + sz > -1 && iz + sz < nx)
            for (int sy = -1; sy <= 1; sy++)
              if (iy + sy > -1 && iy + sy < nx)
                for (int sx = -1; sx <= 1; sx++)
                  if (ix + sx > -1 && ix + sx < nx) {
                    global_int_t col = row + sz * nx * nx + sy * nx + sx;
                    if (col == row) {
                      matrixDiagonal[row] = v;
                      *v++ = 26.0;
                    } else {
                      *v++ = -1.0;
                    }
                    *g++ = col;
                    count++;
                  }
        nonzerosInRow[row] = count;
        nnz += count;
        b.values[row] = 26.0 - ((double) (count - 1));
        x.values[row] = 0.0;
        xexact.values[row] = 1.0;
      }
  for (local_int_t i = 0; i < n; ++i)
    for (int j = 0; j < nonzerosInRow[i]; j++) mtxIndL[i][j] = (local_int_t) mtxIndG[i][j];
  A.totalNumberOfRows = n;
  A.totalNumberOfNonzeros = nnz;
  A.localNumberOfRows = n;
  A.localNumberOfColumns = n;
  A.localNumberOfNonzeros = nnz;
  A.nonzerosInRow = nonzerosInRow;
  A.mtxIndG = mtxIndG;
  A.mtxIndL = mtxIndL;
  A.matrixValues = matrixValues;
  A.matrixDiagonal = matrixDiagonal;
}

int main(int argc, char ** argv) {
  int nx = argc > 1 ? atoi(argv[1]) : 104;
  int samples = argc > 2 ? atoi(argv[2]) : 5;
  long mbrows = argc > 3 ? atol(argv[3]) : 100000;
  if (nx < 4 || nx > 160 || samples < 1 || samples > MAXS || mbrows < 1) {
    fprintf(stderr, "bad arguments\n");
    return 2;
  }
  int bad = 0;
#ifdef __linux__
  cpu_set_t set;
  if (sched_getaffinity(0, sizeof set, &set)) { perror("sched_getaffinity"); return 2; }
  int first = -1, granted = CPU_COUNT(&set);
  for (int c = 0; c < CPU_SETSIZE && first < 0; c++) if (CPU_ISSET(c, &set)) first = c;
  CPU_ZERO(&set);
  CPU_SET(first, &set);
  if (sched_setaffinity(0, sizeof set, &set)) { perror("sched_setaffinity"); return 2; }
  printf("S12_31 cpu %d granted %d running_on %d\n", first, granted, sched_getcpu());
#endif

  SparseMatrix A;
  InitializeSparseMatrix(A, 0);
  Vector b, x, xexact, y, ref;
  build(A, nx, b, x, xexact);
  local_int_t n = A.localNumberOfRows;
  InitializeVector(y, n);
  InitializeVector(ref, n);
  long oddL = 0, oddV = 0;
  for (local_int_t i = 1; i < n; i++) {
    oddL += (char *) A.mtxIndL[i] - (char *) A.mtxIndL[i - 1] != 128;
    oddV += (char *) A.matrixValues[i] - (char *) A.matrixValues[i - 1] != 224;
  }
  printf("S12_31 layout nx %d rows %d nnz %d index_mod64 %d value_mod64 %d "
         "rows_off_stride index %ld value %ld x_mod64 %d\n",
         nx, n, A.localNumberOfNonzeros, (int) ((unsigned long) A.mtxIndL[0] % 64),
         (int) ((unsigned long) A.matrixValues[0] % 64), oddL, oddV,
         (int) ((unsigned long) x.values % 64));
  for (local_int_t i = 0; i < n; i++) xexact.values[i] = 1.0 + 0.125 * (i % 7);
  fflush(stdout);

  static double t[2][NH][MAXS];
  size_t bytes = sizeof(double) * n;
  for (int k = 0; k < 2; k++) {
    const char * kernel = k ? "symgs" : "spmv";
    int reps = k ? 1 : 2;
    // Reference answer from the first variant (the donor), also warms pages.
    if (k) { memset(x.values, 0, bytes); hpcg[0].symgs(A, b, x); memcpy(ref.values, x.values, bytes); }
    else { hpcg[0].spmv(A, xexact, y); memcpy(ref.values, y.values, bytes); }
    for (int s = 0; s < samples; s++)
      for (int o = 0; o < NH; o++) {
        int v = s % 2 ? NH - 1 - o : o;
        double * out = k ? x.values : y.values;
        memset(out, 0, bytes);
        double t0 = now();
        if (k) hpcg[v].symgs(A, b, x);
        else for (int r = 0; r < reps; r++) hpcg[v].spmv(A, xexact, y);
        t[k][v][s] = now() - t0;
        int same = !memcmp(out, ref.values, bytes);
        bad += !same;
        printf("S12_31 hpcg %s %s s%d %.9f %s\n", kernel, hpcg[v].name, s, t[k][v][s],
               same ? "same" : "MISMATCH");
        fflush(stdout);
      }
    for (int v = 0; v < NH; v++)
      printf("S12_31 hpcg_median %s %s %.9f donor_over_this %.4f\n", kernel, hpcg[v].name,
             median(t[k][v], samples), median(t[k][0], samples) / median(t[k][v], samples));
  }

  // Microbench: one SpMV-shaped row loop of 27 products, data in L1.
  static double mt[NM][MAXS];
  double xs[32], vals[27], want = 0;
  int idx[27];
  for (int j = 0; j < 32; j++) xs[j] = 0.5 + 0.03125 * j;
  for (int j = 0; j < 27; j++) { vals[j] = 1.0 / (1 << (j % 5)); idx[j] = (j * 7) % 32; }
  mb[0].fn(mbrows, 27, xs, vals, idx, &want);
  for (int s = 0; s < samples; s++)
    for (int o = 0; o < NM; o++) {
      int v = s % 2 ? NM - 1 - o : o;
      double got = 0, t0 = now();
      mb[v].fn(mbrows, 27, xs, vals, idx, &got);
      mt[v][s] = (now() - t0) * 1e9 / mbrows;
      if (memcmp(&got, &want, sizeof got)) { bad++; printf("S12_31 mb %s MISMATCH\n", mb[v].name); }
    }
  for (int v = 0; v < NM; v++)
    printf("S12_31 mb_median %s ns_per_row %.3f over_first %+.3f\n", mb[v].name,
           median(mt[v], samples), median(mt[v], samples) - median(mt[0], samples));
  if (bad) { printf("FAIL S12-31 %d mismatches\n", bad); return 1; }
  printf("PASS S12-31 diagnostic complete\n");
  return 0;
}
