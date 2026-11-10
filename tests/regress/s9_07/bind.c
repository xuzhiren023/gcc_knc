/* S9-07 card check of libgomp's binding on KNC (docs/research/knc-libgomp.md section 3 and
   ticket B's card checks); run by the run.sh that tools/s9_07_checks.py build writes.

       bind PLACES PER-PLACE BIND

   PLACES is the expected place list within the mask this job inherited (card_run's, read from
   the parent's Cpus_allowed_list, because libgomp has already bound this thread): "cores" is
   one place per core, the four CPUs 4c+1..4c+4 of core c in 0-59; "first" is one place per core
   holding only CPU 4c+1; "none" is no place list.  A team of PER-PLACE threads per place (the
   default team for 0) must put exactly that many threads on every place, each thread's affinity
   mask being its place ("none": the inherited mask).  BIND is the expected omp_get_proc_bind.
   The OS core (CPUs 0 and 241-243) is in no expected place; a mask with it is the host test's
   case.  */
#define _GNU_SOURCE
#include <omp.h>
#include <sched.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define CORES 60
#define MAX_THREADS 1024

static cpu_set_t inherited, want[CORES], bound[MAX_THREADS];
static int place_of[MAX_THREADS], on_place[CORES];
static int failures;

static void
fail (const char *what, int index, int got, int expected)
{
  if (failures++ < 10)
    printf ("  %s %d: %d, expected %d\n", what, index, got, expected);
}

static void
read_inherited (void)
{
  char name[64], line[4096];
  FILE *f;

  snprintf (name, sizeof name, "/proc/%d/status", (int) getppid ());
  f = fopen (name, "r");
  while (f && fgets (line, sizeof line, f))
    if (strncmp (line, "Cpus_allowed_list:", 18) == 0)
      for (char *p = line + 18, *end; *p && *p != '\n'; p = end + (*end == ','))
	{
	  long first = strtol (p, &end, 10), last = first;
	  if (end == p)
	    break;
	  if (*end == '-')
	    last = strtol (end + 1, &end, 10);
	  for (; first <= last; first++)
	    CPU_SET (first, &inherited);
	}
  if (f)
    fclose (f);
}

int
main (int argc, char **argv)
{
  static const char *const binds[] = { "false", "true", "primary", "close", "spread" };
  int places = 0, procs = 0, team = 0;

  if (argc != 4)
    return 2;
  const char *mode = argv[1];
  int per_place = atoi (argv[2]);
  bool unbound = strcmp (mode, "none") == 0;
  int width = strcmp (mode, "first") == 0 ? 1 : 4;

  read_inherited ();
  for (int core = 0; core < CORES && !unbound; core++)
    {
      CPU_ZERO (&want[places]);
      for (int k = 0; k < width; k++)
	if (CPU_ISSET (4 * core + 1 + k, &inherited))
	  CPU_SET (4 * core + 1 + k, &want[places]);
      procs += CPU_COUNT (&want[places]);
      places += CPU_COUNT (&want[places]) != 0;
    }
  /* Only the KNC default places change omp_get_num_procs: with a place list from the
     environment libgomp counts the inherited mask, as on any Linux.  */
  if (unbound || getenv ("OMP_PLACES") || getenv ("GOMP_CPU_AFFINITY"))
    procs = CPU_COUNT (&inherited);

  if (omp_get_num_places () != places)
    fail ("omp_get_num_places", 0, omp_get_num_places (), places);
  if (omp_get_num_procs () != procs)
    fail ("omp_get_num_procs", 0, omp_get_num_procs (), procs);
  if (strcmp (binds[omp_get_proc_bind ()], argv[3]) != 0)
    printf ("  omp_get_proc_bind: %s, expected %s\n", binds[omp_get_proc_bind ()],
	    argv[3]), failures++;
  for (int i = 0; i < places && i < omp_get_num_places (); i++)
    {
      int ids[CPU_SETSIZE];
      cpu_set_t have;

      CPU_ZERO (&have);
      omp_get_place_proc_ids (i, ids);
      for (int k = 0; k < omp_get_place_num_procs (i); k++)
	CPU_SET (ids[k], &have);
      if (!CPU_EQUAL (&have, &want[i]))
	fail ("omp_get_place_num_procs of place", i, omp_get_place_num_procs (i),
	      CPU_COUNT (&want[i]));
    }

  int threads = per_place ? per_place * places : omp_get_max_threads ();
  if (threads < 1 || threads > MAX_THREADS)
    threads = 1;
#pragma omp parallel num_threads (threads)
  {
    int t = omp_get_thread_num ();
    sched_getaffinity (0, sizeof bound[t], &bound[t]);
    place_of[t] = omp_get_place_num ();
#pragma omp master
    team = omp_get_num_threads ();
  }

  if (team != threads)
    fail ("team size", 0, team, threads);
  for (int t = 0; t < team; t++)
    {
      int place = place_of[t];
      if (unbound ? place != -1 : place < 0 || place >= places)
	fail ("omp_get_place_num of thread", t, place, unbound ? -1 : places - 1);
      else if (!CPU_EQUAL (&bound[t], unbound ? &inherited : &want[place]))
	fail ("CPUs in the affinity mask of thread", t, CPU_COUNT (&bound[t]),
	      CPU_COUNT (unbound ? &inherited : &want[place]));
      else if (!unbound)
	on_place[place]++;
    }
  for (int i = 0; i < places && per_place; i++)
    if (on_place[i] != per_place)
      fail ("threads on place", i, on_place[i], per_place);

  printf ("S9-07 bind %s places=%s per-place=%d bind=%s: %d places, %d procs, threads=%d, "
	  "%d CPUs inherited\n", failures ? "FAIL" : "PASS", mode, per_place, argv[3],
	  omp_get_num_places (), omp_get_num_procs (), team, CPU_COUNT (&inherited));
  return failures != 0;
}
