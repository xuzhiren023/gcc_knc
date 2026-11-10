// S8-20: at one thread per core no other thread hides the loop branch, so a
// small vector loop still unrolls (S8-01 C9).  Two ops per store unroll 4
// times; a stream (one vector op per vector store) unrolls 2 times, whose
// one-test remainder costs a call of one iteration nothing, where unroll 4's
// remainder dispatch cost M2 short 2% (S8-15 card run 2026-11-10).
// options: -O2 -march=knc --param knc-threads-per-core=1
// scan-asm-func two_ops: ^(\.L\d+):\n(?:(?![^\n]*\bvmulps\b)(?!\.L\d+:)[^\n]*\n)*(?:[^\n]*\bvmulps\b[^\n]*\n(?:(?![^\n]*\bvmulps\b)(?!\.L\d+:)[^\n]*\n)*){4}\s*j\w+\s+\1\s*$
// scan-asm-func stream_add: ^(\.L\d+):\n(?:(?![^\n]*\bvaddps\b)(?!\.L\d+:)[^\n]*\n)*(?:[^\n]*\bvaddps\b[^\n]*\n(?:(?![^\n]*\bvaddps\b)(?!\.L\d+:)[^\n]*\n)*){2}\s*j\w+\s+\1\s*$
// scan-asm-loop-not stream_add: (?:\bvaddps\b[\s\S]*){3}

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
