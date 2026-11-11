/* S9-12 host test of the KNC malloc arena cap (ADR-0012 point 3).

   tools/s9_12_checks.py host compiles this with the Cygwin GCC against the lane's
   libgomp/config/linux/knc/card.h, the code libgomp on k1om runs at load, and runs it once.
   The host is x86-64 LP64 like k1om.  Inputs are fixtures, not this machine's:

   - MemTotal of the three cards (3120 6 GB, 5110P 8 GB, 7120 16 GB; the kernel keeps some back),
     244/240/228 CPUs, 8 MiB stacks (RLIMIT_STACK) and 2 MiB (OMP_STACKSIZE=2M);
   - with no RLIMIT_AS and no strict overcommit (one arena per CPU: reservations then cost no
     memory; S9-24 from measurement 7), with RLIMIT_AS 6, 8 and 10 GiB (card_run's memoryMB);
     strict overcommit (CommitLimit); a user MALLOC_ARENA_MAX, which wins;
   - a fixture /proc tree under argv[1] for the meminfo and overcommit readers.

   Expected caps are computed here from the rule, written out: the largest N with
   N * 64 MiB + CPUs * stack + reserve <= budget, at most the CPUs, at least the minimum.  */
#include "card.h"

#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

#define KB(x) ((unsigned long long) (x) << 10)
#define MIB(x) ((unsigned long long) (x) << 20)
#define GIB(x) ((unsigned long long) (x) << 30)

static int failed;

static void
expect (int ok, const char *what)
{
  printf ("%s %s\n", ok ? "ok  " : "FAIL", what);
  failed += !ok;
}

/* The rule, independent of card.h's arithmetic.  */
static unsigned long
rule (unsigned long long budget, unsigned long cpus, unsigned long long stack)
{
  unsigned long n = 0;

  while (n < cpus
	 && (n + 1) * MIB (64) + cpus * stack + GOMP_KNC_ARENA_RESERVE <= budget)
    n++;
  if (n < GOMP_KNC_ARENA_MIN && n < cpus)
    n = GOMP_KNC_ARENA_MIN < cpus ? GOMP_KNC_ARENA_MIN : cpus;
  return n;
}

struct card
{
  const char *name;
  unsigned long long mem_total;
  unsigned long cpus;
};

/* MemTotal as such cards report it (kB), and the CPUs of a whole-card mask.  */
static const struct card cards[] = {
  { "3120", KB (5853148), 228 },
  { "5110P", KB (7882348), 240 },
  { "7120", KB (15948328), 244 },
};

static void
check (const char *what, const struct gomp_knc_mem *in, unsigned long want,
       enum gomp_knc_budget kind)
{
  struct gomp_knc_arena a;
  unsigned long got = gomp_knc_arena_decide (NULL, in, &a);
  char line[256];

  snprintf (line, sizeof line, "%s: cap %lu (want %lu), budget kind %d (want %d)", what, got,
	    want, (int) a.budget_kind, (int) kind);
  expect (got == want && a.cap == want && a.source == GOMP_KNC_ARENA_DERIVED
	  && a.budget_kind == kind, line);
}

static void
write_file (const char *path, const char *text)
{
  FILE *f = fopen (path, "w");
  fputs (text, f);
  fclose (f);
}

int
main (int argc, char **argv)
{
  static const unsigned long long stacks[] = { MIB (8), MIB (2) };
  static const unsigned long long limits[] = { GIB (6), GIB (8), GIB (10) };
  struct gomp_knc_mem in;
  struct gomp_knc_arena a;
  char what[128], root[512], path[600], display[512];
  unsigned int c, s, l;

  if (argc != 2)
    {
      fprintf (stderr, "usage: arena_host FIXTURE-DIR\n");
      return 2;
    }

  for (c = 0; c < 3; c++)
    for (s = 0; s < 2; s++)
      {
	memset (&in, 0, sizeof in);
	in.mem_total = cards[c].mem_total;
	in.commit_limit = cards[c].mem_total / 2;
	in.overcommit = 0;
	in.rlimit_as = GOMP_KNC_NO_LIMIT;
	in.cpus = cards[c].cpus;
	in.stack = stacks[s];
	snprintf (what, sizeof what, "%s, %llu MiB stacks, no RLIMIT_AS", cards[c].name,
		  stacks[s] >> 20);
	check (what, &in, in.cpus, GOMP_KNC_BUDGET_NONE);
	in.overcommit = 1;
	snprintf (what, sizeof what, "%s, %llu MiB stacks, no RLIMIT_AS, overcommit 1",
		  cards[c].name, stacks[s] >> 20);
	check (what, &in, in.cpus, GOMP_KNC_BUDGET_NONE);
	in.overcommit = 0;
	for (l = 0; l < 3; l++)
	  {
	    in.rlimit_as = limits[l];
	    snprintf (what, sizeof what, "%s, %llu MiB stacks, RLIMIT_AS %llu GiB", cards[c].name,
		      stacks[s] >> 20, limits[l] >> 30);
	    check (what, &in, rule (limits[l], in.cpus, in.stack), GOMP_KNC_BUDGET_RLIMIT_AS);
	  }
	/* Strict overcommit: CommitLimit when it is below RLIMIT_AS or there is none.  */
	in.overcommit = 2;
	in.rlimit_as = GOMP_KNC_NO_LIMIT;
	snprintf (what, sizeof what, "%s, %llu MiB stacks, strict overcommit", cards[c].name,
		  stacks[s] >> 20);
	check (what, &in, rule (in.commit_limit, in.cpus, in.stack), GOMP_KNC_BUDGET_COMMIT_LIMIT);
	in.rlimit_as = GIB (6);
	snprintf (what, sizeof what, "%s, %llu MiB stacks, strict overcommit, RLIMIT_AS 6 GiB",
		  cards[c].name, stacks[s] >> 20);
	if (in.commit_limit < GIB (6))
	  check (what, &in, rule (in.commit_limit, in.cpus, in.stack), GOMP_KNC_BUDGET_COMMIT_LIMIT);
	else
	  check (what, &in, rule (GIB (6), in.cpus, in.stack), GOMP_KNC_BUDGET_RLIMIT_AS);
      }

  /* The S9-06 tasks case: a 7120 under card_run's 6 GiB with 8 MiB stacks fits fewer arenas
     than threads, and what it derives fits.  */
  memset (&in, 0, sizeof in);
  in.mem_total = cards[2].mem_total;
  in.overcommit = 0;
  in.rlimit_as = GIB (6);
  in.cpus = 244;
  in.stack = MIB (8);
  gomp_knc_arena_decide (NULL, &in, &a);
  expect (a.cap < 244 && a.cap * MIB (64) + 244 * MIB (8) + GOMP_KNC_ARENA_RESERVE <= GIB (6),
	  "7120 under 6 GiB, 8 MiB stacks: fewer arenas than CPUs, and they fit");

  /* Nothing read: as many arenas as CPUs.  */
  memset (&in, 0, sizeof in);
  in.overcommit = -1;
  in.rlimit_as = GOMP_KNC_NO_LIMIT;
  in.cpus = 240;
  in.stack = MIB (8);
  check ("nothing read", &in, 240, GOMP_KNC_BUDGET_NONE);

  /* A budget too small for the minimum still gives the minimum; few CPUs give their count.  */
  in.rlimit_as = MIB (512);
  check ("RLIMIT_AS 512 MiB", &in, GOMP_KNC_ARENA_MIN, GOMP_KNC_BUDGET_RLIMIT_AS);
  in.cpus = 4;
  check ("4 CPUs, RLIMIT_AS 512 MiB", &in, 4, GOMP_KNC_BUDGET_RLIMIT_AS);

  /* A user MALLOC_ARENA_MAX wins: no cap from libgomp, and the display says so.  An empty one
     is ignored by glibc, so libgomp derives.  */
  in.cpus = 240;
  in.rlimit_as = GIB (6);
  expect (gomp_knc_arena_decide ("64", &in, &a) == 0 && a.source == GOMP_KNC_ARENA_USER,
	  "MALLOC_ARENA_MAX=64: libgomp sets no cap");
  {
    FILE *f = tmpfile ();
    size_t n;
    gomp_knc_display_arena (f, &a);
    rewind (f);
    n = fread (display, 1, sizeof display - 1, f);
    display[n] = '\0';
    fclose (f);
  }
  expect (strcmp (display, "  [host] KNC malloc arena cap = '64' (user: MALLOC_ARENA_MAX)\n") == 0,
	  "display: user cap and its source");
  expect (gomp_knc_arena_decide ("", &in, &a) == rule (GIB (6), 240, MIB (8))
	  && a.source == GOMP_KNC_ARENA_DERIVED, "MALLOC_ARENA_MAX='': derived");
  {
    FILE *f = tmpfile ();
    size_t n;
    char want[256];
    gomp_knc_display_arena (f, &a);
    rewind (f);
    n = fread (display, 1, sizeof display - 1, f);
    display[n] = '\0';
    fclose (f);
    snprintf (want, sizeof want, "  [host] KNC malloc arena cap = '%lu' (derived: budget 6144 MiB "
	      "from RLIMIT_AS, 240 CPUs, 8192 KiB stacks)\n", a.cap);
    expect (strcmp (display, want) == 0, "display: derived cap with its budget");
  }

  /* Nothing bounds the reservations: one arena per CPU, and the display says why.  */
  in.cpus = 169;
  in.mem_total = cards[2].mem_total;
  in.overcommit = 0;
  in.rlimit_as = GOMP_KNC_NO_LIMIT;
  {
    FILE *f = tmpfile ();
    size_t n;
    gomp_knc_arena_decide (NULL, &in, &a);
    gomp_knc_display_arena (f, &a);
    rewind (f);
    n = fread (display, 1, sizeof display - 1, f);
    display[n] = '\0';
    fclose (f);
  }
  expect (strcmp (display, "  [host] KNC malloc arena cap = '169' (derived: budget none, "
		  "169 CPUs, 8192 KiB stacks)\n") == 0,
	  "display: one arena per CPU when nothing bounds the reservations");

  /* The readers, on a fixture /proc tree.  */
  snprintf (root, sizeof root, "%s/proc-7120", argv[1]);
  mkdir (root, 0755);
  snprintf (path, sizeof path, "%s/proc", root);
  mkdir (path, 0755);
  snprintf (path, sizeof path, "%s/proc/sys", root);
  mkdir (path, 0755);
  snprintf (path, sizeof path, "%s/proc/sys/vm", root);
  mkdir (path, 0755);
  snprintf (path, sizeof path, "%s/proc/meminfo", root);
  write_file (path, "MemTotal:       15948328 kB\nMemFree:        15000000 kB\n"
	      "CommitLimit:     7974164 kB\nCommitted_AS:     123456 kB\n");
  snprintf (path, sizeof path, "%s/proc/sys/vm/overcommit_memory", root);
  write_file (path, "2\n");
  {
    unsigned long long total, commit;
    gomp_knc_read_meminfo (root, &total, &commit);
    expect (total == KB (15948328) && commit == KB (7974164), "meminfo: MemTotal and CommitLimit");
    expect (gomp_knc_read_overcommit (root) == 2, "overcommit_memory: 2");
    snprintf (path, sizeof path, "%s/none", argv[1]);
    gomp_knc_read_meminfo (path, &total, &commit);
    expect (total == 0 && commit == 0 && gomp_knc_read_overcommit (path) == -1,
	    "missing /proc: zero and -1");
  }

  printf ("%s S9-12 arena host: %d failed\n", failed ? "FAIL" : "PASS", failed);
  return failed != 0;
}
