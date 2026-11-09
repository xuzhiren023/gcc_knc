// S8-08 (E5-12): -mtune=knc turns X86_TUNE_FAST_PREFIX off.  The 0x66
// operand-size prefix costs 2 decode cycles on KNC (SSDG p.16, section
// 2.1.1), so a 16-bit register operation whose 32-bit form gives the same
// low 16 bits uses the unprefixed 32-bit form.  The 16-bit memory add and
// store in sum16 and the 16-bit compare in sel16 have no such form.
// options: -O2 -march=knc
// scan-asm-func mask16: \b(?:and|test)l\s+\$4660,
// scan-asm-func clear_low: \bandl\s+\$-65536,
// scan-asm-not: \b(?:and|or|xor|test|add|sub|neg|not|sal)w\s+(?:\$-?\d+,\s*)?%\w+(?:,\s*%\w+)?\s*$

int
mask16 (unsigned short a)
{
  return (a & 0x1234) ? 7 : 3;
}

unsigned
clear_low (unsigned x)
{
  return x & 0xffff0000u;
}

short
sel16 (short a, short b)
{
  return a < b ? 10 : 20;
}

void
sum16 (short *restrict p, int n)
{
  short s = 0;
  for (int i = 0; i < n; i++)
    {
      s += p[i];
      s ^= i;
      p[i] = s;
    }
}
