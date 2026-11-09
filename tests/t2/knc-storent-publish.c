/* S8-13 / E5-08: data written with vmovnrngoaps (weakly ordered, no read)
   must be visible to another core once a flag says so.  The compiler places
   the KNC fence (lock addl $0,(%rsp)) before the loop exit, so the flag
   store that follows the fill cannot pass the streamed lines.

   Threads form pairs, each pinned to its own logical CPU from the launch
   affinity (thread t and t + threads/2, so a pair crosses cores at 60x4).
   Each round the writer streams a = round+1 times x into its 1 MiB y with
   stream_fill, built here at -O2 so its main loop takes the NGO path (n/16
   = 16384 iterations is beyond the 4096 guard), then publishes the round in
   the flag.  The reader spins on the flag, checks every element of y
   bitwise against a * x (x holds small integers, so the products are
   exact), the last-streamed lines first since those are the ones that can
   still be in flight, then acknowledges.  Any stale element is a failure.

   Build: -O2 -pthread (tools/storent.py t2 stages the binary).  Run on the
   card with --threads 240 (default; pairs = threads/2), --rounds R (20),
   --length N floats per pair (262144).  Prints
   "S8-13-PUBLISH PASS pairs=P rounds=R stale=0" and exits 0, or FAIL and
   exits 1.  With --control 1 the writer streams through inline-asm
   vmovnrngoaps with no fence before the flag, to show whether the card
   makes a missing fence visible: it prints "S8-13-PUBLISH CONTROL ...
   stale=N" and exits 0 whatever N is.  The lead runs it; the engineer only
   builds it.  */
#define _GNU_SOURCE
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

__attribute__ ((noinline)) void
stream_fill (float *restrict yy, const float *restrict xx, float a,
	     unsigned long n)
{
  float *restrict y = __builtin_assume_aligned (yy, 64);
  const float *restrict x = __builtin_assume_aligned (xx, 64);
  for (unsigned long i = 0; i < n; ++i)
    y[i] = a * x[i];
}

/* The control writer: the same NGO stores by hand, and no fence.  */
typedef float v16sf __attribute__ ((vector_size (64)));

__attribute__ ((noinline)) void
stream_fill_control (float *restrict yy, const float *restrict xx, float a,
		     unsigned long n)
{
  v16sf *restrict y = __builtin_assume_aligned (yy, 64);
  const v16sf *restrict x = __builtin_assume_aligned (xx, 64);
  for (unsigned long i = 0; i < n / 16; ++i)
    {
      v16sf v = a * x[i];
      __asm__ volatile ("vmovnrngoaps %g1, %0" : "=m" (y[i]) : "YJ" (v)
			: "memory");
    }
}

struct pair
{
  float *y;
  unsigned long stale;
  int cpu_writer, cpu_reader;
  char pad0[64];
  volatile unsigned int flag;	/* round published by the writer */
  char pad1[60];
  volatile unsigned int ack;	/* round consumed by the reader */
  char pad2[60];
} __attribute__ ((aligned (64)));

static struct pair *pairs;
static const float *x;
static unsigned long length = 262144;
static unsigned int rounds = 20;
static int threads = 240;
static int control;
static pthread_barrier_t barrier;
static cpu_set_t allowed;

static void
fail (const char *what)
{
  printf ("S8-13-PUBLISH FAIL %s\n", what);
  exit (2);
}

static void
pin (int cpu)
{
  cpu_set_t mask;
  CPU_ZERO (&mask);
  CPU_SET (cpu, &mask);
  if (sched_setaffinity (0, sizeof mask, &mask))
    fail ("affinity");
}

static void
spin_until (volatile unsigned int *word, unsigned int value)
{
  unsigned long spins = 0;
  while (__atomic_load_n (word, __ATOMIC_ACQUIRE) != value)
    if (++spins % 4096 == 0)
      sched_yield ();
}

static void *
writer (void *arg)
{
  struct pair *p = arg;
  pin (p->cpu_writer);
  pthread_barrier_wait (&barrier);
  for (unsigned int round = 1; round <= rounds; ++round)
    {
      if (control)
	stream_fill_control (p->y, x, (float) round, length);
      else
	stream_fill (p->y, x, (float) round, length);
      /* A plain release store: only the compiler's fence after the NGO
	 loop orders the streamed lines before this flag.  */
      __atomic_store_n (&p->flag, round, __ATOMIC_RELEASE);
      spin_until (&p->ack, round);
    }
  return 0;
}

static void *
reader (void *arg)
{
  struct pair *p = arg;
  pin (p->cpu_reader);
  pthread_barrier_wait (&barrier);
  for (unsigned int round = 1; round <= rounds; ++round)
    {
      spin_until (&p->flag, round);
      float a = (float) round;
      unsigned long stale = 0;
      for (unsigned long i = length; i-- > 0;)
	if (p->y[i] != a * x[i])
	  ++stale;
      p->stale += stale;
      __atomic_store_n (&p->ack, round, __ATOMIC_RELEASE);
    }
  return 0;
}

int
main (int argc, char **argv)
{
  for (int i = 1; i + 1 < argc; i += 2)
    if (!strcmp (argv[i], "--threads"))
      threads = atoi (argv[i + 1]);
    else if (!strcmp (argv[i], "--rounds"))
      rounds = (unsigned int) atoi (argv[i + 1]);
    else if (!strcmp (argv[i], "--length"))
      length = strtoul (argv[i + 1], 0, 10);
    else if (!strcmp (argv[i], "--control"))
      control = atoi (argv[i + 1]);
    else
      fail ("argument");
  if (threads < 2 || threads > 240 || rounds < 1 || length < 4096
      || length % 16)
    fail ("argument range");
  int npairs = threads / 2;
  threads = 2 * npairs;

  /* Logical CPUs the launch allows, in order; thread t uses the t-th.  */
  if (sched_getaffinity (0, sizeof allowed, &allowed))
    fail ("allowed affinity");
  int cpus[CPU_SETSIZE], ncpus = 0;
  for (int c = 0; c < CPU_SETSIZE; ++c)
    if (CPU_ISSET (c, &allowed))
      cpus[ncpus++] = c;
  if (ncpus < 2)
    fail ("needs two CPUs");

  void *mem;
  if (posix_memalign (&mem, 64, length * sizeof (float)))
    fail ("x allocation");
  float *xw = mem;
  for (unsigned long i = 0; i < length; ++i)
    xw[i] = (float) (i % 251);
  x = xw;
  if (posix_memalign (&mem, 64, npairs * sizeof (struct pair)))
    fail ("pair allocation");
  pairs = memset (mem, 0, npairs * sizeof (struct pair));
  for (int p = 0; p < npairs; ++p)
    {
      if (posix_memalign (&mem, 64, length * sizeof (float)))
	fail ("y allocation");
      pairs[p].y = memset (mem, 0, length * sizeof (float));
      pairs[p].cpu_writer = cpus[p % ncpus];
      pairs[p].cpu_reader = cpus[(p + npairs) % ncpus];
    }

  if (pthread_barrier_init (&barrier, 0, threads))
    fail ("barrier");
  pthread_t *ids = calloc (threads, sizeof *ids);
  for (int p = 0; p < npairs; ++p)
    if (pthread_create (&ids[2 * p], 0, writer, &pairs[p])
	|| pthread_create (&ids[2 * p + 1], 0, reader, &pairs[p]))
      fail ("thread create");
  for (int t = 0; t < threads; ++t)
    if (pthread_join (ids[t], 0))
      fail ("thread join");

  unsigned long stale = 0;
  for (int p = 0; p < npairs; ++p)
    {
      stale += pairs[p].stale;
      if (pairs[p].stale)
	printf ("INFO pair=%d writer_cpu=%d reader_cpu=%d stale=%lu\n", p,
		pairs[p].cpu_writer, pairs[p].cpu_reader, pairs[p].stale);
    }
  printf ("INFO cpus=%d length=%lu\n", ncpus, length);
  printf ("S8-13-PUBLISH %s pairs=%d rounds=%u stale=%lu\n",
	  control ? "CONTROL" : stale ? "FAIL" : "PASS", npairs, rounds,
	  stale);
  return !control && stale != 0;
}
