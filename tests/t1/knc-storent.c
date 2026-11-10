// S8-13 / E5-08, ADR-0009 point 5 and amendment 1 point 1: a write-only
// output stream that covers whole 64-byte lines beyond L2 is stored with the
// no-read, non-globally-ordered vmovnrngoap* (knc-characterization.md C1:
// 3.1x at one thread, 2.7x on the whole card), followed by the KNC fence
// lock addl $0,(%rsp) before the loop's exit publishes the data (no sfence or
// mfence on KNC).  GCC's loop-prefetch pass marks the stores (storent optab);
// a loop whose trip count is known only at run time is versioned on the L2
// footprint: the NGO copy runs when iterations x bytes per iteration reach
// the 512 KiB L2 (two 64-byte streams: 4096 iterations, three: 2731), and
// the other copy is the S8-03 prefetched loop with normal stores.
// -fno-unroll-loops: this test pins the NGO stores and fence, not unrolling (S8-15).
// options: -O2 -ffp-contract=off -fno-unroll-loops
// Order within each NGO function: every NGO store comes before the fence,
// the fence before a ret, and no NGO store reaches a ret without a fence.
// scan-asm-func stream_f32: (?s)\A(?!.*\bvmovnrngoap[sd]\b(?:(?!\block\b).)*\n\s*ret\b)(?!.*\block[^\n]*addl[^\n]*\n.*\bvmovnrngoap)(?=.*\bvmovnrngoaps\s+%zmm\d+,\s*[^\n]*\(%r.*\block\b[ \t]*;?\s*addl[ \t]+\$0,[ \t]*\(%rsp\).*\n\s*ret\b)
// The NGO copy prefetches its input stream but never its output: no loop
// has a vprefetch whose base register is the NGO store's.
// scan-asm-loop-not stream_f32: (?s)\bvmovnrngoaps\s+%zmm\d+,\s*[^\n(]*\((%r\w+)\b.*\bvprefetch[0-2]\s+[^\n(]*\(\1\b
// scan-asm-loop-not stream_f32: (?s)\bvprefetch[0-2]\s+[^\n(]*\((%r\w+)\b.*\bvmovnrngoaps\s+%zmm\d+,\s*[^\n(]*\(\1\b
// The run-time L2-resident copy keeps the normal aligned store.
// scan-asm-func stream_f32: \bvmovaps\s+%zmm\d+,\s*[^\n]*\(%r
// scan-asm-func stream_f64: (?s)\A(?!.*\bvmovnrngoap[sd]\b(?:(?!\block\b).)*\n\s*ret\b)(?!.*\block[^\n]*addl[^\n]*\n.*\bvmovnrngoap)(?=.*\bvmovnrngoapd\s+%zmm\d+,\s*[^\n]*\(%r.*\block\b[ \t]*;?\s*addl[ \t]+\$0,[ \t]*\(%rsp\).*\n\s*ret\b)
// scan-asm-func stream_f64: \bvmovapd\s+%zmm\d+,\s*[^\n]*\(%r
// Integer lines take the same no-read store (the ISA has no vmovnrngo integer
// form; the bits are the line).
// scan-asm-func stream_i32: (?s)\A(?!.*\bvmovnrngoap[sd]\b(?:(?!\block\b).)*\n\s*ret\b)(?!.*\block[^\n]*addl[^\n]*\n.*\bvmovnrngoap)(?=.*\bvmovnrngoaps\s+%zmm\d+,\s*[^\n]*\(%r.*\block\b[ \t]*;?\s*addl[ \t]+\$0,[ \t]*\(%rsp\).*\n\s*ret\b)
// scan-asm-func stream_i64: (?s)\A(?!.*\bvmovnrngoap[sd]\b(?:(?!\block\b).)*\n\s*ret\b)(?!.*\block[^\n]*addl[^\n]*\n.*\bvmovnrngoap)(?=.*\bvmovnrngoapd\s+%zmm\d+,\s*[^\n]*\(%r.*\block\b[ \t]*;?\s*addl[ \t]+\$0,[ \t]*\(%rsp\).*\n\s*ret\b)
// A constant trip count beyond L2 (two 4 MiB static arrays) needs no guard:
// the pass judges it from the footprint alone.
// scan-asm-func big_stream_f32: (?s)\A(?![\s\S]*\bjbe\b)(?!.*\bvmovnrngoap[sd]\b(?:(?!\block\b).)*\n\s*ret\b)(?!.*\block[^\n]*addl[^\n]*\n.*\bvmovnrngoap)(?=.*\bvmovnrngoaps\s+%zmm\d+,\s*[^\n]*\(%r.*\block\b[ \t]*;?\s*addl[ \t]+\$0,[ \t]*\(%rsp\).*\n\s*ret\b)
// The inlined publish case: the NGO loop is followed in the same function
// by a flag store, and the fence sits between the last NGO store and it.
// scan-asm-func publish_f32: (?s)\A(?!.*\bvmovnrngoaps\b(?:(?!\block\b).)*\n\s*movl\s+\$1,)(?!.*\block[^\n]*addl[^\n]*\n.*\bvmovnrngoap)(?=.*\bvmovnrngoaps\s+%zmm\d+,\s*[^\n]*\(%r.*\block\b[ \t]*;?\s*addl[ \t]+\$0,[ \t]*\(%rsp\).*\n\s*movl\s+\$1,\s*\(%r)
// Normal stores, no fence: a masked (conditional) store, a converting
// half-line store, a store of unknown alignment (vpackstore pair) and a
// constant L2-resident footprint (two 128 KiB arrays).
// scan-asm-func masked_f32: \A(?![\s\S]*\bvmovnrngo)(?![\s\S]*\block\b[ \t]*;?\s*addl)(?=[\s\S]*\bvmovaps\s+%zmm\d+,\s*[^\n]*\{%k[1-7]\})
// scan-asm-func narrow_u16: \A(?![\s\S]*\bvmovnrngo)(?![\s\S]*\block\b[ \t]*;?\s*addl)(?=[\s\S]*\bvmovdqa32\s+%zmm\d+\{uint16\},)
// scan-asm-func stream_unaligned_f32: \A(?![\s\S]*\bvmovnrngo)(?![\s\S]*\block\b[ \t]*;?\s*addl)(?=[\s\S]*\bvpackstorelps\b)
// scan-asm-func l2_stream_f32: \A(?![\s\S]*\bvmovnrngo)(?![\s\S]*\block\b[ \t]*;?\s*addl)(?=[\s\S]*\bvmovaps\s+%zmm\d+,\s*[^\n]*\(%r)
// scan-asm-not: \b(?:sfence|mfence|vmovnraps|vmovnrapd)\b

void
stream_f32 (float *restrict yy, const float *restrict xx, float a,
	    unsigned long n)
{
  float *restrict y = __builtin_assume_aligned (yy, 64);
  const float *restrict x = __builtin_assume_aligned (xx, 64);
  for (unsigned long i = 0; i < n; ++i)
    y[i] = a * x[i];
}

void
stream_f64 (double *restrict yy, const double *restrict xx, double a,
	    unsigned long n)
{
  double *restrict y = __builtin_assume_aligned (yy, 64);
  const double *restrict x = __builtin_assume_aligned (xx, 64);
  for (unsigned long i = 0; i < n; ++i)
    y[i] = a * x[i];
}

void
stream_i32 (int *restrict yy, const int *restrict xx, int a, int b,
	    unsigned long n)
{
  int *restrict y = __builtin_assume_aligned (yy, 64);
  const int *restrict x = __builtin_assume_aligned (xx, 64);
  for (unsigned long i = 0; i < n; ++i)
    y[i] = x[i] * a + b;
}

void
stream_i64 (long *restrict yy, const long *restrict xx,
	    const long *restrict zz, unsigned long n)
{
  long *restrict y = __builtin_assume_aligned (yy, 64);
  const long *restrict x = __builtin_assume_aligned (xx, 64);
  const long *restrict z = __builtin_assume_aligned (zz, 64);
  for (unsigned long i = 0; i < n; ++i)
    y[i] = x[i] + z[i];
}

float big_y[1 << 20] __attribute__ ((aligned (64)));
float big_x[1 << 20] __attribute__ ((aligned (64)));

void
big_stream_f32 (float a)
{
  for (unsigned int i = 0; i < (1 << 20); ++i)
    big_y[i] = a * big_x[i];
}

void
publish_f32 (float *restrict yy, const float *restrict xx, float a,
	     unsigned long n, volatile int *flag)
{
  float *restrict y = __builtin_assume_aligned (yy, 64);
  const float *restrict x = __builtin_assume_aligned (xx, 64);
  for (unsigned long i = 0; i < n; ++i)
    y[i] = a * x[i];
  *flag = 1;
}

void
masked_f32 (float *restrict yy, const float *restrict xx,
	    const int *restrict mm, unsigned long n)
{
  float *restrict y = __builtin_assume_aligned (yy, 64);
  const float *restrict x = __builtin_assume_aligned (xx, 64);
  const int *restrict m = __builtin_assume_aligned (mm, 64);
  for (unsigned long i = 0; i < n; ++i)
    if (m[i] > 0)
      y[i] = x[i];
}

void
narrow_u16 (unsigned short *restrict yy, const int *restrict xx,
	    unsigned long n)
{
  unsigned short *restrict y = __builtin_assume_aligned (yy, 64);
  const int *restrict x = __builtin_assume_aligned (xx, 64);
  for (unsigned long i = 0; i < n; ++i)
    y[i] = x[i];
}

void
stream_unaligned_f32 (float *restrict y, const float *restrict x, float a,
		      unsigned long n)
{
  for (unsigned long i = 0; i < n; ++i)
    y[i] = a * x[i];
}

float l2_y[32768] __attribute__ ((aligned (64)));
const float l2_x[32768] __attribute__ ((aligned (64)));

void
l2_stream_f32 (float a)
{
  for (unsigned int i = 0; i < 32768; ++i)
    l2_y[i] = a * l2_x[i];
}
