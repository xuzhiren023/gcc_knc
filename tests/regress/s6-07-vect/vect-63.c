/* Reduced from gcc.dg/vect/vect-63.c; S6-07 baseline ICE. */
extern void abort(void);
#define N 16
__attribute__ ((noinline))
int main1 ()
{
  int i, j;
  int ib[N] = {0,3,6,9,12,15,18,21,24,27,30,33,36,39,42,45};
  int ia[N*2][4][N];
  for (i = 0; i < N; i++)
    {
      for (j = 0; j < N; j++)
        {
           ia[i + j][1][j] = ib[i];
        }
    }
  for (i = 0; i < N; i++)
    {
#pragma GCC novector
      for (j = 0; j < N; j++)
        {
           if (ia[i + j][1][j] != ib[i])
              abort();
        }
    }
  return 0;
}
