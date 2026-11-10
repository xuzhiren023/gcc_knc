/* S9-06: simple and nested locks, omp_test_lock, omp_get_wtime and omp_get_wtick.  */
#include "check.h"

static omp_nest_lock_t nest;
static long nested_count;

static void enter (int depth)
{
  omp_set_nest_lock (&nest);
  nested_count++;
  if (depth > 0)
    enter (depth - 1);
  omp_unset_nest_lock (&nest);
}

int main (void)
{
  omp_lock_t lock;
  long plain = 0;
  int nt = team_size (), test_ok = 0;
  omp_init_lock (&lock);
  omp_init_nest_lock (&nest);
  double t0 = omp_get_wtime ();
#pragma omp parallel
  for (int i = 0; i < 500; i++)
    {
      omp_set_lock (&lock);
      plain++;
      omp_unset_lock (&lock);
      enter (2);
    }
  omp_set_lock (&lock);
#pragma omp parallel num_threads(2)
  if (omp_get_thread_num () == 1)
    test_ok = omp_test_lock (&lock) == 0;
  omp_unset_lock (&lock);
  double t1 = omp_get_wtime ();
  CHECK (plain == 500L * nt);
  CHECK (nested_count == 1500L * nt);
  CHECK (test_ok || nt == 1);
  /* The tick is clock_getres (CLOCK_MONOTONIC), the card kernel's timer resolution, which was
     coarser than 1 ms on the card (2026-11-10); OpenMP only requires it to be positive.  */
  printf ("omp_get_wtick %g
", omp_get_wtick ());
  CHECK (t1 >= t0 && omp_get_wtick () > 0);
  omp_destroy_lock (&lock);
  omp_destroy_nest_lock (&nest);
  return report ("locks", nt);
}
