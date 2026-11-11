/* S9-15 host test of the KNC spin-count arithmetic (config/linux/knc/card.h): the GOMP_SPINCOUNT
   that spins for 3, 30 and 200 msec in DELAY periods of 128 cycles at a 5110P's 1100 MHz and a
   7120's 1238 MHz.  tools/s9_15_checks.py host compiles this against the lane's card.h; the card
   runner (tools/s9_15_checks.py build) sets GOMP_SPINCOUNT from the same function.

   Expected: msec * 1000 * mhz / delay cycles, rounded down, at least 1; the default of
   gomp_knc_default_spincount is the same arithmetic for 200 msec (S9-24).  */
#include "card.h"

static const struct test_case
{
  unsigned int msec, mhz, delay;
  unsigned long long spin;
} cases[] =
{
  { 3, 1100, 128, 25781 },
  { 30, 1100, 128, 257812 },
  { 200, 1100, 128, 1718750 },
  { 3, 1238, 128, 29015 },
  { 30, 1238, 128, 290156 },
  { 200, 1238, 128, 1934375 },
  /* Extremes: no overflow at the largest delay and a long spin, never 0.  */
  { 200, 1238, 4294967295u, 1 },
  { 0, 1100, 128, 1 },
  { 4000000, 100000, 1, 400000000000000ULL }
};

int
main (void)
{
  int failed = 0, n = (int) (sizeof cases / sizeof cases[0]);
  for (int i = 0; i < n; i++)
    {
      const struct test_case *c = &cases[i];
      unsigned long long got = gomp_knc_spincount (c->msec, c->mhz, c->delay);
      bool ok = got == c->spin;
      printf ("%s %u msec at %u MHz, DELAY %u: spin count %llu (want %llu)\n", ok ? "ok  " : "FAIL",
	      c->msec, c->mhz, c->delay, got, c->spin);
      failed += !ok;
    }
  for (unsigned int mhz = 1100; mhz <= 1238; mhz += 138)
    for (unsigned int delay = 32; delay <= 128; delay *= 4)
      {
	unsigned long long want = gomp_knc_spincount (200, mhz, delay);
	unsigned long long got = gomp_knc_default_spincount (mhz, delay);
	bool ok = got == want;
	printf ("%s default at %u MHz, DELAY %u: %llu (want the 200 msec count %llu)\n",
		ok ? "ok  " : "FAIL", mhz, delay, got, want);
	failed += !ok;
	n++;
      }
  printf ("%s S9-15 spin count: %d of %d cases\n", failed ? "FAIL" : "PASS", n - failed, n);
  return failed != 0;
}
