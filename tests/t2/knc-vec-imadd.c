/* S8-07 card check, run by the lead (vpmadd231d, E5-14):
   xgcc -B<build>/ -O2 -ftree-vectorize -march=knc tests/t2/knc-vec-imadd.c -o <shared>/imadd
   tools/card_run <shared>/imadd
   Every pair of edge values (INT_MIN, INT_MAX, -1, 0, 1, 2^16 and
   neighbours) times every addend edge, then pseudo-random values, through
   the vectorized x = a * b + c and c += a * b loops and a loop-invariant
   multiplier.  The reference is unsigned 64-bit arithmetic truncated to 32
   bits, without vectorization.  Prints PASS or the first mismatch.  */
#include <limits.h>
#include <stdio.h>
#include <stdint.h>

#define N 4099 /* not a multiple of 16: exercises the tail */
#define NOIPA __attribute__ ((noipa))

static int a[N] __attribute__ ((aligned (64)));
static int b[N] __attribute__ ((aligned (64)));
static int c[N] __attribute__ ((aligned (64)));
static int x[N] __attribute__ ((aligned (64)));

NOIPA void
madd (int *restrict x, const int *restrict a, const int *restrict b,
      const int *restrict c, int n)
{
  for (int i = 0; i < n; i++)
    x[i] = (int) ((unsigned) a[i] * (unsigned) b[i] + (unsigned) c[i]);
}

NOIPA void
acc (int *restrict c, const int *restrict a, const int *restrict b, int n)
{
  for (int i = 0; i < n; i++)
    c[i] = (int) ((unsigned) c[i] + (unsigned) a[i] * (unsigned) b[i]);
}

NOIPA void
index_madd (int *restrict x, const int *restrict j, const int *restrict i,
            int nx, int n)
{
  for (int k = 0; k < n; k++)
    x[k] = (int) ((unsigned) j[k] * (unsigned) nx + (unsigned) i[k]);
}

__attribute__ ((optimize ("no-tree-vectorize"), noipa)) static int
ref (int p, int q, int r)
{
  uint64_t v = (uint64_t) (uint32_t) p * (uint32_t) q + (uint32_t) r;
  return (int) (uint32_t) v;
}

static const int edge[] = { INT_MIN, INT_MIN + 1, -65537, -65536, -2, -1, 0,
                            1, 2, 3, 65535, 65536, 65537, 46341,
                            INT_MAX - 1, INT_MAX };
#define NE (int) (sizeof edge / sizeof edge[0])

static uint32_t seed = 12345;
static int
next (void)
{
  seed = seed * 1103515245u + 12345u;
  return (int) (seed ^ (seed >> 15));
}

static int failures;

static void
check (const char *what, int i, int got, int want)
{
  if (got != want && failures++ < 8)
    printf ("FAIL %s i=%d a=%d b=%d c=%d got=%d want=%d\n", what, i, a[i],
            b[i], c[i], got, want);
}

int
main (void)
{
  int n = 0;
  for (int p = 0; p < NE; p++)
    for (int q = 0; q < NE; q++)
      for (int r = 0; r < NE && n < N; r++, n++)
        a[n] = edge[p], b[n] = edge[q], c[n] = edge[r];
  for (; n < N; n++)
    a[n] = next (), b[n] = next (), c[n] = next ();

  madd (x, a, b, c, N);
  for (int i = 0; i < N; i++)
    check ("madd", i, x[i], ref (a[i], b[i], c[i]));

  for (int k = 0; k < NE; k++)
    {
      index_madd (x, a, c, edge[k], N);
      for (int i = 0; i < N; i++)
        check ("index", i, x[i], ref (a[i], edge[k], c[i]));
    }

  for (int i = 0; i < N; i++)
    x[i] = c[i];
  acc (x, a, b, N);
  for (int i = 0; i < N; i++)
    check ("acc", i, x[i], ref (a[i], b[i], c[i]));

  printf ("%s imadd values=%d failures=%d\n", failures ? "FAIL" : "PASS",
          N * (NE + 2), failures);
  return failures != 0;
}
