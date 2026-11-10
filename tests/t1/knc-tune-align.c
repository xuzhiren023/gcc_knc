// S8-08 (E5-12): -mtune=knc starts functions on the 64-byte line.
// The lead's A/A pairs on the card (2026-11-09: same code, shifted half a
// line) moved m2_mat8 by 1.34 at the generic 16 and 0.76 at 32; at 64 every
// kernel stayed within 1.8%.  The code-placement swing is the reason.
// Loops keep the knc alignment (.p2align 4,,10 then 3): a 64-byte loop
// default has no max-skip, so an inner loop entered by fallthrough ran up to
// 63 bytes of nops per outer trip (lead, card 2026-11-10: mat8 1.106,
// mat16 1.173 slower than knc).
// options: -O2 -march=knc
// scan-asm: \.p2align 6\s*\n\s*\.globl\s+scale\b
// scan-asm: \.p2align 6\s*\n\s*\.globl\s+sum\b
// scan-asm-not: \.p2align [0-5]\s*\n\s*\.globl
// scan-asm: ^\s*\.p2align 4,,10\s*\n\s*\.p2align 3\s*\n\.L\d+:
// scan-asm-not: ^\s*\.p2align 6\s*\n\s*\.p2align 3\s*\n\.L\d+:

void
scale (float *restrict p, int n)
{
  for (int i = 0; i < n; i++)
    p[i] *= 3.0f;
}

int
sum (const int *p, int n)
{
  int s = 0;
  for (int i = 0; i < n; i++)
    s += p[i] * i;
  return s;
}
