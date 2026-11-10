/* S9-08 card measurement 1 (docs/research/knc-libgomp.md section 4): one core, a worker loop
   alone and with 1, 2 and 3 siblings spinning on a local word, with no hint and with DELAY 32,
   128 and 512 between reads.  This fixes gomp_knc_delay and shows whether DELAY is a NOP on
   this stepping.

       spin_core [ROUNDS [SEED]]

   The worker is pinned to sibling 0 of core 0 (CPU 1) and the spinners to siblings 1-3
   (CPUs 2-4); every thread sets and checks its own single-CPU affinity (ADR-0010 point 2).
   Spinners are created before and joined after each timed group, so no thread exists outside
   its configuration.  Timing follows ADR-0010: CLOCK_MONOTONIC_RAW makespans; a pilot sizes a
   batch to about 60 ms alone (at most about 4x that under three hint-less spinners); each
   configuration is one group of 3 warm-up and 21 timed batches per round, the 13 groups of a
   round in an order drawn per round (point 7).  The statistic is the per-round ratio
   T(configuration) / T(alone); every batch is printed.  */
#define _GNU_SOURCE 1
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define WORKER_CPU 1
#define LEN 1024
#define WARMUP 3
#define TIMED 21
#define TARGET_NS 60000000.0

/* Line-sized and line-aligned, one per spinner: the spinners poll a local word.  */
struct word
{
  volatile int stop;
  char pad[64 - sizeof (int)];
} __attribute__ ((aligned (64)));

struct config
{
  const char *name;
  int spinners;			/* 0 to 3.  */
  unsigned int delay;		/* 0: no hint.  */
};

static struct config configs[13];
static int nconfigs;
static struct word words[3];
static float xs[LEN] __attribute__ ((aligned (4096)));
static float ys[LEN + 128] __attribute__ ((aligned (4096)));
static volatile float sink;
static volatile int running;

static double
now_ns (void)
{
  struct timespec ts;
  clock_gettime (CLOCK_MONOTONIC_RAW, &ts);
  return ts.tv_sec * 1e9 + ts.tv_nsec;
}

/* Set and check this thread's single-CPU affinity.  */
static void
pin (int cpu)
{
  cpu_set_t set;
  CPU_ZERO (&set);
  CPU_SET (cpu, &set);
  if (pthread_setaffinity_np (pthread_self (), sizeof set, &set) != 0
      || pthread_getaffinity_np (pthread_self (), sizeof set, &set) != 0
      || CPU_COUNT (&set) != 1 || !CPU_ISSET (cpu, &set) || sched_getcpu () != cpu)
    {
      fprintf (stderr, "spin_core: pin to CPU %d failed\n", cpu);
      exit (2);
    }
}

/* The worker's batch: N passes of an L1-resident dot product.  */
static void
work (long n)
{
  float s = 0;
  const float *y = ys + 128;	/* x and y 512 bytes apart (ADR-0010 amendment 1).  */
  for (long pass = 0; pass < n; pass++)
    {
      for (int i = 0; i < LEN; i++)
	s += xs[i] * y[i];
      __asm volatile ("" : "+m" (xs[0]));
    }
  sink = s;
}

struct spinner
{
  int index;
  unsigned int delay;
};

static void *
spin (void *arg)
{
  struct spinner *sp = arg;
  struct word *w = &words[sp->index];
  unsigned int delay = sp->delay;
  pin (WORKER_CPU + 1 + sp->index);
  __atomic_add_fetch (&running, 1, __ATOMIC_SEQ_CST);
  if (delay == 0)
    while (!w->stop)
      ;
  else
    while (!w->stop)
      __asm volatile ("delay %0" : : "r" (delay) : "memory");
  return NULL;
}

static int
compare (const void *a, const void *b)
{
  double x = *(const double *) a, y = *(const double *) b;
  return (x > y) - (x < y);
}

/* One group of configuration C: returns the median timed batch in ns.  */
static double
group (int round, const struct config *c, long passes)
{
  pthread_t threads[3];
  struct spinner sps[3];
  double t[TIMED];
  running = 0;
  for (int k = 0; k < c->spinners; k++)
    {
      words[k].stop = 0;
      sps[k].index = k;
      sps[k].delay = c->delay;
      if (pthread_create (&threads[k], NULL, spin, &sps[k]) != 0)
	{
	  fprintf (stderr, "spin_core: pthread_create failed\n");
	  exit (2);
	}
    }
  while (running != c->spinners)
    ;
  for (int b = 0; b < WARMUP + TIMED; b++)
    {
      double t0 = now_ns ();
      work (passes);
      double t1 = now_ns ();
      if (b >= WARMUP)
	t[b - WARMUP] = t1 - t0;
    }
  for (int k = 0; k < c->spinners; k++)
    words[k].stop = 1;
  for (int k = 0; k < c->spinners; k++)
    pthread_join (threads[k], NULL);
  for (int b = 0; b < TIMED; b++)
    printf ("SAMPLE round=%d config=%s batch=%d ms=%.4f\n", round, c->name, b, t[b] / 1e6);
  qsort (t, TIMED, sizeof t[0], compare);
  return t[TIMED / 2];
}

int
main (int argc, char **argv)
{
  int rounds = argc > 1 ? atoi (argv[1]) : 5;
  if (rounds < 1 || rounds > 64)
    rounds = 5;
  unsigned int seed = argc > 2 ? strtoul (argv[2], NULL, 10) : (unsigned int) time (NULL);
  static const unsigned int delays[] = { 0, 32, 128, 512 };
  static char names[13][24];

  configs[nconfigs++] = (struct config) { "alone", 0, 0 };
  for (int s = 1; s <= 3; s++)
    for (int d = 0; d < 4; d++)
      {
	if (delays[d])
	  snprintf (names[nconfigs], sizeof names[0], "s%d-delay%u", s, delays[d]);
	else
	  snprintf (names[nconfigs], sizeof names[0], "s%d-nohint", s);
	configs[nconfigs] = (struct config) { names[nconfigs], s, delays[d] };
	nconfigs++;
      }

  pin (WORKER_CPU);
  for (int i = 0; i < LEN; i++)
    {
      xs[i] = 1.0f / (i + 1);
      ys[i + 128] = (float) (i & 7);
    }

  /* Pilot: size a batch to about TARGET_NS alone.  */
  long passes = 64;
  for (;;)
    {
      double t0 = now_ns ();
      work (passes);
      double dt = now_ns () - t0;
      if (dt > TARGET_NS / 4)
	{
	  passes = (long) (passes * TARGET_NS / dt);
	  break;
	}
      passes *= 4;
    }
  printf ("S9-08 spin_core: worker CPU %d, spinners CPUs %d-%d, %ld passes of %d per batch, "
	  "%d rounds, seed %u\n", WORKER_CPU, WORKER_CPU + 1, WORKER_CPU + 3, passes, LEN,
	  rounds, seed);

  double ratio[13][64];
  srand (seed);
  for (int r = 0; r < rounds; r++)
    {
      int order[13];
      double median[13];
      for (int i = 0; i < nconfigs; i++)
	order[i] = i;
      for (int i = nconfigs - 1; i > 0; i--)
	{
	  int j = rand () % (i + 1), tmp = order[i];
	  order[i] = order[j];
	  order[j] = tmp;
	}
      for (int i = 0; i < nconfigs; i++)
	{
	  int k = order[i];
	  median[k] = group (r, &configs[k], passes);
	  printf ("GROUP round=%d position=%d config=%s median_ms=%.4f\n", r, i, configs[k].name,
		  median[k] / 1e6);
	}
      for (int k = 0; k < nconfigs; k++)
	{
	  ratio[k][r] = median[k] / median[0];
	  printf ("RATIO round=%d config=%s ratio=%.4f\n", r, configs[k].name, ratio[k][r]);
	}
    }
  for (int k = 1; k < nconfigs; k++)
    {
      qsort (ratio[k], rounds, sizeof ratio[k][0], compare);
      printf ("SUMMARY config=%s median_ratio=%.4f min=%.4f max=%.4f rounds=%d\n",
	      configs[k].name, ratio[k][rounds / 2], ratio[k][0], ratio[k][rounds - 1], rounds);
    }
  return 0;
}
