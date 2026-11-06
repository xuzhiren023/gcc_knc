/* Reduced from gcc.dg/vect/vect-strided-store.c; S6-07 baseline ICE. */
void __attribute__((noinline))
sumit (float * __restrict dest,
       float * __restrict src, float * __restrict src2,
       int stride, int n)
{
  int i;
  for (i = 0; i < n; i++)
    dest[i*stride] = src[i] + src2[i];
}
