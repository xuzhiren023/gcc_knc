/* S1-06: integer-only default link. Until E2-05 supplies GCC 16 libgcc,
   tools/check --compiler gcc16 --link-defaults uses -B to the shared donor's
   lib/gcc/k1om-mpss-linux/5.1.1 for crtbegin.o, crtend.o and libgcc.
   The executable is inspected on the host; the card is on the owner's hold. */
int main(void) { return 0; }
