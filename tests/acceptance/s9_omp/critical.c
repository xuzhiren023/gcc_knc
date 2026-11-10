/* S9-06: critical, named critical and atomic capture under contention.  */
#include "check.h"
#define ITERS 2000

int main (void)
{
  long crit = 0, named = 0, atom = 0, last = 0;
  int nt = team_size ();
#pragma omp parallel
  for (int i = 0; i < ITERS; i++)
    {
#pragma omp critical
      crit++;
#pragma omp critical(other)
      named += 2;
      long v;
#pragma omp atomic capture
      v = ++atom;
      if (v == (long) nt * ITERS)
        last = v;
    }
  CHECK (crit == (long) nt * ITERS);
  CHECK (named == 2L * nt * ITERS);
  CHECK (atom == (long) nt * ITERS);
  CHECK (last == atom);
  return report ("critical", nt);
}
