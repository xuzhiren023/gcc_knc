// S8-15 (E5-09, ADR-0009 point 6): -O2 -march=knc unrolls a vector loop of a
// few instructions.  S8-01 C9: a dependent vector add costs about 2 ticks per
// vector op plus 2 per loop branch, so unroll 4 is best at 1 and 2 threads per
// core (25% then 17% over no unroll).  A larger loop already pays for its
// branch and keeps one copy of its body.
// S8-20: at the default 4 threads per core a stream (one vector op per vector
// store) keeps one copy: M2 affine_f64 lost 3-7% and short 2% unrolled 4
// times, while two ops per store (stencil1) and no store (mat16) still gained.
// knc-unroll-density1.c scans the same loops at one thread per core.
// options: -O2 -march=knc
// scan-asm-func two_ops: ^(\.L\d+):\n(?:(?![^\n]*\bvmulps\b)(?!\.L\d+:)[^\n]*\n)*(?:[^\n]*\bvmulps\b[^\n]*\n(?:(?![^\n]*\bvmulps\b)(?!\.L\d+:)[^\n]*\n)*){4}\s*j\w+\s+\1\s*$
// scan-asm-func stream_add: ^(\.L\d+):\n(?:(?![^\n]*\bvaddps\b)(?!\.L\d+:)[^\n]*\n)*[^\n]*\bvaddps\b[^\n]*\n(?:(?![^\n]*\bvaddps\b)(?!\.L\d+:)[^\n]*\n)*?\s*j\w+\s+\1\s*$
// scan-asm-loop-not stream_add: \bvaddps\b[\s\S]*\bvaddps\b
// scan-asm-func large_mix: ^(\.L\d+):\n(?:(?![^\n]*\bvpackstorehps\b)(?!\.L\d+:)[^\n]*\n)*[^\n]*\bvpackstorehps\b[^\n]*\n(?:(?![^\n]*\bvpackstorehps\b)(?!\.L\d+:)[^\n]*\n)*?\s*j\w+\s+\1\s*$

void
two_ops (float *restrict a, const float *restrict b, int n)
{
  for (int i = 0; i < n; i++)
    a[i] = (a[i] + b[i]) * b[i];
}

void
stream_add (float *restrict a, const float *restrict b, int n)
{
  for (int i = 0; i < n; i++)
    a[i] += b[i];
}

void
large_mix (float *restrict a, const float *restrict b, const float *restrict c,
           const float *restrict d, int n)
{
  for (int i = 0; i < n; i++)
    a[i] = (a[i] * b[i] + c[i]) * (d[i] - b[i]) + (a[i] - c[i]) * d[i]
           + b[i] * c[i] - d[i] * a[i] + c[i] * c[i];
}
