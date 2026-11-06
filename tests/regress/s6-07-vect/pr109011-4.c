/* Reduced from gcc.dg/vect/pr109011-4.c; S6-07 baseline ICE. */
void baz(long long *p, long long *q) {
  for (int i=0; i<2048; ++i) p[i]=__builtin_ffsll(q[i]);
}
