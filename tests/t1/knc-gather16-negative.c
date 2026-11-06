// S5-13: unsigned indices cannot use signed dword addressing; 8-lane data
// is deferred to S5-14. These scans must keep passing when S5-13 is implemented.
// options: -O3
// scan-asm-not: \bv(?:p?gather|p?scatter)\w*\b
float a_unsigned_f32[1024] __attribute__((aligned(64)));
int a_unsigned_i32[1024] __attribute__((aligned(64)));
double a_f64[1024] __attribute__((aligned(64)));
long a_i64[1024] __attribute__((aligned(64)));
unsigned uidx[1024] __attribute__((aligned(64)));
int idx[1024] __attribute__((aligned(64)));

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

void gather_f64 (const double *restrict b)
{
  for (int i = 0; i < 1024; ++i)
    a_f64[i] = b[idx[i]];
}

void scatter_f64 (double *restrict b)
{
  for (int i = 0; i < 1024; ++i)
    b[idx[i]] = a_f64[i];
}

void gather_i64 (const long *restrict b)
{
  for (int i = 0; i < 1024; ++i)
    a_i64[i] = b[idx[i]];
}

void scatter_i64 (long *restrict b)
{
  for (int i = 0; i < 1024; ++i)
    b[idx[i]] = a_i64[i];
}
