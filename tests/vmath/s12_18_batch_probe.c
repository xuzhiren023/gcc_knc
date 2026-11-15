/* S12-18: deterministic timing input for the real benchmark controller.
   No card timing or numerical qualification is claimed by this fixture. */
#define _GNU_SOURCE
#include <stdint.h>
#include <time.h>

static uint64_t elapsed_ns;
static int cold_calls;
static int late_transition, vector_calls;
static int base_n;
static int memory_span, next_offset[2], wraps[2];

static int
test_clock_gettime (clockid_t clock, struct timespec *t)
{
  (void) clock;
  t->tv_sec = elapsed_ns / 1000000000;
  t->tv_nsec = elapsed_ns % 1000000000;
  return 0;
}

#define clock_gettime test_clock_gettime
#define main benchmark_main
#include "../bench/vmath/driver.c"
#undef main
#undef clock_gettime

/* The first seven vector invocations take 20 ms; later invocations take
   5 ms. Scalar invocations always take 4 ms. This models a transient during
   calibration followed by steady execution, without depending on host load.
   All output lanes agree so the real check() does not mask the timing bug. */
static void
fake_kernel (void *out, int n, int size, int vector)
{
  if (memory_span && n == base_n)
    {
      int b = !vector;
      int offset = ((char *) out - arrays[0][3 + b]) / size;
      if (offset != next_offset[b])
        die ("memory batches did not advance through the working set");
      next_offset[b] += n;
      if (next_offset[b] == memory_span)
        next_offset[b] = 0, ++wraps[b];
    }
  memset (out, 0, (size_t) n * size);
  if (vector)
    {
      ++vector_calls;
      uint64_t cost = late_transition && vector_calls >= 100 ? 1250000
                      : cold_calls-- > 0 ? 20000000 : 5000000;
      elapsed_ns += cost * n / base_n;
    }
  else
    elapsed_ns += UINT64_C(4000000) * n / base_n;
}

#define FAKE_KERNEL(name, size, build, vector) \
  void name##_##build (void *restrict out, const void *restrict a, \
                       const void *restrict b, const void *restrict c, int n) \
  { \
    (void) a; (void) b; (void) c; \
    fake_kernel (out, n, size, vector); \
  }
#define FAKE_PAIR(name, size) \
  FAKE_KERNEL (name, size, vec, 1) \
  FAKE_KERNEL (name, size, scl, 0)
FAKE_PAIR (expf, 4)
FAKE_PAIR (logf, 4)
FAKE_PAIR (powf, 4)
FAKE_PAIR (exp, 8)
FAKE_PAIR (log, 8)
FAKE_PAIR (pow, 8)
FAKE_PAIR (column, 4)

int
main (int argc, char **argv)
{
  if (argc != 4)
    return 2;
  int k = atoi (argv[1]);
  if (k < EXP || k > POW)
    return 2;
  cold_calls = atoi (argv[2]);
  /* A second scenario changes speed during the first measured group. */
  late_transition = cold_calls == -1;
  cores = workers = 1;
  density = 4;
  rounds = 3;
  batches = 3;
  int set = atoi (argv[3]);
  if (set < 0 || set > 1)
    return 2;
  base_n = set_bytes[0] / density / ((kernels[k].inputs + 1) * kernels[k].size);
  base_n -= base_n % 16;
  if (set)
    {
      memory_span = set_bytes[set] / density / ((kernels[k].inputs + 1) * kernels[k].size);
      memory_span -= memory_span % base_n;
    }
  if (pthread_barrier_init (&barrier, NULL, workers))
    return 2;
  for (int a = 0; a < ARRAYS; ++a)
    {
      arrays[0][a] = calloc (1, set_bytes[set]);
      if (!arrays[0][a])
        return 2;
    }
  int result = measure (k, set);
  if (set && (!wraps[0] || !wraps[1]))
    die ("memory timing did not visit the whole working set");
  for (int a = 0; a < ARRAYS; ++a)
    free (arrays[0][a]);
  pthread_barrier_destroy (&barrier);
  return result;
}
