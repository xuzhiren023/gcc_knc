/* S9-08 host test of GOMP_KNC_DELAY and the KNC default spin count
   (docs/research/knc-libgomp.md section 4, ticket C).

   tools/s9_08_checks.py host compiles this with the k1om config_path as the include path, so
   spincount.h below is the file the k1om runtime's env.c includes, and libgomp.h is the shim
   next to this file.  Each case sets or clears GOMP_KNC_DELAY and runs what env.c runs at
   startup on k1om: gomp_knc_init_delay, then, with neither GOMP_SPINCOUNT nor
   OMP_WAIT_POLICY, do_adjust_default_spincount.  Expected: a positive 32-bit decimal count is
   taken; anything else is reported once and the default delay of 128 is kept (S9-24, from S9-08's
   card data); the default spin count is 200 msec in delay periods at the clock this machine's
   /proc/cpuinfo gives (S9-24, from S9-15's), 200000 * MHz / delay, at least 1; the verbose
   omp_display_env line shows the delay in use.  The exact counts at the cards' clocks are
   tests/regress/s9_12/topology_host.c's.  */
#include "spincount.h"

#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

/* As config/linux/knc/mutex.c.  */
unsigned int gomp_knc_delay = GOMP_KNC_DELAY_DEFAULT;
unsigned long long gomp_spin_count_var;

static int errors;

void
gomp_error (const char *fmt, ...)
{
  va_list ap;
  va_start (ap, fmt);
  printf ("  libgomp: ");
  vprintf (fmt, ap);
  printf ("\n");
  va_end (ap);
  errors++;
}

static const struct test_case
{
  const char *value;		/* GOMP_KNC_DELAY, or NULL when it is not set.  */
  unsigned int delay;		/* Expected gomp_knc_delay.  */
  int errors;			/* Expected reports.  */
} cases[] =
{
  { NULL, 128, 0 },
  { "32", 32, 0 },
  { " 512 ", 512, 0 },
  { "1", 1, 0 },
  { "4294967295", 4294967295u, 0 },
  { "", 128, 1 },
  { "0", 128, 1 },
  { "-32", 128, 1 },
  { "32x", 128, 1 },
  { "abc", 128, 1 },
  { "4294967296", 128, 1 }
};

int
main (void)
{
  int failed = 0;
  unsigned int mhz = gomp_knc_read_mhz ("");
  printf ("clock %u MHz\n", mhz);
  for (size_t i = 0; i < sizeof cases / sizeof cases[0]; i++)
    {
      const struct test_case *c = &cases[i];
      unsigned long long spin = 200000ULL * mhz / c->delay;
      if (spin == 0)
	spin = 1;
      if (c->value)
	setenv ("GOMP_KNC_DELAY", c->value, 1);
      else
	unsetenv ("GOMP_KNC_DELAY");
      gomp_knc_delay = GOMP_KNC_DELAY_DEFAULT;
      gomp_spin_count_var = 300000;
      errors = 0;

      gomp_knc_init_delay ();
      do_adjust_default_spincount ();

      char want[64], got[64] = "";
      snprintf (want, sizeof want, "  [host] GOMP_KNC_DELAY = '%u'\n", c->delay);
      FILE *f = tmpfile ();
      if (f)
	{
	  gomp_knc_display_delay (f);
	  rewind (f);
	  if (!fgets (got, sizeof got, f))
	    got[0] = '\0';
	  fclose (f);
	}

      bool ok = (gomp_knc_delay == c->delay && gomp_spin_count_var == spin
		 && errors == c->errors && strcmp (got, want) == 0);
      printf ("%s GOMP_KNC_DELAY=%s%s%s: delay %u (want %u), spin count %llu (want %llu), "
	      "%d reports (want %d), display \"%.*s\"\n",
	      ok ? "ok  " : "FAIL", c->value ? "'" : "", c->value ? c->value : "unset",
	      c->value ? "'" : "", gomp_knc_delay, c->delay, gomp_spin_count_var, spin,
	      errors, c->errors, (int) strcspn (got, "\n"), got);
      failed += !ok;
    }
  printf ("%s S9-08 GOMP_KNC_DELAY: %d of %d cases\n", failed ? "FAIL" : "PASS",
	  (int) (sizeof cases / sizeof cases[0]) - failed, (int) (sizeof cases / sizeof cases[0]));
  return failed != 0;
}
