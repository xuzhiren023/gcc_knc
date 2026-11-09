/* S9-06 and S9-09: recursive tasks with taskwait, 10,000 sibling tasks, a taskgroup of nested tasks.  */
#include "check.h"

static long fib (int n)
{
  long a, b;
  if (n < 2)
    return n;
  if (n < 12)
    return fib (n - 1) + fib (n - 2);
#pragma omp task shared(a)
  a = fib (n - 1);
#pragma omp task shared(b)
  b = fib (n - 2);
#pragma omp taskwait
  return a + b;
}

int main (void)
{
  long f = 0, done = 0, grouped = 0;
#pragma omp parallel
#pragma omp single
  {
    f = fib (27);
    for (int i = 0; i < 10000; i++)
      {
#pragma omp task
        {
#pragma omp atomic
          done++;
        }
      }
#pragma omp taskwait
#pragma omp taskgroup
    for (int i = 0; i < 100; i++)
      {
#pragma omp task
        {
#pragma omp task
          {
#pragma omp atomic
            grouped++;
          }
        }
      }
  }
  CHECK (f == 196418);
  CHECK (done == 10000);
  CHECK (grouped == 100);
  return report ("tasks", team_size ());
}
