// S5-13: unsigned indices cannot use signed dword addressing.
// S5-14 moves the former 8-lane negative cases into positive scans.
// options: -O3
// scan-asm-not: \bv(?:p?gather|p?scatter)\w*\b
float a_unsigned_f32[1024] __attribute__((aligned(64)));
int a_unsigned_i32[1024] __attribute__((aligned(64)));
unsigned uidx[1024] __attribute__((aligned(64)));

void unsigned_gather_f32 (const float *restrict b)
{
  for (int i = 0; i < 1024; ++i)
    a_unsigned_f32[i] = b[uidx[i]];
}

void unsigned_gather_i32 (const int *restrict b)
{
  for (int i = 0; i < 1024; ++i)
    a_unsigned_i32[i] = b[uidx[i]];
}
