// S8-07 (E5-14): an int32 multiply-add becomes one vpmadd231d
// (zmm1 += zmm2 * zmm3, modular int32; Intel 327364-001 VPMADD231D), not
// vpmulld + vpaddd.  Exact, so no flag is needed.  Card check of the
// wrapping values: tests/t2/knc-vec-imadd.c.
// options: -O2 -ftree-vectorize -march=knc
// scan-asm-func madd: \bvpmadd231d\s[^\n]*%zmm\d+
// scan-asm-loop-not madd: \bvpmulld\b
// scan-asm-func acc: \bvpmadd231d\s[^\n]*%zmm\d+
// scan-asm-loop-not acc: \bvpmulld\b
// scan-asm-func index2d: \bvpmadd231d\s[^\n]*%zmm\d+
// scan-asm-loop-not index2d: \bvpmulld\b

void
madd (int *restrict x, const int *restrict a, const int *restrict b,
      const int *restrict c, int n)
{
  for (int i = 0; i < n; i++)
    x[i] = a[i] * b[i] + c[i];
}

void
acc (int *restrict c, const int *restrict a, const int *restrict b, int n)
{
  for (int i = 0; i < n; i++)
    c[i] += a[i] * b[i];
}

/* Flat 2-D index math, j * nx + i, with a loop-invariant multiplier.  */
void
index2d (int *restrict x, const int *restrict j, const int *restrict i, int nx,
         int n)
{
  for (int k = 0; k < n; k++)
    x[k] = j[k] * nx + i[k];
}
