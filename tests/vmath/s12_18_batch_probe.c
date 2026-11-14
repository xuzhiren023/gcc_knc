/* S12-18: deterministic timing input for the real benchmark controller.
   No card timing or numerical qualification is claimed by this fixture. */
#define _GNU_SOURCE
#include <stdint.h>
#include <time.h>

static uint64_t elapsed_ns;
static int cold_calls;

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
  memset (out, 0, (size_t) n * size);
  elapsed_ns += vector ? (cold_calls-- > 0 ? 20000000 : 5000000) : 4000000;
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
  if (argc != 3)
    return 2;
  int k = atoi (argv[1]);
  if (k < EXP || k > POW)
    return 2;
  cold_calls = atoi (argv[2]);
  cores = workers = 1;
  density = 4;
  rounds = 3;
  batches = 3;
  if (pthread_barrier_init (&barrier, NULL, workers))
    return 2;
  for (int a = 0; a < ARRAYS; ++a)
    {
      arrays[0][a] = calloc (1, set_bytes[0]);
      if (!arrays[0][a])
        return 2;
    }
  int result = measure (k, 0);
  for (int a = 0; a < ARRAYS; ++a)
    free (arrays[0][a]);
  pthread_barrier_destroy (&barrier);
  return result;
}
