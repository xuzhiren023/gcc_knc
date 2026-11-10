/* S9-06: parallel for with static, dynamic and guided schedules; each iteration runs exactly once.  */
#include "check.h"
#include <stdlib.h>
#define N 100003

int main (void)
{
  int *hits = calloc (N, sizeof (int));
  long sum = 0;
#pragma omp parallel for schedule(static) reduction(+:sum)
  for (int i = 0; i < N; i++)
    {
      hits[i]++;
      sum += i;
    }
  CHECK (sum == (long) N * (N - 1) / 2);
#pragma omp parallel for schedule(dynamic, 7)
  for (int i = 0; i < N; i++)
    hits[i]++;
#pragma omp parallel for schedule(guided)
  for (int i = 0; i < N; i++)
    hits[i]++;
  int once = 1;
  for (int i = 0; i < N; i++)
    once &= hits[i] == 3;
  CHECK (once);
  int nt = team_size (), owner_ok = 1;
#pragma omp parallel for schedule(static, 1) reduction(&&:owner_ok)
  for (int i = 0; i < 4 * nt; i++)
    owner_ok = owner_ok && omp_get_thread_num () == i % nt;
  CHECK (owner_ok);
  free (hits);
  return report ("for", nt);
}
