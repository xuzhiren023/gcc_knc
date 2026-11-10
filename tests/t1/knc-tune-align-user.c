// S8-08 (E5-12): a user -falign-functions or -falign-loops still wins over
// the -mtune=knc 64-byte default (knc-tune-align.c).
// options: -O2 -march=knc -falign-functions=16 -falign-loops=16
// scan-asm: \.p2align 4\s*\n\s*\.globl\s+sum\b
// scan-asm-not: \.p2align 6\s*\n\s*\.globl
// scan-asm: ^\s*\.p2align 4\s*\n\s*\.p2align 3\s*\n\.L\d+:

int
sum (const int *p, int n)
{
  int s = 0;
  for (int i = 0; i < n; i++)
    s += p[i] * i;
  return s;
}
