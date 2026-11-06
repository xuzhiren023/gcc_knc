/* Reduced from gcc.dg/vect/pr53185.c; S6-07 baseline ICE. */
void fn1(int *f, int *d, unsigned short n, int stride) {
  for (unsigned short i=0; i<n; ++i) f[i]=d[i*stride];
}
