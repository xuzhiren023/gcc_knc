/* S2-15: the lead runs the -Ofast executable on the card.  */
#include <stdio.h>

int
main (void)
{
  unsigned int mxcsr;
  __asm__ volatile ("stmxcsr %0" : "=m" (mxcsr));
  printf ("MXCSR after startup: 0x%08x FTZ=%u DAZ=%u\n",
          mxcsr, (mxcsr >> 15) & 1, (mxcsr >> 6) & 1);
  return 0;
}
