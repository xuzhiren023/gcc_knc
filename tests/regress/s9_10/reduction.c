/* S9-10 measurement 6 (docs/research/knc-libgomp.md section 5): the cost of a parallel region
   that ends in a reduction over THREADS threads, by how the reduction is done.

   usage: reduction.mic atomic|lock|padded THREADS [REGIONS]

   atomic  reduction(+:sum), one scalar clause: GCC combines with one atomic update of SUM per
           thread (omp-low.cc lower_reduction_clauses).
   lock    reduction(+:sum, sum2), two clauses: GCC wraps the updates in GOMP_atomic_start/end,
           one global lock.
   padded  by hand: each thread stores its partial in its own 64-byte line, then a barrier, and
           the master sums the lines.

   A batch is REGIONS regions (default 10000).  One warm-up batch, then 5 groups of 5 timed
   batches, CLOCK_MONOTONIC_RAW (ADR-0010 point 1).  Every batch prints a SAMPLE line; the
   result line has the median of the group medians in us per region.  Every region's sum is
   checked.  Placement is libgomp's KNC default (one place per core, spread).  */
#define _GNU_SOURCE
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define GROUPS 5
#define BATCHES 5

struct line
{
  long v;
} __attribute__((aligned (64)));

static struct line part[256];
static int bad;

static double
now_us (void)
{
  struct timespec ts;
  clock_gettime (CLOCK_MONOTONIC_RAW, &ts);
  return ts.tv_sec * 1e6 + ts.tv_nsec / 1e3;
}

/* Thread I adds I + 1 + R % 7, so a region's sum is known.  */
static long
expected (int threads, long r)
{
  return (long) threads * (threads + 1) / 2 + (long) threads * (r % 7);
}

static void
batch (int mode, int threads, long regions)
{
  long r;

  for (r = 0; r < regions; r++)
    {
      long sum = 0, sum2 = 0;

      if (mode == 0)
	{
#pragma omp parallel num_threads(threads) reduction(+:sum)
	  sum += omp_get_thread_num () + 1 + r % 7;
	}
      else if (mode == 1)
	{
#pragma omp parallel num_threads(threads) reduction(+:sum, sum2)
	  {
	    sum += omp_get_thread_num () + 1 + r % 7;
	    sum2 += 1;
	  }
	  if (sum2 != threads)
	    bad++;
	}
      else
	{
#pragma omp parallel num_threads(threads)
	  {
	    int id = omp_get_thread_num ();
	    part[id].v = id + 1 + r % 7;
#pragma omp barrier
#pragma omp master
	    {
	      long s = 0;
	      int i, n = omp_get_num_threads ();
	      for (i = 0; i < n; i++)
		s += part[i].v;
	      sum = s;
	    }
	  }
	}
      if (sum != expected (threads, r))
	bad++;
    }
}

static int
cmp (const void *a, const void *b)
{
  double x = *(const double *) a, y = *(const double *) b;
  return (x > y) - (x < y);
}

int
main (int argc, char **argv)
{
  static const char *const names[] = { "atomic", "lock", "padded" };
  double group_median[GROUPS], sample[BATCHES], median;
  int mode, threads, g, b, got = 0;
  long regions;

  for (mode = 0; mode < 3; mode++)
    if (argc >= 3 && strcmp (argv[1], names[mode]) == 0)
      break;
  threads = argc >= 3 ? atoi (argv[2]) : 0;
  regions = argc >= 4 ? atol (argv[3]) : 10000;
  if (mode == 3 || threads < 1 || threads > 256 || regions < 1)
    {
      fprintf (stderr, "usage: %s atomic|lock|padded THREADS [REGIONS]\n", argv[0]);
      return 2;
    }

#pragma omp parallel num_threads(threads)
#pragma omp master
  got = omp_get_num_threads ();
  if (got != threads)
    {
      printf ("S9-10 reduction %s FAIL threads=%d: got a team of %d\n", names[mode], threads, got);
      return 1;
    }

  batch (mode, threads, regions);
  for (g = 0; g < GROUPS; g++)
    {
      for (b = 0; b < BATCHES; b++)
	{
	  double t0 = now_us ();
	  batch (mode, threads, regions);
	  sample[b] = (now_us () - t0) / regions;
	  printf ("SAMPLE reduction %s threads=%d group=%d batch=%d us_per_region=%.3f\n",
		  names[mode], threads, g, b, sample[b]);
	}
      qsort (sample, BATCHES, sizeof sample[0], cmp);
      group_median[g] = sample[BATCHES / 2];
    }
  qsort (group_median, GROUPS, sizeof group_median[0], cmp);
  median = group_median[GROUPS / 2];
  if (bad)
    {
      printf ("S9-10 reduction %s FAIL threads=%d: %d wrong sums\n", names[mode], threads, bad);
      return 1;
    }
  printf ("S9-10 reduction %s PASS threads=%d regions=%ld median_us=%.3f spread=%.4f\n",
	  names[mode], threads, regions, median,
	  (group_median[GROUPS - 1] - group_median[0]) / median);
  return 0;
}
