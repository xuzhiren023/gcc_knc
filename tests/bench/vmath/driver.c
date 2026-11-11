/* S10-04: paired timing of loops calling libknc_vmath against the same loops on scalar libm.

   usage: vmath-bench.mic [--cores N] [--density D] [--set l2|mem|all] [--kernel K|all]
                          [--rounds R] [--batches B]
   Kernels (kernels.c): expf logf powf exp log pow column.  Workers are pinned one per hardware
   thread, D per core on the first N cores (never cpu 0), and each worker first-touches its own
   page-aligned arrays (1 KiB further per sibling, arrays 512 bytes apart; ADR-0010 amendment 1).
   Working sets per core, counting every sibling's live arrays: l2 = 256 KiB (half the L2),
   mem = 32 MiB.

   For each kernel and set: both builds run once and must agree lane by lane (1 ULP for the six
   functions, the S10-02 limit, with the same NaNs and signed zeros; COLUMN_ULP for the column
   loop, see below), then each build's batch is sized to 50-200 ms, then R rounds each time one
   group of each build, order drawn per round (ADR-0010 amendment 2 point 7).  A group is one
   warm-up and B timed batches; its time is the median batch.  The statistic is the per-round
   ratio of times per element, vec / scl.  Every batch is printed.
   Exit 0 when every check passed and every round ran, 1 on a mismatch, 2 on an error.  */
#define _GNU_SOURCE
#include <math.h>
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define KERNEL_ARGS void *restrict, const void *restrict, const void *restrict, \
  const void *restrict, int
#define DECLARE(name) void name##_vec (KERNEL_ARGS); void name##_scl (KERNEL_ARGS);
DECLARE (expf)
DECLARE (logf)
DECLARE (powf)
DECLARE (exp)
DECLARE (log)
DECLARE (pow)
DECLARE (column)

typedef void (*kernel_fn) (KERNEL_ARGS);

/* The column loop composes powf, logf and expf with divides; the vector build rounds every
   step to float, and the scalar build's x87 code keeps intermediates wider.  A 1-ULP change in
   tl or in the exponent moves the result by a few ULPs, so its lanes are held to this bound
   rather than to one function's limit; the worst lane is always printed.  */
#define COLUMN_ULP 16

enum { EXPF, LOGF, POWF, EXP, LOG, POW, COLUMN, KERNELS };
static const struct
{
  const char *name;
  kernel_fn fn[2];              /* vec, scl */
  int size, inputs;             /* bytes per element, input arrays */
} kernels[KERNELS] = {
  { "expf", { expf_vec, expf_scl }, 4, 1 },
  { "logf", { logf_vec, logf_scl }, 4, 1 },
  { "powf", { powf_vec, powf_scl }, 4, 2 },
  { "exp", { exp_vec, exp_scl }, 8, 1 },
  { "log", { log_vec, log_scl }, 8, 1 },
  { "pow", { pow_vec, pow_scl }, 8, 2 },
  { "column", { column_vec, column_scl }, 4, 3 },
};
static const char *builds[2] = { "vec", "scl" };
static const char *sets[2] = { "l2", "mem" };
static const size_t set_bytes[2] = { 256 << 10, 32 << 20 };     /* per core */

#define MAX_WORKERS 244
#define ARRAYS 5                /* three inputs and one output per build */

static int cores = 60, density = 4, rounds = 7, batches = 5, workers;
static int cpus[MAX_WORKERS], siblings[MAX_WORKERS];
static char *arrays[MAX_WORKERS][ARRAYS];
static size_t capacity;          /* bytes per array */
static pthread_barrier_t barrier;

/* The command every worker runs between two barriers.  */
static volatile int cmd_kernel, cmd_build, cmd_fill, cmd_stop;
static volatile long cmd_reps;
static volatile int cmd_n;

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
  clock_gettime (CLOCK_MONOTONIC_RAW, &t);
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
pin (int cpu)
{
  cpu_set_t mask;
  CPU_ZERO (&mask);
  CPU_SET (cpu, &mask);
  if (sched_setaffinity (0, sizeof mask, &mask) || sched_getcpu () != cpu)
    die ("affinity");
}

/* A value in [low, high) from a per-worker generator.  */
static double
uniform (uint64_t *seed, double low, double high)
{
  *seed = *seed * 6364136223846793005u + 1442695040888963407u;
  return low + (high - low) * ((*seed >> 11) * 0x1p-53);
}

/* Inputs with finite, normal results for every kernel; the column gets profiles of a
   troposphere (pressure, temperature and moisture fall with height).  */
static void
fill (int w, int k, int n)
{
  uint64_t seed = 0x5eed10045eed1004u ^ ((uint64_t) w << 32 | (unsigned) k);
  float *af = (float *) arrays[w][0], *bf = (float *) arrays[w][1], *cf = (float *) arrays[w][2];
  double *ad = (double *) arrays[w][0], *bd = (double *) arrays[w][1];
  for (int i = 0; i < n; i++)
    switch (k)
      {
      case EXPF: af[i] = (float) uniform (&seed, -87, 88); break;
      case LOGF: af[i] = (float) exp2 (uniform (&seed, -125, 127)); break;
      case POWF:
        af[i] = (float) uniform (&seed, 0.01, 20);
        bf[i] = (float) uniform (&seed, -18, 18);
        break;
      case EXP: ad[i] = uniform (&seed, -708, 709); break;
      case LOG: ad[i] = exp2 (uniform (&seed, -1021, 1023)); break;
      case POW:
        ad[i] = uniform (&seed, 0.01, 20);
        bd[i] = uniform (&seed, -150, 150);
        break;
      default:
        {
          double h = uniform (&seed, 0, 1);       /* height, 0 at the ground */
          bf[i] = (float) (101000 - 90000 * h);
          af[i] = (float) (305 - 90 * h + uniform (&seed, -5, 5));
          cf[i] = (float) (0.02 * (1 - h) * (1 - h) * uniform (&seed, 0.2, 1) + 1e-6);
        }
      }
  memset (arrays[w][3], 0, (size_t) n * kernels[k].size);
  memset (arrays[w][4], 0, (size_t) n * kernels[k].size);
}

static void
work (int w)
{
  int k = cmd_kernel, b = cmd_build, n = cmd_n;
  if (cmd_fill)
    {
      fill (w, k, n);
      return;
    }
  kernel_fn fn = kernels[k].fn[b];
  char *const *a = arrays[w];
  for (long r = 0; r < cmd_reps; r++)
    fn (a[3 + b], a[0], a[1], a[2], n);
}

static void *
worker (void *arg)
{
  int w = (int) (intptr_t) arg;
  pin (cpus[w]);
  for (;;)
    {
      sync_workers ();
      if (cmd_stop)
        return NULL;
      work (w);
      sync_workers ();
    }
}

/* Main is worker 0.  Returns the makespan.  */
static double
command (int k, int b, int n, long reps, int fill_only)
{
  cmd_kernel = k, cmd_build = b, cmd_n = n, cmd_reps = reps, cmd_fill = fill_only;
  double start = now ();
  sync_workers ();
  work (0);
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
          siblings[c * density + t] = t;
          printf ("placement worker=%d core=%d cpu=%d\n", c * density + t, c, sibling[c][t]);
        }
    }
}

static void
print_file (const char *label, const char *path)
{
  char line[256] = "unavailable";
  FILE *f = fopen (path, "r");
  if (f)
    {
      if (!fgets (line, sizeof line, f))
        strcpy (line, "unreadable");
      fclose (f);
    }
  line[strcspn (line, "\n")] = 0;
  printf ("clock %s=%s\n", label, line);
}

/* Order the bit patterns as the values are ordered; adjacent values differ by one.  */
static int64_t
order (const char *p, int size)
{
  if (size == 4)
    {
      uint32_t bits;
      memcpy (&bits, p, 4);
      return bits >> 31 ? -(int64_t) (bits & 0x7fffffff) : (int64_t) bits;
    }
  uint64_t bits;
  memcpy (&bits, p, 8);
  return bits >> 63 ? -(int64_t) (bits & INT64_MAX) : (int64_t) bits;
}

/* ULPs between two results; UINT64_MAX when only one is a NaN or zeros differ in sign.  */
static uint64_t
distance (const char *v, const char *s, int size)
{
  double dv = size == 4 ? *(const float *) v : *(const double *) v;
  double ds = size == 4 ? *(const float *) s : *(const double *) s;
  int64_t a = order (v, size), b = order (s, size);
  if (dv != dv || ds != ds)
    return dv != dv && ds != ds ? 0 : UINT64_MAX;
  if (a == b)
    return !signbit (dv) == !signbit (ds) ? 0 : UINT64_MAX;
  return a > b ? (uint64_t) a - (uint64_t) b : (uint64_t) b - (uint64_t) a;
}

static int
check (int k, int set, int n)
{
  int size = kernels[k].size;
  uint64_t worst = 0, limit = k == COLUMN ? COLUMN_ULP : 1;
  long differ = 0;
  int ww = 0, wi = 0;
  for (int w = 0; w < workers; w++)
    for (int i = 0; i < n; i++)
      {
        uint64_t d = distance (arrays[w][3] + (size_t) i * size,
                               arrays[w][4] + (size_t) i * size, size);
        differ += d != 0;
        if (d > worst)
          worst = d, ww = w, wi = i;
      }
  printf ("check kernel=%s set=%s lanes=%ld differ=%ld limit_ulp=%llu worst_ulp=", kernels[k].name,
          sets[set], (long) workers * n, differ, (unsigned long long) limit);
  if (worst == UINT64_MAX)
    printf ("nan_or_zero_sign");
  else
    printf ("%llu", (unsigned long long) worst);
  if (worst)
    {
      printf (" at");
      for (int j = 0; j < kernels[k].inputs; j++)
        printf (" %a", size == 4 ? (double) ((float *) arrays[ww][j])[wi]
                                 : ((double *) arrays[ww][j])[wi]);
      printf (" vec=%a scl=%a", size == 4 ? (double) ((float *) arrays[ww][3])[wi]
                                          : ((double *) arrays[ww][3])[wi],
              size == 4 ? (double) ((float *) arrays[ww][4])[wi] : ((double *) arrays[ww][4])[wi]);
    }
  puts (worst > limit ? " FAIL" : " PASS");
  return worst > limit;
}

static int
by_double (const void *a, const void *b)
{
  double x = *(const double *) a, y = *(const double *) b;
  return (x > y) - (x < y);
}

static double
median (double *v, int count)
{
  qsort (v, count, sizeof v[0], by_double);
  return count % 2 ? v[count / 2] : 0.5 * (v[count / 2 - 1] + v[count / 2]);
}

/* Repetitions that make one batch 50-200 ms, aiming at 100 ms.  */
static long
size_batch (int k, int b, int n)
{
  long reps = 1;
  for (int tries = 0; tries < 8; tries++)
    {
      double t = command (k, b, n, reps, 0);
      if (t >= 0.05 && t <= 0.2)
        break;
      double scale = 0.1 / (t > 1e-6 ? t : 1e-6);
      reps = (long) (reps * scale + 0.5);
      if (reps < 1)
        reps = 1;
    }
  return reps;
}

/* Returns the median batch time of one group.  */
static double
group (int k, int set, int b, int n, long reps, int round)
{
  double t[64];
  command (k, b, n, reps, 0);
  printf ("batches kernel=%s set=%s round=%d build=%s reps=%ld seconds=", kernels[k].name,
          sets[set], round, builds[b], reps);
  for (int i = 0; i < batches; i++)
    {
      t[i] = command (k, b, n, reps, 0);
      printf ("%s%.6f", i ? "," : "", t[i]);
    }
  putchar ('\n');
  return median (t, batches);
}

static int
measure (int k, int set)
{
  int size = kernels[k].size;
  int n = (int) (set_bytes[set] / density / ((kernels[k].inputs + 1) * size));
  n -= n % 16;
  command (k, 0, n, 0, 1);
  command (k, 0, n, 1, 0);
  command (k, 1, n, 1, 0);
  if (check (k, set, n))
    return 1;

  long reps[2];
  double elements[2], ratio[100], batch_med[2][100];
  for (int b = 0; b < 2; b++)
    {
      reps[b] = size_batch (k, b, n);
      elements[b] = (double) reps[b] * n * workers;
    }
  printf ("sizing kernel=%s set=%s n_per_worker=%d bytes_per_worker=%zu reps_vec=%ld "
          "reps_scl=%ld\n", kernels[k].name, sets[set], n,
          (size_t) n * size * (kernels[k].inputs + 1), reps[0], reps[1]);
  for (int r = 0; r < rounds; r++)
    {
      double t[2];
      int first = rand () & 1;
      t[first] = group (k, set, first, n, reps[first], r + 1);
      t[!first] = group (k, set, !first, n, reps[!first], r + 1);
      for (int b = 0; b < 2; b++)
        batch_med[b][r] = t[b];
      ratio[r] = (t[0] / elements[0]) / (t[1] / elements[1]);
      printf ("round kernel=%s set=%s round=%d first=%s ns_per_elem_vec=%.4f ns_per_elem_scl=%.4f "
              "ratio_vec_over_scl=%.4f\n", kernels[k].name, sets[set], r + 1, builds[first],
              1e9 * t[0] * workers / elements[0], 1e9 * t[1] * workers / elements[1], ratio[r]);
    }
  double med_vec = median (batch_med[0], rounds), med_scl = median (batch_med[1], rounds);
  int valid = med_vec >= 0.05 && med_vec <= 0.2 && med_scl >= 0.05 && med_scl <= 0.2;
  double m = median (ratio, rounds);
  printf ("summary kernel=%s set=%s cores=%d threads_per_core=%d rounds=%d "
          "median_ratio_vec_over_scl=%.4f speedup=%.2f min=%.4f max=%.4f batch_ms_vec=%.1f "
          "batch_ms_scl=%.1f batches=%s\n", kernels[k].name, sets[set], cores, density, rounds, m,
          1 / m, ratio[0], ratio[rounds - 1], 1e3 * med_vec, 1e3 * med_scl,
          valid ? "valid" : "INVALID");
  return 0;
}

int
main (int argc, char **argv)
{
  int set_mask = 3, kernel_mask = (1 << KERNELS) - 1;
  for (int i = 1; i + 1 < argc; i += 2)
    {
      const char *opt = argv[i], *val = argv[i + 1];
      if (!strcmp (opt, "--cores")) cores = atoi (val);
      else if (!strcmp (opt, "--density")) density = atoi (val);
      else if (!strcmp (opt, "--rounds")) rounds = atoi (val);
      else if (!strcmp (opt, "--batches")) batches = atoi (val);
      else if (!strcmp (opt, "--set"))
        set_mask = !strcmp (val, "l2") ? 1 : !strcmp (val, "mem") ? 2 : !strcmp (val, "all") ? 3 : 0;
      else if (!strcmp (opt, "--kernel"))
        {
          kernel_mask = !strcmp (val, "all") ? (1 << KERNELS) - 1 : 0;
          for (int k = 0; k < KERNELS; k++)
            if (!strcmp (val, kernels[k].name))
              kernel_mask = 1 << k;
        }
      else
        die ("usage: vmath-bench.mic [--cores N] [--density D] [--set l2|mem|all] "
             "[--kernel K|all] [--rounds R] [--batches B]");
    }
  if (argc % 2 == 0)
    die ("options take one value each");
  if (cores < 1 || cores > 61 || density < 1 || density > 4 || density == 3 || rounds < 1
      || rounds > 100 || batches < 1 || batches > 64 || !set_mask || !kernel_mask)
    die ("cores 1..61, density 1, 2 or 4, rounds 1..100, batches 1..64, a known set and kernel");
  workers = cores * density;
  read_topology ();
  print_file ("source", "/sys/devices/system/clocksource/clocksource0/current_clocksource");
  print_file ("governor", "/sys/devices/system/cpu/cpu1/cpufreq/scaling_governor");

  /* Room for the largest kernel at the largest selected set.  */
  for (int s = 0; s < 2; s++)
    if (set_mask >> s & 1)
      for (int k = 0; k < KERNELS; k++)
        if (kernel_mask >> k & 1)
          {
            size_t bytes = set_bytes[s] / density / (kernels[k].inputs + 1) + 64;
            if (bytes > capacity)
              capacity = bytes;
          }
  if (pthread_barrier_init (&barrier, NULL, workers))
    die ("pthread_barrier_init");
  pin (cpus[0]);
  /* Allocated here, first touched by each worker's own fill.  */
  for (int w = 0; w < workers; w++)
    for (int a = 0; a < ARRAYS; a++)
      {
        void *p;
        size_t skew = (size_t) siblings[w] * 1024 + (size_t) a * 512;
        if (posix_memalign (&p, 4096, capacity + skew))
          die ("posix_memalign");
        arrays[w][a] = (char *) p + skew;
      }
  pthread_t threads[MAX_WORKERS];
  for (int w = 1; w < workers; ++w)
    if (pthread_create (&threads[w], NULL, worker, (void *) (intptr_t) w))
      die ("pthread_create");

  unsigned seed = (unsigned) time (NULL);
  srand (seed);
  printf ("config cores=%d threads_per_core=%d workers=%d rounds=%d batches=%d seed=%u "
          "l2_bytes_per_core=%zu mem_bytes_per_core=%zu\n", cores, density, workers, rounds,
          batches, seed, set_bytes[0], set_bytes[1]);
  int failed = 0;
  for (int s = 0; s < 2; s++)
    for (int k = 0; k < KERNELS; k++)
      if ((set_mask >> s & 1) && (kernel_mask >> k & 1))
        failed |= measure (k, s);
  print_file ("source_end", "/sys/devices/system/clocksource/clocksource0/current_clocksource");
  print_file ("governor_end", "/sys/devices/system/cpu/cpu1/cpufreq/scaling_governor");
  cmd_stop = 1;
  sync_workers ();
  for (int w = 1; w < workers; ++w)
    pthread_join (threads[w], NULL);
  puts (failed ? "S10-04 vmath bench FAIL" : "S10-04 vmath bench PASS");
  return failed;
}
