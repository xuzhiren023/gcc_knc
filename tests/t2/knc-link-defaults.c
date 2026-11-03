/* S1-06: integer-only default link. Until E2-05 supplies GCC 16 libgcc,
   tools/check --compiler gcc16 --link-defaults uses -B to the shared donor's
   lib/gcc/k1om-mpss-linux/5.1.1 for crtbegin.o, crtend.o and libgcc.
   The executable is inspected on the host; the card is on the owner's hold. */
/* Variable integer division requires __divti3, proving that the link really
   uses the donor libgcc archive rather than merely searching its directory. */
int main(void)
{
  volatile __int128 dividend = 84;
  volatile __int128 divisor = 7;
  return dividend / divisor != 12;
}
