/* S9 acceptance (lead-owned): each program prints one result line, compared byte for byte on the
   host. Built with -DBREAK, the first check of every program is inverted, so each one can go red.
   The thread count goes on its own line, so the result line is the same at 60x1 and 60x4.  */
#include <omp.h>
#include <stdio.h>
#ifdef BREAK
static const int break_first = 1;
#else
static const int break_first = 0;
#endif
static int checks, failures;
#define CHECK(cond)                                                     \
  do {                                                                  \
    int ok_ = (cond) ? 1 : 0;                                           \
    ++checks;                                                           \
    if (break_first && checks == 1)                                     \
      ok_ = !ok_;                                                       \
    if (!ok_) {                                                         \
      ++failures;                                                       \
      printf ("check %d failed: %s\n", checks, #cond);                  \
    }                                                                   \
  } while (0)

static int report (const char *name, int threads)
{
  printf ("S9-OMP %s threads=%d\n", name, threads);
  printf ("S9-OMP %s %s checks=%d failures=%d\n", name, failures ? "FAIL" : "PASS", checks, failures);
  return failures != 0;
}

static int team_size (void)
{
  int n = 0;
#pragma omp parallel
#pragma omp single
  n = omp_get_num_threads ();
  return n;
}
