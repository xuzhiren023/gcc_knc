/* S9-15 card program: fork/join with serial gaps, to set libgomp's KNC spin time from (best-practice
   review item 3).  Between parallel regions the initial thread computes alone for GAP msec while
   the team's threads wait, spinning for GOMP_SPINCOUNT DELAY periods and then sleeping on a futex;
   the region entry then costs either a spinning thread's notice or a futex wake.

       gapjoin THREADS LABEL GAP_MS...
       gapjoin spincount MSEC DELAY

   The first form runs, for each gap, a warm-up of 3 regions and then about 2 s of regions (at least
   20).  Each region's entry time is the time from the initial thread's last instruction before the
   region to the last thread's first instruction in it; its region time ends after the join.  Per
   gap it prints the median, 10th and 90th percentile and maximum of both in microseconds, and the
   process CPU time over wall time during the gap phase (getrusage): about 1 when the team sleeps
   through the gaps, up to THREADS when it spins through them.  Timing is CLOCK_MONOTONIC_RAW, as
   ADR-0010.

   The second form prints the GOMP_SPINCOUNT that spins MSEC msec in DELAY periods at this card's
   clock (card.h, as libgomp computes its default), so that the runner sets the setting libgomp
   would derive.  */
#include "card.h"

#include <omp.h>
#include <sys/resource.h>
#include <time.h>

#define WARMUP 3
#define PHASE_NS 2e9
#define MIN_REGIONS 20
#define MAX_THREADS 1024

/* One line per thread: the time it entered the region.  */
static struct
{
  double ns;
  char pad[64 - sizeof (double)];
} __attribute__ ((aligned (64))) entered[MAX_THREADS];

static double
now_ns (void)
{
  struct timespec ts;
  clock_gettime (CLOCK_MONOTONIC_RAW, &ts);
  return ts.tv_sec * 1e9 + ts.tv_nsec;
}

static double
cpu_ns (void)
{
  struct rusage ru;
  getrusage (RUSAGE_SELF, &ru);
  return (ru.ru_utime.tv_sec + ru.ru_stime.tv_sec) * 1e9
	 + (ru.ru_utime.tv_usec + ru.ru_stime.tv_usec) * 1e3;
}

/* The serial gap: the initial thread computes alone, as serial code between regions does.  */
static void
gap (double ns)
{
  double end = now_ns () + ns;
  while (now_ns () < end)
    ;
}

/* One region; its entry and region times in microseconds.  */
static void
region (int threads, double *entry, double *whole)
{
  double t0 = now_ns ();
#pragma omp parallel num_threads (threads)
  entered[omp_get_thread_num ()].ns = now_ns ();
  double t1 = now_ns (), last = t0;
  for (int i = 0; i < threads; i++)
    if (entered[i].ns > last)
      last = entered[i].ns;
  *entry = (last - t0) / 1e3;
  *whole = (t1 - t0) / 1e3;
}

static int
compare (const void *a, const void *b)
{
  double x = *(const double *) a, y = *(const double *) b;
  return (x > y) - (x < y);
}

static void
stats (const char *what, double *v, int n, char *out, size_t size)
{
  qsort (v, n, sizeof v[0], compare);
  snprintf (out, size, "%s_median_us=%.1f %s_p10_us=%.1f %s_p90_us=%.1f %s_max_us=%.1f", what, v[n / 2],
	    what, v[n / 10], what, v[n - 1 - n / 10], what, v[n - 1]);
}

int
main (int argc, char **argv)
{
  if (argc == 4 && strcmp (argv[1], "spincount") == 0)
    {
      unsigned int mhz = gomp_knc_read_mhz ("");
      printf ("%llu\n", gomp_knc_spincount (strtoul (argv[2], NULL, 10), mhz,
					    strtoul (argv[3], NULL, 10)));
      return 0;
    }
  if (argc < 4)
    {
      fprintf (stderr, "usage: gapjoin THREADS LABEL GAP_MS... | gapjoin spincount MSEC DELAY\n");
      return 2;
    }
  int threads = atoi (argv[1]);
  const char *label = argv[2];
  if (threads < 1 || threads > MAX_THREADS)
    {
      printf ("S9-15 gapjoin %s FAIL: %d threads, want 1 to %d\n", label, threads, MAX_THREADS);
      return 1;
    }
  int team = 0;
#pragma omp parallel num_threads (threads)
#pragma omp single
  team = omp_get_num_threads ();
  if (team != threads)
    {
      printf ("S9-15 gapjoin %s FAIL: team of %d threads, want %d\n", label, team, threads);
      return 1;
    }

  for (int g = 3; g < argc; g++)
    {
      double gap_ms = atof (argv[g]), entry, whole;
      int n = (int) (PHASE_NS / (gap_ms * 1e6 + 1e5));
      if (n < MIN_REGIONS)
	n = MIN_REGIONS;
      double *e = malloc (n * sizeof *e), *w = malloc (n * sizeof *w);
      if (!e || !w)
	{
	  printf ("S9-15 gapjoin %s FAIL: out of memory\n", label);
	  return 1;
	}
      for (int i = 0; i < WARMUP; i++)
	{
	  gap (gap_ms * 1e6);
	  region (threads, &entry, &whole);
	}
      double c0 = cpu_ns (), t0 = now_ns ();
      for (int i = 0; i < n; i++)
	{
	  gap (gap_ms * 1e6);
	  region (threads, &e[i], &w[i]);
	}
      double busy = (cpu_ns () - c0) / (now_ns () - t0);
      char es[160], ws[160];
      stats ("entry", e, n, es, sizeof es);
      stats ("region", w, n, ws, sizeof ws);
      printf ("S9-15 gapjoin %s PASS: threads=%d gap_ms=%g regions=%d %s %s cpu_per_wall=%.2f\n", label,
	      threads, gap_ms, n, es, ws, busy);
      free (e);
      free (w);
    }
  return 0;
}
