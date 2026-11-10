/* S9-12 host test of the core count and the spin count libgomp reads from the KNC card
   (libgomp/config/linux/knc/card.h), instead of a 7120's 60 cores and a 5110P's 1.1 GHz.

   tools/s9_12_checks.py host compiles this with the Cygwin GCC against the lane's card.h and
   runs it with a scratch directory, where it writes fixture /proc and /sys trees of KNC cards:
   CPUs 4C+1..4C+4 on core C and CPU 0 on the last core with the three highest CPUs, as the card
   numbers them.

   - 57 cores (3120), 60 (5110P), 61 (7120): sysfs thread_siblings_list, /proc/cpuinfo with
     "core id" and "cpu MHz" 1100.000, 1052.630 and 1238.094, and cpu/online; the count is the
     cores without the OS core, 56, 59 and 60;
   - the 57-core tree without sysfs topology (from cpuinfo's core id), and with neither (from the
     online CPUs over four);
   - an empty tree: 60 cores and 1100 MHz, the fallbacks;
   - the spin count: 3 msec at the clock in DELAY periods, 103125 at 1100 MHz and delay 32.  */
#include "card.h"

#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

static int failed;

static void
expect (int ok, const char *what)
{
  printf ("%s %s\n", ok ? "ok  " : "FAIL", what);
  failed += !ok;
}

static void
mkdirs (const char *path)
{
  char buf[1024];
  char *p;

  snprintf (buf, sizeof buf, "%s", path);
  for (p = buf + 1; *p; p++)
    if (*p == '/')
      {
	*p = '\0';
	mkdir (buf, 0755);
	*p = '/';
      }
  mkdir (buf, 0755);
}

static FILE *
create (const char *root, const char *rel)
{
  char path[1024], dir[1024];
  char *slash;

  snprintf (path, sizeof path, "%s%s", root, rel);
  snprintf (dir, sizeof dir, "%s", path);
  slash = strrchr (dir, '/');
  *slash = '\0';
  mkdirs (dir);
  return fopen (path, "w");
}

/* The core of CPU I on an N-core card.  */
static unsigned
core_of (unsigned i, unsigned n)
{
  return i == 0 ? n - 1 : (i - 1) / 4;
}

/* The first sibling of core C: CPU 0 for the last core.  */
static unsigned
first_sibling (unsigned c, unsigned n)
{
  return c == n - 1 ? 0 : 4 * c + 1;
}

static void
card_tree (const char *root, unsigned n, const char *mhz, int sysfs, int cpuinfo)
{
  unsigned i;
  FILE *f;

  mkdirs (root);
  f = create (root, "/sys/devices/system/cpu/online");
  fprintf (f, "0-%u\n", 4 * n - 1);
  fclose (f);
  if (sysfs)
    for (i = 0; i < 4 * n; i++)
      {
	char rel[128];
	unsigned c = core_of (i, n), s = first_sibling (c, n);
	snprintf (rel, sizeof rel, "/sys/devices/system/cpu/cpu%u/topology/thread_siblings_list", i);
	f = create (root, rel);
	if (c == n - 1)
	  fprintf (f, "0,%u-%u\n", 4 * n - 3, 4 * n - 1);
	else
	  fprintf (f, "%u-%u\n", s, s + 3);
	fclose (f);
      }
  f = create (root, "/proc/cpuinfo");
  for (i = 0; i < 4 * n; i++)
    {
      fprintf (f, "processor\t: %u\nvendor_id\t: GenuineIntel\ncpu family\t: 11\nmodel\t\t: 1\n", i);
      if (cpuinfo)
	fprintf (f, "cpu MHz\t\t: %s\ncore id\t\t: %u\n", mhz, core_of (i, n));
      fputs ("\n", f);
    }
  fclose (f);
}

int
main (int argc, char **argv)
{
  static const struct { unsigned cores; const char *mhz; unsigned want_mhz; } cards[] = {
    { 57, "1100.000", 1100 }, { 60, "1052.630", 1053 }, { 61, "1238.094", 1238 },
  };
  char root[600], what[200];
  unsigned i, got;

  if (argc != 2)
    {
      fprintf (stderr, "usage: topology_host SCRATCH-DIR\n");
      return 2;
    }

  for (i = 0; i < 3; i++)
    {
      snprintf (root, sizeof root, "%s/card%u", argv[1], cards[i].cores);
      card_tree (root, cards[i].cores, cards[i].mhz, 1, 1);
      got = gomp_knc_count_cores (root);
      snprintf (what, sizeof what, "%u-core card, sysfs: %u cores without the OS core (want %u)",
		cards[i].cores, got, cards[i].cores - 1);
      expect (got == cards[i].cores - 1, what);
      got = gomp_knc_read_mhz (root);
      snprintf (what, sizeof what, "%u-core card: cpu MHz %s read as %u", cards[i].cores,
		cards[i].mhz, got);
      expect (got == cards[i].want_mhz, what);
    }

  snprintf (root, sizeof root, "%s/cpuinfo57", argv[1]);
  card_tree (root, 57, "1100.000", 0, 1);
  got = gomp_knc_count_cores (root);
  snprintf (what, sizeof what, "57-core card, no sysfs topology: %u cores from core id (want 56)", got);
  expect (got == 56, what);

  snprintf (root, sizeof root, "%s/online57", argv[1]);
  card_tree (root, 57, NULL, 0, 0);
  got = gomp_knc_count_cores (root);
  snprintf (what, sizeof what, "57-core card, online CPUs only: %u cores (want 56)", got);
  expect (got == 56, what);
  got = gomp_knc_read_mhz (root);
  snprintf (what, sizeof what, "no cpu MHz: %u (want %u)", got, GOMP_KNC_MHZ_DEFAULT);
  expect (got == 1100, what);

  snprintf (root, sizeof root, "%s/empty", argv[1]);
  mkdirs (root);
  got = gomp_knc_count_cores (root);
  snprintf (what, sizeof what, "nothing readable: %u cores (want 60)", got);
  expect (got == 60, what);
  got = gomp_knc_read_mhz (root);
  snprintf (what, sizeof what, "nothing readable: %u MHz (want 1100)", got);
  expect (got == 1100, what);

  expect (gomp_knc_default_spincount (1100, 32) == 103125, "spin count at 1100 MHz, delay 32: 103125");
  expect (gomp_knc_default_spincount (1238, 32) == 116062, "spin count at 1238 MHz, delay 32: 116062");
  expect (gomp_knc_default_spincount (1053, 64) == 49359, "spin count at 1053 MHz, delay 64: 49359");
  expect (gomp_knc_default_spincount (1, 100000) == 1, "spin count never 0");

  printf ("%s S9-12 topology host: %d failed\n", failed ? "FAIL" : "PASS", failed);
  return failed != 0;
}
