/* Reduced from gcc.dg/vect/vect-strided-epilogue-1.c; S6-07 baseline ICE. */
void
f (int *x, short *y, int z)
{
  for (int i = 0; i < 0x82; ++i)
    x[-i] += x[z * i];
}
