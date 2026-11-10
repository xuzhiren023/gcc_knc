/* S9-08 host test of GOMP_KNC_DELAY and the KNC default spin count
   (docs/research/knc-libgomp.md section 4, ticket C).

   tools/s9_08_checks.py host compiles this with the k1om config_path as the include path, so
   spincount.h below is the file the k1om runtime's env.c includes, and libgomp.h is the shim
   next to this file.  Each case sets or clears GOMP_KNC_DELAY and runs what env.c runs at
   startup on k1om: gomp_knc_init_delay, then, with neither GOMP_SPINCOUNT nor
   OMP_WAIT_POLICY, do_adjust_default_spincount.  Expected: a positive 32-bit decimal count is
   taken; anything else is reported once and the default delay of 32 is kept; the default spin
   count is 3 msec at 1.1 GHz in delay periods, 3300000 / delay, at least 1; the verbose
   omp_display_env line shows the delay in use.  */
#include "spincount.h"

#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

/* As config/linux/knc/mutex.c.  */
unsigned int gomp_knc_delay = 32;
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
  unsigned long long spin;	/* Expected default gomp_spin_count_var.  */
  int errors;			/* Expected reports.  */
} cases[] =
{
  { NULL, 32, 103125, 0 },
  { "128", 128, 25781, 0 },
  { " 512 ", 512, 6445, 0 },
  { "1", 1, 3300000, 0 },
  { "4294967295", 4294967295u, 1, 0 },
  { "", 32, 103125, 1 },
  { "0", 32, 103125, 1 },
  { "-32", 32, 103125, 1 },
  { "32x", 32, 103125, 1 },
  { "abc", 32, 103125, 1 },
  { "4294967296", 32, 103125, 1 }
};

int
main (void)
{
  int failed = 0;
  for (size_t i = 0; i < sizeof cases / sizeof cases[0]; i++)
    {
      const struct test_case *c = &cases[i];
      if (c->value)
	setenv ("GOMP_KNC_DELAY", c->value, 1);
      else
	unsetenv ("GOMP_KNC_DELAY");
      gomp_knc_delay = 32;
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

      bool ok = (gomp_knc_delay == c->delay && gomp_spin_count_var == c->spin
		 && errors == c->errors && strcmp (got, want) == 0);
      printf ("%s GOMP_KNC_DELAY=%s%s%s: delay %u (want %u), spin count %llu (want %llu), "
	      "%d reports (want %d), display \"%.*s\"\n",
	      ok ? "ok  " : "FAIL", c->value ? "'" : "", c->value ? c->value : "unset",
	      c->value ? "'" : "", gomp_knc_delay, c->delay, gomp_spin_count_var, c->spin,
	      errors, c->errors, (int) strcspn (got, "\n"), got);
      failed += !ok;
    }
  printf ("%s S9-08 GOMP_KNC_DELAY: %d of %d cases\n", failed ? "FAIL" : "PASS",
	  (int) (sizeof cases / sizeof cases[0]) - failed, (int) (sizeof cases / sizeof cases[0]));
  return failed != 0;
}
