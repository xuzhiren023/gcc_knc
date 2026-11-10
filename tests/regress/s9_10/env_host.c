/* S9-10 host test of the KNC runtime defaults (docs/research/knc-libgomp.md sections 5 and 6,
   ticket E).

   tools/s9_10_checks.py host compiles libgomp's own env.c with the Cygwin GCC,
   -D__k1om__ and the k1om config_path and config.h, links them with this file, and runs it once
   per case below with that case's environment.  Building it also compiles libgomp.h and
   config/linux/knc/bar.h, whose KNC layout checks (gomp_knc_thread_check1, ...) fail to compile
   when a thread's data, its implicit task or a barrier group shares a cache line; the host is
   x86-64 LP64 like k1om, so the sizes are the card's.

   Cases (argv[1]):
   default  no OMP_SCHEDULE, MALLOC_ARENA_MAX, OMP_STACKSIZE or GOMP_STACKSIZE: run-sched-var,
            read as omp_get_schedule (icv.c) and schedule(runtime) (loop.c) read it, is static
            with the default chunk, and the verbose
            omp_display_env shows OMP_SCHEDULE 'STATIC', MALLOC_ARENA_MAX '' and the KNC hint.
   set      OMP_SCHEDULE=dynamic,4 MALLOC_ARENA_MAX=60 OMP_STACKSIZE=2M: OMP_SCHEDULE still
            overrides, the display shows the values and no hint.  */
#include "libgomp.h"

#include <stdio.h>
#include <string.h>
#include <unistd.h>

/* What the rest of libgomp provides to env.c; none of it is reached in these cases.  */
__thread struct gomp_thread gomp_tls_data;
pthread_attr_t gomp_thread_attr;
unsigned int gomp_knc_delay = 32;

void
gomp_error (const char *fmt, ...)
{
  va_list ap;
  va_start (ap, fmt);
  fputs ("libgomp: ", stdout);
  vprintf (fmt, ap);
  putchar ('\n');
  va_end (ap);
}

void gomp_init_num_threads (void) { gomp_global_icv.nthreads_var = 1; }
void gomp_init_affinity (void) {}
void gomp_init_targets_once (void) {}
void goacc_runtime_initialize (void) {}
void goacc_profiling_initialize (void) {}
void gomp_set_affinity_format (const char *format, size_t len) { (void) format; (void) len; }
void *gomp_malloc_cleared (size_t size) { return calloc (1, size); }
void **gomp_affinity_alloc (unsigned long count, bool quiet) { (void) count; (void) quiet; return NULL; }
void gomp_affinity_init_place (void *p) { (void) p; }
bool gomp_affinity_add_cpus (void *p, unsigned long num, unsigned long len, long stride, bool quiet)
{ (void) p; (void) num; (void) len; (void) stride; (void) quiet; return false; }
bool gomp_affinity_remove_cpu (void *p, unsigned long num) { (void) p; (void) num; return false; }
bool gomp_affinity_copy_place (void *p, void *q, long stride) { (void) p; (void) q; (void) stride; return false; }
bool gomp_affinity_same_place (void *p, void *q) { (void) p; (void) q; return false; }
bool gomp_affinity_finalize_place_list (bool quiet) { (void) quiet; return false; }
bool gomp_affinity_init_level (int level, unsigned long count, bool quiet)
{ (void) level; (void) count; (void) quiet; return false; }
void gomp_affinity_print_place (void *p) { (void) p; }
omp_allocator_handle_t
omp_init_allocator (omp_memspace_handle_t m, int n, const omp_alloctrait_t t[])
{ (void) m; (void) n; (void) t; return omp_null_allocator; }
void omp_destroy_allocator (omp_allocator_handle_t a) { (void) a; }
struct gomp_task_icv *gomp_new_icv (void) { abort (); }

static int failed;

static void
expect (int ok, const char *what)
{
  printf ("%s %s\n", ok ? "ok  " : "FAIL", what);
  failed += !ok;
}

/* The verbose omp_display_env output, which goes to stderr.  */
static char display[65536];

static void
capture_display (void)
{
  FILE *f = tmpfile ();
  int saved = dup (2);
  size_t n;

  fflush (stderr);
  dup2 (fileno (f), 2);
  omp_display_env (1);
  fflush (stderr);
  dup2 (saved, 2);
  close (saved);
  rewind (f);
  n = fread (display, 1, sizeof display - 1, f);
  display[n] = '\0';
  fclose (f);
}

static int
has_line (const char *line)
{
  const char *p = display;
  size_t len = strlen (line);

  while ((p = strstr (p, line)) != NULL)
    {
      if ((p == display || p[-1] == '\n') && (p[len] == '\n' || p[len] == '\0'))
	return 1;
      p += len;
    }
  return 0;
}

#define KNC_HINT "  [host] KNC hint: "

int
main (int argc, char **argv)
{
  omp_sched_t kind;
  int chunk, set;

  if (argc != 2 || (strcmp (argv[1], "default") && strcmp (argv[1], "set")))
    {
      fprintf (stderr, "usage: env_host default|set\n");
      return 2;
    }
  set = strcmp (argv[1], "set") == 0;
  printf ("S9-10 %s: sizeof gomp_thread %zu, release at %zu; sizeof gomp_task %zu, stride %zu, "
	  "implicit_task at %zu\n", argv[1], sizeof (struct gomp_thread),
	  offsetof (struct gomp_thread, release), sizeof (struct gomp_task),
	  (size_t) GOMP_IMPLICIT_TASK_STRIDE, offsetof (struct gomp_team, implicit_task));

  /* As omp_get_schedule.  */
  kind = gomp_icv (false)->run_sched_var;
  chunk = gomp_icv (false)->run_sched_chunk_size;
  printf ("run-sched-var: kind 0x%x chunk %d\n", (unsigned) kind, chunk);
  capture_display ();
  if (!set)
    {
      expect ((kind & ~omp_sched_monotonic) == omp_sched_static && chunk < 1,
	      "schedule(runtime) without OMP_SCHEDULE is static with the default chunk");
      expect (has_line ("  [host] OMP_SCHEDULE = 'STATIC'"), "display: OMP_SCHEDULE = 'STATIC'");
      expect (has_line ("  [host] MALLOC_ARENA_MAX = ''"), "display: MALLOC_ARENA_MAX = ''");
      const char *start = strstr (display, KNC_HINT);
      char hint[1024] = "";
      if (start)
	sscanf (start, "%1023[^\n]", hint);
      expect (strstr (hint, "MALLOC_ARENA_MAX=60") && strstr (hint, "OMP_STACKSIZE="),
	      "display: the KNC hint names MALLOC_ARENA_MAX=60 and OMP_STACKSIZE");
    }
  else
    {
      expect (kind == omp_sched_dynamic && chunk == 4, "OMP_SCHEDULE=dynamic,4 overrides the default");
      expect (has_line ("  [host] OMP_SCHEDULE = 'DYNAMIC,4'"), "display: OMP_SCHEDULE = 'DYNAMIC,4'");
      expect (has_line ("  [host] MALLOC_ARENA_MAX = '60'"), "display: MALLOC_ARENA_MAX = '60'");
      expect (strstr (display, KNC_HINT) == NULL, "display: no KNC hint when both are set");
    }
  if (failed)
    printf ("--- display ---\n%s---\n", display);
  printf ("%s S9-10 host %s: %d failed\n", failed ? "FAIL" : "PASS", argv[1], failed);
  return failed != 0;
}
