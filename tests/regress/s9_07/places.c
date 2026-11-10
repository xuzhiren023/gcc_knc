/* S9-07 host test of libgomp's default places on KNC (docs/research/knc-libgomp.md section 3).

   tools/s9_07_checks.py host compiles this with the k1om config_path as the include path, so
   affinity.c and proc.c below are the files the k1om runtime builds, and libgomp.h is the shim
   next to this file.  The runtime is started the way env.c starts it when the bind policy is
   not false, with the mask of one case as the inherited mask and ROOT in front of every file it
   opens:

       places TREE ROOT

   The card's topology: core c of 0-59 is CPUs 4c+1..4c+4, and core 60, the OS core, is CPUs 0
   and 241-243.  One place per core of the mask is expected, without the OS core unless the mask
   holds nothing else; omp_get_num_procs and the default team size count the CPUs of those
   places; a team size from OMP_NUM_THREADS is kept.  */
#include "affinity.c"
#include "proc.c"

#include <stdarg.h>

#define NCPUS 244
#define OS_CORE 60
#define CORE_CPUS 4

struct gomp_task_icv gomp_global_icv;
unsigned long gomp_available_cpus = 1;
void **gomp_places_list;
unsigned long gomp_places_list_len;

static struct gomp_thread thread;
static struct gomp_icv_list no_suffix;
static cpu_set_t inherited;
static const char *root;

static const struct test_case
{
  const char *name;
  int mask_core, mask_cores;	/* The inherited mask: these whole cores.  */
  int place_core, places;	/* The expected places: these cores, in order.  */
  int num_threads;		/* OMP_NUM_THREADS, or 0 when it is not given.  */
} cases[] =
{
  { "244 CPUs", 0, 61, 0, 60, 0 },
  { "120-CPU mask (cores 30-59)", 30, 30, 30, 30, 0 },
  { "OS core only", OS_CORE, 1, OS_CORE, 1, 0 },
  { "244 CPUs, OMP_NUM_THREADS=244", 0, 61, 0, 60, 244 }
};

static int
core_cpu (int core, int k)
{
  if (core == OS_CORE)
    return k == 0 ? 0 : 240 + k;
  return CORE_CPUS * core + 1 + k;
}

struct gomp_thread *
gomp_thread (void)
{
  return &thread;
}

struct gomp_task_icv *
gomp_icv (bool write)
{
  return &gomp_global_icv;
}

struct gomp_icv_list *
gomp_get_initial_icv_item (int dev_num)
{
  return dev_num == GOMP_DEVICE_NUM_FOR_NO_SUFFIX ? &no_suffix : NULL;
}

bool
gomp_get_icv_flag (uint32_t value, enum gomp_icvs icv)
{
  return value & (1 << icv);
}

void *
gomp_malloc (size_t size)
{
  return malloc (size);
}

void *
gomp_realloc (void *old, size_t size)
{
  return realloc (old, size);
}

void
gomp_error (const char *fmt, ...)
{
  va_list list;

  va_start (list, fmt);
  fputs ("libgomp: ", stderr);
  vfprintf (stderr, fmt, list);
  fputc ('\n', stderr);
  va_end (list);
}

void
gomp_display_string (char *buffer, size_t size, size_t *ret, const char *str,
		     size_t len)
{
}

/* As on Linux: EINVAL unless the set can hold every CPU of the card.  */

int
test_getaffinity (size_t size, cpu_set_t *set)
{
  if (8 * size < NCPUS)
    return EINVAL;
  memset (set, 0, size);
  memcpy (set, &inherited, size < sizeof inherited ? size : sizeof inherited);
  return 0;
}

int
test_setaffinity (size_t size, const cpu_set_t *set)
{
  return 0;
}

FILE *
test_fopen (const char *name, const char *mode)
{
  char path[4096];

  snprintf (path, sizeof path, "%s%s", root, name);
  return (fopen) (path, mode);
}

/* The index of the first place that is not the expected core, or -1.  */

static int
wrong_place (const struct test_case *c)
{
  for (int i = 0; i < c->places && i < (int) gomp_places_list_len; i++)
    {
      if (omp_get_place_num_procs (i) != CORE_CPUS)
	return i;
      for (int k = 0; k < CORE_CPUS; k++)
	if (!CPU_ISSET_S (core_cpu (c->place_core + i, k), gomp_cpuset_size,
			  (cpu_set_t *) gomp_places_list[i]))
	  return i;
    }
  return -1;
}

static bool
run_case (const char *tree, const struct test_case *c)
{
  int procs = CORE_CPUS * c->places;
  int threads = c->num_threads ? c->num_threads : procs;

  CPU_ZERO (&inherited);
  for (int core = c->mask_core; core < c->mask_core + c->mask_cores; core++)
    for (int k = 0; k < CORE_CPUS; k++)
      CPU_SET (core_cpu (core, k), &inherited);
  gomp_places_list = NULL;
  gomp_places_list_len = 0;
  no_suffix.flags = 0;

  /* env.c, initialize_env.  */
  gomp_init_num_threads ();
  gomp_available_cpus = gomp_global_icv.nthreads_var;
  if (c->num_threads)
    {
      gomp_global_icv.nthreads_var = c->num_threads;
      no_suffix.flags |= 1 << GOMP_ICV_NTHREADS;
    }
  gomp_init_affinity ();

  int wrong = wrong_place (c);
  bool ok = ((int) gomp_places_list_len == c->places && wrong < 0
	     && omp_get_num_procs () == procs
	     && (int) gomp_global_icv.nthreads_var == threads);
  printf ("%s %s, %s: omp_get_num_places %lu (want %d), omp_get_num_procs %d "
	  "(want %d), team size %lu (want %d)",
	  ok ? "PASS" : "FAIL", tree, c->name, gomp_places_list_len, c->places,
	  omp_get_num_procs (), procs, gomp_global_icv.nthreads_var, threads);
  if (wrong >= 0)
    printf (", place %d has %d CPUs and is not core %d", wrong,
	    omp_get_place_num_procs (wrong), c->place_core + wrong);
  putchar ('\n');
  return ok;
}

int
main (int argc, char **argv)
{
  int failed = 0;

  if (argc != 3)
    return 2;
  root = argv[2];
  for (size_t i = 0; i < sizeof cases / sizeof cases[0]; i++)
    failed += !run_case (argv[1], &cases[i]);
  return failed != 0;
}
