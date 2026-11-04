// S3-09: an int loop vectorizes with vpaddd.  The same loop on long has no
// 64-bit vector add on k1om (ADR-0005), so it stays scalar and assembles.
// options: -O2 -ftree-vectorize
// scan-asm-func add_int: \bvpaddd\s[^\n]*%zmm\d+
// scan-asm-func add_long: \A(?![\s\S]*%zmm)[\s\S]*\baddq\s[^\n]*\(
// scan-asm-not: %(?:xmm|ymm)\d

void
add_int (int *restrict c, const int *restrict a, const int *restrict b, int n)
{
  for (int i = 0; i < n; i++)
    c[i] = a[i] + b[i];
}

void
add_long (long *restrict c, const long *restrict a, const long *restrict b,
	  int n)
{
  for (int i = 0; i < n; i++)
    c[i] = a[i] + b[i];
}
