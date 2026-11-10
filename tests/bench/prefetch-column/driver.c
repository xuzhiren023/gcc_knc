/* S8-11: paired timing of the WRF-shaped column loop with and without compiler prefetch.

   usage: column.mic [--cores N] [--density D] [--rounds R] [--sweeps S]
   Workers are pinned one per hardware thread, D per core on the first N cores (never cpu 0).
   Each round times one group of S sweeps of each build, order drawn per round (ADR-0010
   amendment 2 point 7), and prints T_pf / T_nopf.  Both builds and a scalar reference
   (-fno-tree-vectorize -ffp-contract=off) must give bitwise identical output first.
   Exit 0 when the check passed and every round ran, 1 on a mismatch, 2 on an error.  */
#define _GNU_SOURCE
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "column.h"

#define NJ 64                                   /* j planes */
#define CHUNKS (COLUMN_LD / COLUMN_NI)          /* 34 rows of 8 floats per k level */
#define ITEMS (NJ * CHUNKS)
#define PLANE ((size_t) COLUMN_NK * COLUMN_LD)
#define ARRAY_FLOATS (NJ * PLANE + 4096)        /* slack: prefetches past the end */

typedef void (*column_fn) (COLUMN_ARGS (COLUMN_IN));
static column_fn builds[3] = { column_nopf, column_pf, column_ref };
static const char *names[3] = { "nopf", "pf", "ref" };

static float *arrays[COLUMN_NIN + 1];           /* [1..28] are read */
static float *outputs[3];
static int cores = 60, density = 4, rounds = 7, sweeps = 20, workers;
static int cpus[244];
static pthread_barrier_t barrier;
static volatile int command;                    /* build to run, -1 to stop */
static volatile float *command_out;

static void
die (const char *what)
{
  fprintf (stderr, "error: %s\n", what);
  exit (2);
}

static double
now (void)
{
  struct timespec t;
  clock_gettime (CLOCK_MONOTONIC, &t);
  return t.tv_sec + 1e-9 * t.tv_nsec;
}

static void
sync_workers (void)
{
  int rc = pthread_barrier_wait (&barrier);
  if (rc && rc != PTHREAD_BARRIER_SERIAL_THREAD)
    die ("pthread_barrier_wait");
}

static void
run_items (column_fn fn, float *out, int first, int last)
{
  for (int item = first; item < last; ++item)
    {
      size_t at = (size_t) (item / CHUNKS) * PLANE + (size_t) (item % CHUNKS) * COLUMN_NI;
      float *const *a = arrays;
      fn (out + at, a[1] + at, a[2] + at, a[3] + at, a[4] + at, a[5] + at, a[6] + at,
          a[7] + at, a[8] + at, a[9] + at, a[10] + at, a[11] + at, a[12] + at, a[13] + at,
          a[14] + at, a[15] + at, a[16] + at, a[17] + at, a[18] + at, a[19] + at, a[20] + at,
          a[21] + at, a[22] + at, a[23] + at, a[24] + at, a[25] + at, a[26] + at, a[27] + at,
          a[28] + at, 0.5f);
    }
}

static void
pin (int cpu)
{
  cpu_set_t mask;
  CPU_ZERO (&mask);
  CPU_SET (cpu, &mask);
  if (sched_setaffinity (0, sizeof mask, &mask) || sched_getcpu () != cpu)
    die ("affinity");
}

static void *
worker (void *arg)
{
  int id = (int) (intptr_t) arg;
  int first = (int) ((long) ITEMS * id / workers), last = (int) ((long) ITEMS * (id + 1) / workers);
  pin (cpus[id]);
  for (;;)
    {
      sync_workers ();
      int b = command;
      if (b < 0)
        return NULL;
      float *out = (float *) command_out;
      for (int s = 0; s < (b == 2 ? 1 : sweeps); ++s)
        run_items (builds[b], out, first, last);
      sync_workers ();
    }
}

/* Main is worker 0.  */
static double
timed (int b, float *out)
{
  command = b;
  command_out = out;
  int first = 0, last = (int) ((long) ITEMS / workers);
  double start = now ();
  sync_workers ();
  for (int s = 0; s < (b == 2 ? 1 : sweeps); ++s)
    run_items (builds[b], out, first, last);
  sync_workers ();
  return now () - start;
}

static void
read_topology (void)
{
  static int sibling[61][4], count[61];
  FILE *f = fopen ("/proc/cpuinfo", "r");
  char line[512];
  int cpu = -1, core;
  if (!f)
    die ("/proc/cpuinfo");
  while (fgets (line, sizeof line, f))
    if (sscanf (line, "processor : %d", &cpu) == 1)
      ;
    else if (sscanf (line, "core id : %d", &core) == 1 && cpu > 0 && core >= 0 && core < 61
             && count[core] < 4)
      sibling[core][count[core]++] = cpu;
  fclose (f);
  for (int c = 0; c < cores; ++c)
    {
      if (count[c] != 4)
        die ("expected four hardware threads on each selected core");
      for (int t = 0; t < density; ++t)
        {
          cpus[c * density + t] = sibling[c][t];
          printf ("placement worker=%d core=%d cpu=%d\n", c * density + t, c, sibling[c][t]);
        }
    }
}

static float *
allocate (int m)
{
  void *p;
  /* Stagger the arrays by lines so that 29 streams do not share one L1 set.  */
  size_t skew = (size_t) (m * 3 % 64) * 64;
  if (posix_memalign (&p, 4096, ARRAY_FLOATS * sizeof (float) + skew))
    die ("posix_memalign");
  return (float *) ((char *) p + skew);
}

static int
compare (const char *a)
{
  for (int b = 0; b < 2; ++b)
    if (memcmp (outputs[b], outputs[2], ARRAY_FLOATS * sizeof (float)))
      {
        printf ("correctness build=%s mismatch against ref\n", names[b]);
        return 1;
      }
  printf ("correctness %s: nopf, pf and ref bitwise identical\n", a);
  return 0;
}

static int
by_double (const void *a, const void *b)
{
  double x = *(const double *) a, y = *(const double *) b;
  return (x > y) - (x < y);
}

int
main (int argc, char **argv)
{
  for (int i = 1; i + 1 < argc; i += 2)
    {
      int v = atoi (argv[i + 1]);
      if (!strcmp (argv[i], "--cores")) cores = v;
      else if (!strcmp (argv[i], "--density")) density = v;
      else if (!strcmp (argv[i], "--rounds")) rounds = v;
      else if (!strcmp (argv[i], "--sweeps")) sweeps = v;
      else die ("usage: column.mic [--cores N] [--density D] [--rounds R] [--sweeps S]");
    }
  if (cores < 1 || cores > 61 || density < 1 || density > 4 || rounds < 1 || rounds > 100
      || sweeps < 1)
    die ("cores 1..61, density 1..4, rounds 1..100, sweeps >= 1");
  workers = cores * density;
  read_topology ();
  for (int m = 1; m <= COLUMN_NIN; ++m)
    {
      arrays[m] = allocate (m);
      for (size_t x = 0; x < ARRAY_FLOATS; ++x)
        arrays[m][x] = (float) ((x * 2654435761u + m * 40503u) % 1000003u) * 0x1p-20f;
    }
  for (int b = 0; b < 3; ++b)
    {
      outputs[b] = allocate (b);
      memset (outputs[b], 0, ARRAY_FLOATS * sizeof (float));
    }

  if (pthread_barrier_init (&barrier, NULL, workers))
    die ("pthread_barrier_init");
  pin (cpus[0]);
  pthread_t threads[244];
  for (int w = 1; w < workers; ++w)
    if (pthread_create (&threads[w], NULL, worker, (void *) (intptr_t) w))
      die ("pthread_create");

  /* Correctness first, then one warm-up group of each build.  */
  for (int b = 0; b < 3; ++b)
    timed (b, outputs[b]);
  if (compare ("before timing"))
    return 1;

  double bytes = (double) sweeps * ITEMS * COLUMN_NK * COLUMN_NI * sizeof (float)
                 * (COLUMN_NIN + 1);
  double ratio[100];
  unsigned seed = (unsigned) time (NULL);
  printf ("config cores=%d threads_per_core=%d workers=%d rounds=%d sweeps=%d "
          "bytes_per_group=%.0f arrays=%d k_trips=%d step_bytes=%d row_floats=%d seed=%u\n",
          cores, density, workers, rounds, sweeps, bytes, COLUMN_NIN + 1, COLUMN_NK,
          (int) (COLUMN_LD * sizeof (float)), COLUMN_NI, seed);
  srand (seed);
  for (int r = 0; r < rounds; ++r)
    {
      double t[2];
      int firstb = rand () & 1;
      t[firstb] = timed (firstb, outputs[firstb]);
      t[!firstb] = timed (!firstb, outputs[!firstb]);
      ratio[r] = t[1] / t[0];
      printf ("round %d first=%s t_nopf=%.6f t_pf=%.6f gbs_nopf=%.2f gbs_pf=%.2f "
              "ratio_pf_over_nopf=%.4f\n", r + 1, names[firstb], t[0], t[1], bytes / t[0] / 1e9,
              bytes / t[1] / 1e9, ratio[r]);
    }
  if (compare ("after timing"))
    return 1;
  command = -1;
  sync_workers ();
  for (int w = 1; w < workers; ++w)
    pthread_join (threads[w], NULL);
  qsort (ratio, rounds, sizeof ratio[0], by_double);
  printf ("summary cores=%d threads_per_core=%d rounds=%d median_ratio_pf_over_nopf=%.4f "
          "min=%.4f max=%.4f\n", cores, density, rounds,
          rounds % 2 ? ratio[rounds / 2] : 0.5 * (ratio[rounds / 2 - 1] + ratio[rounds / 2]),
          ratio[0], ratio[rounds - 1]);
  return 0;
}
