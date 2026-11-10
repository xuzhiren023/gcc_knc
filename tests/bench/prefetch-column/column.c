/* S8-11: WRF-shaped column loop for compiler prefetch (lead note 2026-11-08).
   29 float arrays (28 read, 1 written), a k loop of 51 trips with a 1092-byte step
   (273 floats), 8-float rows.  Compiled twice by build.py, with -fprefetch-loop-arrays
   (NAME column_pf) and -fno-prefetch-loop-arrays (NAME column_nopf).  */
#include "column.h"

#define IN(m) const float *restrict in##m
#define SUM(x) (in0[x] + in1[x] + in2[x] + in3[x] + in4[x] + in5[x] + in6[x] + in7[x]       \
                + in8[x] + in9[x] + in10[x] + in11[x] + in12[x] + in13[x] + in14[x]          \
                + in15[x] + in16[x] + in17[x] + in18[x] + in19[x] + in20[x] + in21[x]        \
                + in22[x] + in23[x] + in24[x] + in25[x] + in26[x] + in27[x])

void
NAME (float *restrict out, IN(0), IN(1), IN(2), IN(3), IN(4), IN(5), IN(6), IN(7), IN(8),
      IN(9), IN(10), IN(11), IN(12), IN(13), IN(14), IN(15), IN(16), IN(17), IN(18), IN(19),
      IN(20), IN(21), IN(22), IN(23), IN(24), IN(25), IN(26), IN(27), float c)
{
  for (int k = 0; k < COLUMN_NK; ++k)
    for (int i = 0; i < COLUMN_NI; ++i)
      {
        int x = k * COLUMN_LD + i;
        out[x] = c * SUM (x);
      }
}
