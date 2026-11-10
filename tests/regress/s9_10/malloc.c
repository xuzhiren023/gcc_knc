/* S9-10 measurement 7 (docs/research/knc-libgomp.md section 6): what glibc's per-thread malloc
   arenas cost in address space and time with THREADS OpenMP threads.

   usage: malloc.mic THREADS [ROUNDS]

   Each thread does ROUNDS (default 100000) malloc, write and free of 1 KiB.  The run.sh caller
   sets MALLOC_ARENA_MAX (unset, 60, 8, 1).  Prints the wall time (CLOCK_MONOTONIC_RAW) and
   VmPeak, VmHWM and VmRSS from /proc/self/status.  A malloc that fails is counted, not fatal,
   so a run under an address-space limit reports how far it got; a thread libgomp cannot create
   ends the program in libgomp.  */
#define _GNU_SOURCE
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static double
now_s (void)
{
  struct timespec ts;
  clock_gettime (CLOCK_MONOTONIC_RAW, &ts);
  return ts.tv_sec + ts.tv_nsec / 1e9;
}

/* The NAME line of /proc/self/status, as "NAME: VALUE kB" without the padding.  */
static void
status (const char *name, char *out, size_t size)
{
  char line[256];
  size_t len = strlen (name);
  FILE *f = fopen ("/proc/self/status", "r");

  snprintf (out, size, "%s=?", name);
  if (f == NULL)
    return;
  while (fgets (line, sizeof line, f))
    if (strncmp (line, name, len) == 0 && line[len] == ':')
      {
	char *v = line + len + 1;
	v += strspn (v, " \t");
	v[strcspn (v, " \t\n")] = '\0';
	snprintf (out, size, "%s=%skB", name, v);
	break;
      }
  fclose (f);
}

int
main (int argc, char **argv)
{
  const char *arenas = getenv ("MALLOC_ARENA_MAX");
  int threads = argc >= 2 ? atoi (argv[1]) : 0;
  long rounds = argc >= 3 ? atol (argv[2]) : 100000;
  long failed = 0;
  int got = 0;
  char peak[64], hwm[64], rss[64];
  double t0, t1;

  if (threads < 1 || rounds < 1)
    {
      fprintf (stderr, "usage: %s THREADS [ROUNDS]\n", argv[0]);
      return 2;
    }
  t0 = now_s ();
#pragma omp parallel num_threads(threads) reduction(+:failed)
  {
    long i;
    for (i = 0; i < rounds; i++)
      {
	volatile char *p = malloc (1024);
	if (p == NULL)
	  {
	    failed++;
	    continue;
	  }
	p[0] = (char) i;
	p[1023] = (char) i;
	free ((void *) p);
      }
#pragma omp masked
    got = omp_get_num_threads ();
  }
  t1 = now_s ();
  status ("VmPeak", peak, sizeof peak);
  status ("VmHWM", hwm, sizeof hwm);
  status ("VmRSS", rss, sizeof rss);
  printf ("S9-10 malloc %s threads=%d team=%d rounds=%ld arena_max=%s wall_s=%.4f %s %s %s failed_mallocs=%ld\n",
	  failed || got != threads ? "FAIL" : "PASS", threads, got, rounds, arenas ? arenas : "unset",
	  t1 - t0, peak, hwm, rss, failed);
  return failed || got != threads;
}
