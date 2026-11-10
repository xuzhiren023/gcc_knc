// S8-21: a row shorter than one vector is vectorized as a masked load and a
// masked store (.MASK_LOAD/.MASK_STORE of 16 lanes, 8 active), and the loop
// prefetch pass prefetches those rows like plain vector accesses (S8-11 batch
// check: before S8-21 such loops got no prefetch at all).  WRF-shaped column:
// 51 k levels at a 273-float (1092-byte) step, 8-float rows; S8-03's byte
// distances for a step beyond a line, the L1 distance capped for the stream
// count (knc-prefetch-O2.c).
// options: -O2 -ffp-contract=off
// scan-asm-func column_rows8: \bvprefetch1\s+\d+\(
// scan-asm-func column_rows8: \bvprefetch0\s+\d+\(
// The written rows are prefetched too: one prefetch per stream and level.
// scan-asm-func column_rows8: (?:\bvprefetch1\s[^\n]*\n[\s\S]*?){4}
// scan-asm-func column_rows8: (?:\bvprefetch0\s[^\n]*\n[\s\S]*?){4}
#define LD 273

void
column_rows8 (float *restrict out, const float *restrict a,
	      const float *restrict b, const float *restrict c, float s)
{
  for (int k = 0; k < 51; ++k)
    for (int i = 0; i < 8; ++i)
      out[k * LD + i] = s * (a[k * LD + i] + b[k * LD + i] + c[k * LD + i]);
}
