/* S1-06: integer-only default link. Until E2-05 supplies GCC 16 libgcc,
   tools/check --compiler gcc16 --link-defaults uses -B to the shared donor's
   lib/gcc/k1om-mpss-linux/5.1.1 for crtbegin.o, crtend.o and libgcc.
   A test-local -L directory supplies libgcc_s_asneeded.so and
   libatomic_asneeded.so linker scripts matching libatomic/Makefile.am.
   -L to cross/k1om-mpss-linux/lib64 resolves the donor shared libraries.
   Both bridges go away at E2-05. The integer main must not acquire a
   DT_NEEDED entry for either libgcc_s or libatomic.
   The executable is inspected on the host; the card is on the owner's hold. */
/* Variable integer division requires __divti3, proving that the link really
   uses the donor libgcc archive rather than merely searching its directory. */
int main(void)
{
  volatile __int128 dividend = 84;
  volatile __int128 divisor = 7;
  return dividend / divisor != 12;
}
