// S5-21: retain the donor's stack ABI after V16HI became a transport mode.
// Reduced to foo from gcc.c-torture/execute/pr109040.c.
// options: -O2 -march=knc
// scalar_abi.t1_short_vector checks offset 8 relative to entry RSP.
// scan-asm-not: %[xy]mm\d+
typedef unsigned short __attribute__((__vector_size__ (32))) V;

unsigned short a, b, c, d;

void
foo (V m, unsigned short *ret)
{
  V v = 6 > ((V) { 2124, 8 } & m);
  unsigned short uc = v[0] + a + b + c + d;
  *ret = uc;
}
