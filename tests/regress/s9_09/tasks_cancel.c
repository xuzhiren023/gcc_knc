/* S9-09 card programs for the task and cancel paths of the KNC team barrier
   (libgomp/config/linux/knc/bar.c) at 60x4; run.sh runs both with 240 threads.

       tasks_cancel tasks THREADS [ROUNDS]
           each round one thread queues 10000 tasks and the team runs them from a barrier: the
           barrier that ends a single (round 0, 3, ...), an explicit barrier after the creator's
           taskwait (1, 4, ...) and the barrier that ends the region (2, 5, ...).  Every task must
           run once, and threads other than the creator must have been woken to run some.
       tasks_cancel cancel THREADS [ROUNDS]        (OMP_CANCELLATION=true)
           each round all threads pass a cancellable barrier; then all but one wait in the next,
           spinning (even rounds) or asleep (odd rounds), and the last one, each thread in turn,
           does `cancel parallel': nobody may pass.  A region with three plain barriers follows,
           which every thread must pass together.  */
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define NTASKS 10000
#define MAX_THREADS 256

static int hits[NTASKS];
static struct { long n; char pad[56]; } ran[MAX_THREADS] __attribute__((aligned (64)));

static double
now_ns (void)
{
  struct timespec ts;
  clock_gettime (CLOCK_MONOTONIC_RAW, &ts);
  return ts.tv_sec * 1e9 + ts.tv_nsec;
}

static void
create (void)
{
  for (int i = 0; i < NTASKS; i++)
    {
#pragma omp task firstprivate (i)
      {
	volatile unsigned long x = i;
	for (int k = 0; k < 2000; k++)
	  x = x * 6364136223846793005UL + 1;
	hits[i]++;
	ran[omp_get_thread_num ()].n++;
      }
    }
}

static int
tasks (int threads, int rounds)
{
  long total = 0;
  int runners = 0;

  for (int r = 0; r < rounds; r++)
    {
#pragma omp parallel num_threads (threads)
      {
	if (r % 3 == 0)
	  {
#pragma omp single
	    create ();
	  }
	else
	  {
#pragma omp masked
	    {
	      create ();
	      if (r % 3 == 1)
		{
#pragma omp taskwait
		}
	    }
	    if (r % 3 == 1)
	      {
#pragma omp barrier
	      }
	  }
      }
      for (int i = 0; i < NTASKS; i++)
	if (hits[i] != r + 1)
	  {
	    printf ("S9-09 tasks FAIL: round %d: task %d ran %d times, want %d\n", r, i, hits[i], r + 1);
	    return 1;
	  }
    }
  for (int i = 0; i < threads; i++)
    {
      total += ran[i].n;
      runners += ran[i].n != 0;
    }
  if (total != (long) rounds * NTASKS || (threads > 1 && runners < 2))
    {
      printf ("S9-09 tasks FAIL: %ld tasks run by %d threads, want %ld by 2 or more\n", total, runners,
	      (long) rounds * NTASKS);
      return 1;
    }
  printf ("S9-09 tasks PASS: threads=%d rounds=%d tasks=%ld, run by %d threads\n", threads, rounds, total,
	  runners);
  return 0;
}

static int
cancel (int threads, int rounds)
{
  if (!omp_get_cancellation ())
    {
      puts ("S9-09 cancel FAIL: run with OMP_CANCELLATION=true");
      return 1;
    }
  for (int r = 0; r < rounds; r++)
    {
      int first = 0, waiting = 0, passed = 0, count[3] = { 0, 0, 0 }, bad = 0;
      int last = r / 2 % threads;

#pragma omp parallel num_threads (threads)
      {
#pragma omp barrier
#pragma omp atomic
	first++;
	if (omp_get_thread_num () == last)
	  {
	    int seen;
	    do
	      {
#pragma omp atomic read
		seen = waiting;
	      }
	    while (seen != threads - 1);
	    /* The default spin is about 3 ms.  */
	    double start = now_ns ();
	    while (now_ns () - start < (r % 2 ? 2e7 : 2e5))
	      continue;
#pragma omp cancel parallel
	  }
#pragma omp atomic
	waiting++;
#pragma omp barrier
#pragma omp atomic
	passed++;
      }

#pragma omp parallel num_threads (threads)
      for (int k = 0; k < 3; k++)
	{
	  int seen;
#pragma omp atomic
	  count[k]++;
#pragma omp barrier
#pragma omp atomic read
	  seen = count[k];
	  if (seen != threads)
	    {
#pragma omp atomic
	      bad++;
	    }
	}

      if (first != threads || waiting != threads - 1 || passed != 0 || bad != 0)
	{
	  printf ("S9-09 cancel FAIL: round %d, thread %d cancels: %d passed the first barrier (want %d), "
		  "%d waited in the cancelled one (want %d), %d passed it (want 0), %d early passes of the "
		  "barriers after it\n", r, last, first, threads, waiting, threads - 1, passed, bad);
	  return 1;
	}
    }
  printf ("S9-09 cancel PASS: threads=%d rounds=%d, each followed by 3 plain barriers\n", threads, rounds);
  return 0;
}

int
main (int argc, char **argv)
{
  int threads = argc > 2 ? atoi (argv[2]) : 0, team = 0;

  if (argc < 3 || threads < 1 || threads > MAX_THREADS)
    {
      fprintf (stderr, "usage: tasks_cancel tasks|cancel THREADS [ROUNDS]\n");
      return 2;
    }
#pragma omp parallel num_threads (threads)
#pragma omp single
  team = omp_get_num_threads ();
  if (team != threads)
    {
      printf ("S9-09 %s FAIL: team of %d threads, want %d\n", argv[1], team, threads);
      return 1;
    }
  if (!strcmp (argv[1], "tasks"))
    return tasks (threads, argc > 3 ? atoi (argv[3]) : 21);
  if (!strcmp (argv[1], "cancel"))
    return cancel (threads, argc > 3 ? atoi (argv[3]) : 2 * threads);
  return 2;
}
