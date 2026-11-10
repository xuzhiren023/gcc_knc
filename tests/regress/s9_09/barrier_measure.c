/* S9-09 card measurements 2, 4 and 5 of docs/research/knc-libgomp.md section 4, for the team
   barrier.  tools/s9_09_checks.py build links this file twice, with the KNC barrier in per-core
   groups and with the one-level Linux barrier (-DGOMP_KNC_FLAT_BARRIER); run.sh runs one process
   per barrier and setting, in an order drawn per round.

       barrier_measure barrier THREADS LABEL
           empty `#pragma omp barrier's in one team, microseconds per barrier; at least 100000
           timed barriers.
       barrier_measure fanout THREADS LABEL [SETTLE_US]
           release fan-out: one thread, a different one each round, arrives SETTLE_US (2000) after
           the others, which spin or sleep as OMP_WAIT_POLICY says; the time from just before its
           arrival to the last thread leaving, and to the median thread.
       barrier_measure imbalance THREADS LABEL
           each round every thread does one unit of work and one thread, a different one each
           round, two, then a barrier; microseconds per round, and the two-unit thread's first unit
           (the others working) and second (the others waiting in the barrier).

   A first region checks that the team has THREADS threads.  Timing follows ADR-0010:
   CLOCK_MONOTONIC_RAW makespans, a pilot sizing a batch to about 100 ms, then 3 warm-up and 21 or
   more timed batches; every sample is printed, and the median last as median_us.  */
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define WARMUP 3
#define TIMED 21
#define TARGET_NS 100000000.0
#define MAX_THREADS 256
#define FANOUT_ROUNDS 101

static struct { double t; unsigned long x; char pad[48]; } slot[MAX_THREADS] __attribute__((aligned (64)));
static long work_iters = 20000;	/* One unit of work.  */
static long heavy_base;		/* Rounds so far: who does two units.  */
static double heavy_ns[2];	/* The two-unit thread's first and second unit, summed over a batch.  */

static double
now_ns (void)
{
  struct timespec ts;
  clock_gettime (CLOCK_MONOTONIC_RAW, &ts);
  return ts.tv_sec * 1e9 + ts.tv_nsec;
}

static int
compare (const void *a, const void *b)
{
  double x = *(const double *) a, y = *(const double *) b;
  return (x > y) - (x < y);
}

static void
barrier_batch (long n, int threads)
{
#pragma omp parallel num_threads (threads)
  for (long i = 0; i < n; i++)
    {
#pragma omp barrier
    }
}

static unsigned long __attribute__((noinline))
work (unsigned long x, long n)
{
  for (long i = 0; i < n; i++)
    {
      x ^= x << 13;
      x ^= x >> 7;
      x ^= x << 17;
    }
  return x;
}

static void
imbalance_batch (long n, int threads)
{
  double first = 0, second = 0;
  long base = heavy_base;
#pragma omp parallel num_threads (threads)
  {
    int id = omp_get_thread_num ();
    unsigned long x = id + 1;
    for (long r = 0; r < n; r++)
      {
	if (id == (base + r) % threads)
	  {
	    /* Rounds are a barrier apart, so one thread at a time writes these.  */
	    double t0 = now_ns ();
	    x = work (x, work_iters);
	    double t1 = now_ns ();
	    x = work (x, work_iters);
	    first += t1 - t0;
	    second += now_ns () - t1;
	  }
	else
	  x = work (x, work_iters);
#pragma omp barrier
      }
    slot[id].x = x;
  }
  heavy_base = base + n;
  heavy_ns[0] = first;
  heavy_ns[1] = second;
}

/* Measurements 2 and 5: batches of N calls of BATCH's unit.  */
static int
batches (const char *mode, void (*batch) (long, int), int threads, const char *label)
{
  int imbalance = batch == imbalance_batch;
  long n = 16;
  for (int sized = 0;;)
    {
      double t0 = now_ns ();
      batch (n, threads);
      double dt = now_ns () - t0;
      if (imbalance && sized++ < 2)
	/* Size a round to about 2 ms first: one unit is then about 1 ms.  */
	work_iters = work_iters * 2e6 / (dt / n) + 100;
      else if (dt > TARGET_NS / 4)
	{
	  n = (long) (n * TARGET_NS / dt) + 1;
	  break;
	}
      else
	n *= 4;
    }

  int timed = imbalance || 100000 / n < TIMED ? TIMED : 100000 / n + 1;
  double *t = malloc (timed * sizeof *t), h[2][TIMED];
  for (int b = 0; b < WARMUP + timed; b++)
    {
      double t0 = now_ns ();
      batch (n, threads);
      double dt = now_ns () - t0;
      if (b < WARMUP)
	continue;
      t[b - WARMUP] = dt / n / 1e3;
      printf ("SAMPLE config=%s batch=%d n=%ld ms=%.3f us=%.3f", label, b - WARMUP, n, dt / 1e6, t[b - WARMUP]);
      if (imbalance)
	{
	  h[0][b - WARMUP] = heavy_ns[0] / n / 1e3;
	  h[1][b - WARMUP] = heavy_ns[1] / n / 1e3;
	  printf (" first_unit_us=%.3f second_unit_us=%.3f", h[0][b - WARMUP], h[1][b - WARMUP]);
	}
      putchar ('\n');
    }
  qsort (t, timed, sizeof t[0], compare);
  printf ("S9-09 %s %s PASS: threads=%d n_per_batch=%ld batches=%d median_us=%.3f min=%.3f max=%.3f",
	  mode, label, threads, n, timed, t[timed / 2], t[0], t[timed - 1]);
  if (imbalance)
    {
      qsort (h[0], TIMED, sizeof h[0][0], compare);
      qsort (h[1], TIMED, sizeof h[1][0], compare);
      printf (" work_iters=%ld first_unit_median_us=%.3f second_unit_median_us=%.3f second/first=%.4f",
	      work_iters, h[0][TIMED / 2], h[1][TIMED / 2], h[1][TIMED / 2] / h[0][TIMED / 2]);
    }
  putchar ('\n');
  return 0;
}

/* Measurement 4.  */
static int
fanout (int threads, const char *label, double settle_ns)
{
  static double last[FANOUT_ROUNDS], mid[FANOUT_ROUNDS];
  double t0 = 0;
#pragma omp parallel num_threads (threads)
  {
    int id = omp_get_thread_num ();
    for (int r = 0; r < WARMUP + FANOUT_ROUNDS; r++)
      {
	if (id == r % threads)
	  {
	    /* The others went from the last round straight into the barrier below.  */
	    double start = now_ns ();
	    while (now_ns () - start < settle_ns)
	      continue;
	    t0 = now_ns ();
	  }
#pragma omp barrier
	slot[id].t = now_ns ();
#pragma omp barrier
#pragma omp single
	if (r >= WARMUP)
	  {
	    double d[MAX_THREADS];
	    for (int i = 0; i < threads; i++)
	      d[i] = (slot[i].t - t0) / 1e3;
	    qsort (d, threads, sizeof d[0], compare);
	    last[r - WARMUP] = d[threads - 1];
	    mid[r - WARMUP] = d[threads / 2];
	    printf ("SAMPLE config=%s round=%d late=%d last_us=%.3f median_thread_us=%.3f\n", label,
		    r - WARMUP, r % threads, d[threads - 1], d[threads / 2]);
	  }
      }
  }
  qsort (last, FANOUT_ROUNDS, sizeof last[0], compare);
  qsort (mid, FANOUT_ROUNDS, sizeof mid[0], compare);
  printf ("S9-09 fanout %s PASS: threads=%d rounds=%d settle_us=%.0f median_us=%.3f min=%.3f max=%.3f "
	  "median_thread_median_us=%.3f\n", label, threads, FANOUT_ROUNDS, settle_ns / 1e3,
	  last[FANOUT_ROUNDS / 2], last[0], last[FANOUT_ROUNDS - 1], mid[FANOUT_ROUNDS / 2]);
  return 0;
}

int
main (int argc, char **argv)
{
  if (argc < 4)
    {
      fprintf (stderr, "usage: barrier_measure barrier|fanout|imbalance THREADS LABEL [SETTLE_US]\n");
      return 2;
    }
  const char *mode = argv[1], *label = argv[3];
  int threads = atoi (argv[2]), team = 0;
#pragma omp parallel num_threads (threads)
#pragma omp single
  team = omp_get_num_threads ();
  if (team != threads || threads > MAX_THREADS)
    {
      printf ("S9-09 %s %s FAIL: team of %d threads, want %d\n", mode, label, team, threads);
      return 1;
    }
  if (!strcmp (mode, "barrier"))
    return batches (mode, barrier_batch, threads, label);
  if (!strcmp (mode, "imbalance"))
    return batches (mode, imbalance_batch, threads, label);
  if (!strcmp (mode, "fanout"))
    return fanout (threads, label, argc > 4 ? atof (argv[4]) * 1e3 : 2e6);
  return 2;
}
