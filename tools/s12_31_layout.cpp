// S12-31 second diagnostic: HPCG 3.1's own setup and CG in a process built like
// the S11-28 pilot, with the two sparse kernels swapped between this build's
// own code and text pages of the pilot binaries run at their pilot addresses.
// Single-core timing.
// Usage: s12-31-layout-<build> [nx=104] [samples=3] [CG iterations=2]
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <vector>
#include <sys/mman.h>
#ifdef __linux__
#include <sched.h>
#endif
#include "hpcg.hpp"
#include "CG.hpp"
#include "CGData.hpp"
#include "CheckAspectRatio.hpp"
#include "CheckProblem.hpp"
#include "ComputeMG.hpp"
#include "ComputeMG_ref.hpp"
#include "ComputeSPMV.hpp"
#include "ComputeSPMV_ref.hpp"
#include "ComputeSYMGS_ref.hpp"
#include "GenerateCoarseProblem.hpp"
#include "GenerateGeometry.hpp"
#include "GenerateProblem.hpp"
#include "Geometry.hpp"
#include "MGData.hpp"
#include "SetupHalo.hpp"
#include "SparseMatrix.hpp"
#include "Vector.hpp"

#ifdef __CYGWIN__
#define ASMABI __attribute__((sysv_abi))
#else
#define ASMABI
#endif

typedef int (*spmv_image)(const SparseMatrix &, Vector &, Vector &) ASMABI;
typedef int (*symgs_image)(const SparseMatrix &, const Vector &, Vector &) ASMABI;

// This build's own kernels: HPCG's two _ref sources compiled under these names.
int own_spmv(const SparseMatrix &, Vector &, Vector &);
int own_symgs(const SparseMatrix &, const Vector &, Vector &);

#include "s12_31_images.inc"
struct Image { const char * name; unsigned long base, spmv, symgs; const unsigned char * bytes; unsigned long size; };
static const Image images[] = {
#define X(n, base, spmv, symgs) {#n, base, spmv, symgs, image_##n, sizeof image_##n},
  S12_31_IMAGES
#undef X
};
enum { NI = sizeof images / sizeof images[0], NV = NI + 1, MAXS = 9, NT = 4 };

static unsigned char * pages[NI];  // where image i runs; images at one address share pages
static int shown[NI];              // which image those pages hold now
static spmv_image use_spmv;        // null: this build's own
static symgs_image use_symgs;
static double spent[NT];           // wall seconds: CG's SpMV, MG, every SpMV, every SymGS
static const char * const spent_name[NT] = {"spmv", "mg", "spmv_all", "symgs_all"};

static double now() {
  struct timespec t;
  clock_gettime(CLOCK_MONOTONIC, &t);
  return t.tv_sec + 1e-9 * t.tv_nsec;
}

// ComputeMG_ref calls the _ref kernels directly, so the switch sits here.
int ComputeSPMV_ref(const SparseMatrix & A, Vector & x, Vector & y) {
  double t = now();
  int e = use_spmv ? use_spmv(A, x, y) : own_spmv(A, x, y);
  spent[2] += now() - t;
  return e;
}

int ComputeSYMGS_ref(const SparseMatrix & A, const Vector & r, Vector & x) {
  double t = now();
  int e = use_symgs ? use_symgs(A, r, x) : own_symgs(A, r, x);
  spent[3] += now() - t;
  return e;
}

// HPCG's ComputeSPMV.cpp and ComputeMG.cpp with a wall clock around them (the
// pilot's serial timers are tick-counted CPU time, too coarse for short samples).
int ComputeSPMV(const SparseMatrix & A, Vector & x, Vector & y) {
  A.isSpmvOptimized = false;
  double t = now();
  int e = ComputeSPMV_ref(A, x, y);
  spent[0] += now() - t;
  return e;
}

int ComputeMG(const SparseMatrix & A, const Vector & r, Vector & x) {
  A.isMgOptimized = false;
  double t = now();
  int e = ComputeMG_ref(A, r, x);
  spent[1] += now() - t;
  return e;
}

static int home(int i) {
  int j = 0;
  while (images[j].base != images[i].base) j++;
  return j;
}

static const char * name_of(int v) { return v ? images[v - 1].name : "own"; }

static void choose(int v) {
  use_spmv = 0;
  use_symgs = 0;
  if (!v) return;
  const Image & m = images[v - 1];
  int h = home(v - 1);
  if (shown[h] != v - 1) {
    memcpy(pages[h], m.bytes, m.size);
    shown[h] = v - 1;
  }
  use_spmv = (spmv_image) (unsigned long) (pages[h] + (m.spmv - m.base));
  use_symgs = (symgs_image) (unsigned long) (pages[h] + (m.symgs - m.base));
}

static double median(const double * v, int n) {
  double s[MAXS];
  std::copy(v, v + n, s);
  std::sort(s, s + n);
  return n % 2 ? s[n / 2] : 0.5 * (s[n / 2 - 1] + s[n / 2]);
}

static void where(int level, const char * name, const void * p) {
  unsigned long a = (unsigned long) p;
  printf("S12_31L layout level %d %s %#lx page_mod16 %lu page_offset %lu\n", level, name, a,
         (a >> 12) % 16, a % 4096);
}

int main(int argc, char ** argv) {
  int n1 = argc > 1 ? atoi(argv[1]) : 104;
  int samples = argc > 2 ? atoi(argv[2]) : 3;
  int iterations = argc > 3 ? atoi(argv[3]) : 2;
  if (n1 < 16 || n1 > 160 || n1 % 8 || samples < 1 || samples > MAXS || iterations < 1) {
    fprintf(stderr, "bad arguments\n");
    return 2;
  }
#ifdef __linux__
  cpu_set_t set;
  if (sched_getaffinity(0, sizeof set, &set)) { perror("sched_getaffinity"); return 2; }
  int first = -1, granted = CPU_COUNT(&set);
  for (int c = 0; c < CPU_SETSIZE && first < 0; c++) if (CPU_ISSET(c, &set)) first = c;
  CPU_ZERO(&set);
  CPU_SET(first, &set);
  if (sched_setaffinity(0, sizeof set, &set)) { perror("sched_setaffinity"); return 2; }
  printf("S12_31L cpu %d granted %d running_on %d\n", first, granted, sched_getcpu());
#endif

  // The pilot pages, before anything else can take their addresses.
  for (int i = 0; i < NI; i++) {
    int h = home(i);
    if (h == i) {
#ifdef S12_31_RELOCATE
      void * want = 0;
#else
      void * want = (void *) images[i].base;
#endif
      void * got = mmap(want, images[i].size, PROT_READ | PROT_WRITE | PROT_EXEC,
                        MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
      if (got == MAP_FAILED || (want && got != want)) {
        printf("FAIL S12-31 cannot place %s at %#lx\n", images[i].name, images[i].base);
        return 1;
      }
      pages[i] = (unsigned char *) got;
      shown[i] = -1;
    } else if (images[i].size != images[h].size) {
      printf("FAIL S12-31 %s and %s differ in size\n", images[i].name, images[h].name);
      return 1;
    }
    pages[i] = pages[h];
    printf("S12_31L code %s pages %#lx spmv %#lx symgs %#lx\n", images[i].name,
           (unsigned long) pages[i], (unsigned long) pages[i] + images[i].spmv - images[i].base,
           (unsigned long) pages[i] + images[i].symgs - images[i].base);
  }
  printf("S12_31L code own spmv %#lx symgs %#lx\n", (unsigned long) &own_spmv, (unsigned long) &own_symgs);

  // HPCG's main.cpp, in its order, up to the first timed call.
  char a0[] = "s12-31-layout", a1[32], a2[32], a3[32];
  sprintf(a1, "--nx=%d", n1);
  sprintf(a2, "--ny=%d", n1);
  sprintf(a3, "--nz=%d", n1);
  char * fake[] = {a0, a1, a2, a3, 0};
  char ** fake_argv = fake;
  int fake_argc = 4;
  HPCG_Params params;
  HPCG_Init(&fake_argc, &fake_argv, params);
  int size = params.comm_size, rank = params.comm_rank;
  local_int_t nx = (local_int_t) params.nx, ny = (local_int_t) params.ny, nz = (local_int_t) params.nz;
  if (CheckAspectRatio(0.125, nx, ny, nz, "local problem", rank == 0)) return 2;
  Geometry * geom = new Geometry;
  GenerateGeometry(size, rank, params.numThreads, params.pz, params.zl, params.zu, nx, ny, nz,
                   params.npx, params.npy, params.npz, geom);
  if (CheckAspectRatio(0.125, geom->npx, geom->npy, geom->npz, "process grid", rank == 0)) return 2;
  std::vector< double > times(10, 0.0);
  double setup = now();
  SparseMatrix A;
  InitializeSparseMatrix(A, geom);
  Vector b, x, xexact;
  GenerateProblem(A, &b, &x, &xexact);
  SetupHalo(A);
  int numberOfMgLevels = 4;
  SparseMatrix * curLevelMatrix = &A;
  for (int level = 1; level < numberOfMgLevels; ++level) {
    GenerateCoarseProblem(*curLevelMatrix);
    curLevelMatrix = curLevelMatrix->Ac;
  }
  setup = now() - setup;
  curLevelMatrix = &A;
  Vector * curb = &b;
  Vector * curx = &x;
  Vector * curxexact = &xexact;
  for (int level = 0; level < numberOfMgLevels; ++level) {
    CheckProblem(*curLevelMatrix, curb, curx, curxexact);
    curLevelMatrix = curLevelMatrix->Ac;
    curb = 0;
    curx = 0;
    curxexact = 0;
  }
  CGData data;
  InitializeSparseCGData(A, data);
  local_int_t nrow = A.localNumberOfRows;
  local_int_t ncol = A.localNumberOfColumns;
  Vector x_overlap, b_computed;
  InitializeVector(x_overlap, ncol);
  InitializeVector(b_computed, nrow);
  FillRandomVector(x_overlap);

  printf("S12_31L build %s cplusplus %ld map_bytes %d nx %d rows %d setup_seconds %.3f\n", S12_31_BUILD,
         (long) __cplusplus, (int) sizeof A.globalToLocalMap, (int) nx, (int) nrow, setup);
  where(0, "b", b.values);
  where(0, "x", x.values);
  where(0, "r", data.r.values);
  where(0, "z", data.z.values);
  where(0, "p", data.p.values);
  where(0, "Ap", data.Ap.values);
  int level = 0;
  for (const SparseMatrix * M = &A; M; M = M->Ac, level++) {
    where(level, "nonzerosInRow", M->nonzerosInRow);
    where(level, "mtxIndL", M->mtxIndL);
    where(level, "matrixValues", M->matrixValues);
    where(level, "matrixDiagonal", M->matrixDiagonal);
    where(level, "index_row0", M->mtxIndL[0]);
    where(level, "value_row0", M->matrixValues[0]);
    if (M->mgData) {
      where(level, "Axf", M->mgData->Axf->values);
      where(level, "rc", M->mgData->rc->values);
      where(level, "xc", M->mgData->xc->values);
    }
  }
  fflush(stdout);

  static double t[NT][NV][MAXS];
  Vector ref;
  InitializeVector(ref, nrow);
  size_t bytes = sizeof(double) * nrow;
  int bad = 0;
  for (int s = 0; s < samples; s++)
    for (int o = 0; o < NV; o++) {
      int v = s % 2 ? NV - 1 - o : o;
      choose(v);
      ZeroVector(x);
      for (int k = 0; k < NT; k++) spent[k] = 0;
      int niters = 0;
      double normr = 0, normr0 = 0;
      int e = CG(A, data, b, x, iterations, 0.0, niters, normr, normr0, &times[0], true);
      if (!s && !o) memcpy(ref.values, x.values, bytes);
      int same = !e && niters == iterations && !memcmp(x.values, ref.values, bytes);
      bad += !same;
      printf("S12_31L cg %s s%d", name_of(v), s);
      for (int k = 0; k < NT; k++) {
        t[k][v][s] = spent[k];
        printf(" %s %.6f", spent_name[k], spent[k]);
      }
      printf(" %s\n", same ? "same" : "MISMATCH");
      fflush(stdout);
    }
  // Every time is reported against the donor's pilot code in this process.
  for (int v = 0; v < NV; v++) {
    printf("S12_31L median %s", name_of(v));
    for (int k = 0; k < NT; k++)
      printf(" %s %.6f %.4f", spent_name[k], median(t[k][v], samples),
             median(t[k][1], samples) / median(t[k][v], samples));
    printf("\n");
  }
  HPCG_Finalize();
  if (bad) { printf("FAIL S12-31 %d mismatches\n", bad); return 1; }
  printf("PASS S12-31 layout diagnostic complete\n");
  return 0;
}
