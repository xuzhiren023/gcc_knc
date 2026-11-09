/* S8-03 / E5-07: loops that GCC's loop prefetching must carry on KNC.
   Each vector iteration moves one 64-byte line per stream, so a distance of
   N lines appears as a displacement of 64*N bytes on the prefetch address
   (knc-characterization.md C5 counts the same unit: one row per iteration).
   The scans live in the including .c file, one per option set.  */

/* Two streams: C5 best L1 16 / L2 32 lines.  */
void
stream_f32 (float *restrict y, const float *restrict x, float a, unsigned long n)
{
  for (unsigned long i = 0; i < n; ++i)
    y[i] = a * x[i];
}

/* Forward 3-point stencil: three reads of x share one prefetched stream,
   so this is two streams like stream_f32.  */
void
stencil_f32 (float *restrict y, const float *restrict x, unsigned long n)
{
  for (unsigned long i = 1; i + 1 < n; ++i)
    y[i] = x[i - 1] + x[i] + x[i + 1];
}

/* C5's eight-stream short row: seven inputs and one output.  S8-12 rerun:
   best L1 8 / L2 32 at 2 and 4 threads per core.  */
void
row8_f32 (float *restrict y, const float *restrict a0, const float *restrict a1,
	  const float *restrict a2, const float *restrict a3,
	  const float *restrict a4, const float *restrict a5,
	  const float *restrict a6, unsigned long n)
{
  for (unsigned long i = 0; i < n; ++i)
    y[i] = a0[i] + a1[i] + a2[i] + a3[i] + a4[i] + a5[i] + a6[i];
}

/* 2 KiB per stream, 32 vector iterations: fits L1 and runs fewer than four
   L2 distances, so no prefetch at all.  */
void
l1_resident_f32 (float *restrict y, const float *restrict x, float a)
{
  for (unsigned int i = 0; i < 512; ++i)
    y[i] = a * x[i];
}
