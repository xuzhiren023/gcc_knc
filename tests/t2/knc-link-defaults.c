/* S1-06 / S2-07: integer-only default link with fork-built runtime files.
   The integer main must not acquire a DT_NEEDED entry for either libgcc_s
   or libatomic. The executable is inspected on the host. */
/* Variable integer division requires __divti3, proving that the link really
   uses the fork's libgcc archive rather than merely searching its directory. */
int main(void)
{
  volatile __int128 dividend = 84;
  volatile __int128 divisor = 7;
  return dividend / divisor != 12;
}
