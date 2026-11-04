/* { dg-options "-ffast-math" } */
// S3-07: reduced from gcc.c-torture/compile/acc1.c (bar).
// options: -O3 -ffast-math
double
knc_product (int n, double f)
{
  if (n == 0)
    return f;
  return f * knc_product (n - 1, f);
}
