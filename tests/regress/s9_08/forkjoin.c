/* S9-08 card measurement 3 (docs/research/knc-libgomp.md section 4): fork/join of empty
   parallel regions at 60x4 (240 threads), under the wait policy and GOMP_KNC_DELAY of the
   environment; run.sh runs one process per setting, in an order drawn per round.

       forkjoin THREADS LABEL

   A first region checks that the team has THREADS threads.  Timing follows ADR-0010:
   CLOCK_MONOTONIC_RAW makespans of batches of empty regions, a pilot sizing a batch to about
   100 ms, then 3 warm-up and 21 timed batches; every batch is printed, in microseconds per
   region, and the median last.  */
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define WARMUP 3
#define TIMED 21
#define TARGET_NS 100000000.0

static double
now_ns (void)
{
  struct timespec ts;
  clock_gettime (CLOCK_MONOTONIC_RAW, &ts);
  return ts.tv_sec * 1e9 + ts.tv_nsec;
}

static void
batch (long n, int threads)
{
  for (long i = 0; i < n; i++)
    {
#pragma omp parallel num_threads (threads)
      __asm volatile ("" ::: "memory");
    }
}

static int
compare (const void *a, const void *b)
{
  double x = *(const double *) a, y = *(const double *) b;
  return (x > y) - (x < y);
}

int
main (int argc, char **argv)
{
  if (argc != 3)
    {
      fprintf (stderr, "usage: forkjoin THREADS LABEL\n");
      return 2;
    }
  int threads = atoi (argv[1]);
  const char *label = argv[2];
  int team = 0;
#pragma omp parallel num_threads (threads)
#pragma omp single
  team = omp_get_num_threads ();
  if (team != threads)
    {
      printf ("S9-08 forkjoin %s FAIL: team of %d threads, want %d\n", label, team, threads);
      return 1;
    }

  long n = 16;
  for (;;)
    {
      double t0 = now_ns ();
      batch (n, threads);
      double dt = now_ns () - t0;
      if (dt > TARGET_NS / 4)
	{
	  n = (long) (n * TARGET_NS / dt);
	  break;
	}
      n *= 4;
    }

  double t[TIMED];
  for (int b = 0; b < WARMUP + TIMED; b++)
    {
      double t0 = now_ns ();
      batch (n, threads);
      double dt = now_ns () - t0;
      if (b >= WARMUP)
	{
	  t[b - WARMUP] = dt / n / 1e3;
	  printf ("SAMPLE config=%s batch=%d regions=%ld ms=%.3f us_per_region=%.3f\n", label,
		  b - WARMUP, n, dt / 1e6, t[b - WARMUP]);
	}
    }
  qsort (t, TIMED, sizeof t[0], compare);
  printf ("S9-08 forkjoin %s PASS: threads=%d regions_per_batch=%ld median_us_per_region=%.3f "
	  "min=%.3f max=%.3f\n", label, threads, n, t[TIMED / 2], t[0], t[TIMED - 1]);
  return 0;
}
