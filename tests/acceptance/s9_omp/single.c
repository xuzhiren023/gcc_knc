/* S9-06: single and master run once; a barrier separates phases; ordered keeps iteration order.  */
#include "check.h"
#define N 1000

int main (void)
{
  int singles = 0, masters = 0, next = 0, in_order = 1, phase_ok = 1;
  int arr[256] = { 0 };
  int nt = team_size ();
#pragma omp parallel
  {
#pragma omp single
    singles++;
#pragma omp master
    masters++;
    int me = omp_get_thread_num ();
    if (me < 256)
      arr[me] = me + 1;
#pragma omp barrier
    int peer = (me + 1) % omp_get_num_threads ();
    if (peer < 256 && arr[peer] != peer + 1)
      {
#pragma omp atomic write
        phase_ok = 0;
      }
  }
#pragma omp parallel for ordered schedule(dynamic, 3)
  for (int i = 0; i < N; i++)
    {
#pragma omp ordered
      {
        if (next != i)
          in_order = 0;
        next++;
      }
    }
  CHECK (singles == 1);
  CHECK (masters == 1);
  CHECK (phase_ok);
  CHECK (in_order && next == N);
  return report ("single", nt);
}
