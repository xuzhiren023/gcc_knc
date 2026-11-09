/* S9-06: reductions on long, double, max and an array section.  */
#include "check.h"
#define N 200000

int main (void)
{
  long isum = 0;
  double dsum = 0;
  int maxv = -1;
  long bins[4] = { 0, 0, 0, 0 };
#pragma omp parallel for reduction(+:isum, dsum) reduction(max:maxv) reduction(+:bins[0:4])
  for (int i = 1; i <= N; i++)
    {
      isum += i;
      dsum += 0.5;
      if ((int) ((long) i * 7919 % N) > maxv)
        maxv = (int) ((long) i * 7919 % N);
      bins[i % 4]++;
    }
  CHECK (isum == (long) N * (N + 1) / 2);
  CHECK (dsum == N * 0.5);
  CHECK (maxv == N - 1);
  CHECK (bins[0] == N / 4 && bins[1] == N / 4 && bins[2] == N / 4 && bins[3] == N / 4);
  return report ("reduction", team_size ());
}
