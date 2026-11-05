/* S5-10: lead-only native exhaustive check, 2^32 FP32 bit patterns.
   Build: xgcc -march=knc -O2 -ftree-vectorize -fno-math-errno FILE -lm.
   Exact midpoint test scaled from tests/acceptance/s5_ops/driver.c sqrt_ok.
   No floating-point reference, no per-input output.  RN, DAZ=FTZ=0.  */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <fenv.h>

typedef unsigned __int128 u128;
enum { N = 4096 };
static float a[N] __attribute__((aligned(64)));
static float c[N] __attribute__((aligned(64)));
__attribute__((noinline, noclone))
static void sqrt_vector (void)
{
  for (int i = 0; i < N; ++i)
    c[i] = __builtin_sqrtf (a[i]);
}
static void split (uint32_t x, uint64_t *m, int *e)
{
  unsigned exp = x >> 23;
  *m = x & 0x7fffff;
  *e = exp ? (int) exp - 150 : -149;
  if (exp) *m |= 1u << 23;
  else while (*m < (1u << 23)) { *m <<= 1; --*e; }
}
static int sqrt_ok (uint32_t x, uint32_t q)
{
  if (q < 0x00800000 || q >= 0x7f800000) return 0;
  uint64_t ma, mq;
  int ea, eq;
  split (x, &ma, &ea); split (q, &mq, &eq);
  int pow2 = mq == (1u << 23);
  u128 hi = (u128) (2 * mq + 1) * (2 * mq + 1);
  u128 lo = pow2 ? (u128) (4 * mq - 1) * (4 * mq - 1)
                 : (u128) (2 * mq - 1) * (2 * mq - 1);
  int elo = pow2 ? 2 * eq - 2 : 2 * eq;
  int E = elo < ea + 2 ? elo : ea + 2;
  if (ea + 2 - E > 70 || 2 * eq - E > 2) return 0;
  u128 four_a = (u128) ma << (ea + 2 - E);
  if (((u128) mq * mq << (2 * eq - E + 2)) == four_a) return 1;
  return (lo << (elo - E)) < four_a && four_a < (hi << (2 * eq - E));
}
int main (void)
{
  uint64_t regular = 0, special = 0, bad_regular = 0, bad_special = 0;
  if (fesetenv (FE_DFL_ENV) || fesetround (FE_TONEAREST)) return 2;
  unsigned csr;
  __asm__ volatile ("stmxcsr %0" : "=m" (csr));
  csr &= ~0x8040u;
  __asm__ volatile ("ldmxcsr %0" : : "m" (csr));
  for (uint64_t base = 0; base < (1ull << 32); base += N)
    {
      for (unsigned i = 0; i < N; ++i)
        { uint32_t x = base + i; memcpy (&a[i], &x, 4); }
      sqrt_vector ();
      for (unsigned i = 0; i < N; ++i)
        {
          uint32_t x = base + i, q, want;
          memcpy (&q, &c[i], 4);
          uint32_t ax = x & 0x7fffffff;
          if (x && x < 0x7f800000)
            { ++regular; bad_regular += !sqrt_ok (x, q); continue; }
          if (ax > 0x7f800000) want = x | 0x00400000; /* quiet payload */
          else if (!ax || x == 0x7f800000) want = x;
          else want = 0xffc00000; /* IEEE indefinite for negatives */
          ++special; bad_special += q != want;
        }
    }
  printf ("inputs=%llu regular=%llu special=%llu bad_regular=%llu bad_special=%llu\n",
          (unsigned long long) (regular + special),
          (unsigned long long) regular, (unsigned long long) special,
          (unsigned long long) bad_regular, (unsigned long long) bad_special);
  return bad_regular || bad_special;
}
