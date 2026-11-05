// S3-09: an int loop vectorizes with vpaddd.  S4-04: k1om has no vpaddq or
// vpsubq (ADR-0005), so the same loops on long vectorize through the IMCI
// carry form (ADR-0007 point 6): the low dwords swapped into the odd lanes
// with {cdab}, an unmasked vpaddsetcd/vpsubsetbd for the carry, vpaddd/vpsubd,
// and vpadcd/vpsbbd adding the carry into the high dwords under a k1-k7 mask.
// options: -O2 -ftree-vectorize
// scan-asm-func add_int: \bvpaddd\s[^\n]*%zmm\d+
// scan-asm-func add_long: \bvmovdqa32\s+%zmm\d+\{cdab\},\s*%zmm\d+\s*$
// scan-asm-func add_long: \bvpaddsetcd\s+%zmm\d+\{cdab\},\s*%k[0-7],\s*%zmm\d+\s*$
// scan-asm-func add_long: \bvpaddd\s+%zmm\d+,\s*%zmm\d+,\s*%zmm\d+\s*$
// scan-asm-func add_long: \bvpadcd\s+%zmm\d+,\s*%k[0-7],\s*%zmm\d+\{%k[1-7]\}\s*$
// scan-asm-func sub_long: \bvmovdqa32\s+%zmm\d+\{cdab\},\s*%zmm\d+\s*$
// scan-asm-func sub_long: \bvpsubsetbd\s+%zmm\d+\{cdab\},\s*%k[0-7],\s*%zmm\d+\s*$
// scan-asm-func sub_long: \bvpsubd\s+%zmm\d+,\s*%zmm\d+,\s*%zmm\d+\s*$
// scan-asm-func sub_long: \bvpsbbd\s+%zmm\d+,\s*%k[0-7],\s*%zmm\d+\{%k[1-7]\}\s*$
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

void
sub_long (long *restrict c, const long *restrict a, const long *restrict b,
	  int n)
{
  for (int i = 0; i < n; i++)
    c[i] = a[i] - b[i];
}
