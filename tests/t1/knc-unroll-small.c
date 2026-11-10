// S8-15 (E5-09, ADR-0009 point 6): -O2 -march=knc unrolls a vector loop of a
// few instructions 4 times.  S8-01 C9: a dependent vector add costs about 2
// ticks per vector op plus 2 per loop branch, so unroll 4 is best at 1 and 2
// threads per core (25% then 17% over no unroll).  A larger loop already
// pays for its branch and keeps one copy of its body.
// options: -O2 -march=knc
// scan-asm-func small_add: ^(\.L\d+):\n(?:(?![^\n]*\bvaddps\b)(?!\.L\d+:)[^\n]*\n)*(?:[^\n]*\bvaddps\b[^\n]*\n(?:(?![^\n]*\bvaddps\b)(?!\.L\d+:)[^\n]*\n)*){4}\s*j\w+\s+\1\s*$
// scan-asm-func large_mix: ^(\.L\d+):\n(?:(?![^\n]*\bvpackstorehps\b)(?!\.L\d+:)[^\n]*\n)*[^\n]*\bvpackstorehps\b[^\n]*\n(?:(?![^\n]*\bvpackstorehps\b)(?!\.L\d+:)[^\n]*\n)*?\s*j\w+\s+\1\s*$

void
small_add (float *restrict a, const float *restrict b, int n)
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
