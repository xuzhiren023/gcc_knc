/* Reduced from gcc.dg/vect/pr53185-2.c; S6-07 baseline ICE. */
void __attribute__((noinline,noclone))
fn1 (int * __restrict f, int * __restrict d, unsigned short a, int c)
{
  unsigned short e;
  for (e = 0; e < a; ++e)
    f[e] = d[e * c];
}
extern void abort (void);
