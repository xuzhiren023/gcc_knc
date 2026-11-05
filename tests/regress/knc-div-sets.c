/* S5-03 section 5.2 (a)--(g).  Run on the card after the lead merges.
   Integer residuals decide rounding; no scalar FP division is a reference.
   Output is counts and flag masks only.  FZ=DAZ=0 is required. */
#include <stdint.h>
#include <stdio.h>
#include <fenv.h>
#include <string.h>

#define N 16
static float av[N] __attribute__((aligned(64)));
static float bv[N] __attribute__((aligned(64)));
static float cv[N] __attribute__((aligned(64)));
static uint32_t ax[N], bx[N];
static unsigned used;
static int mode;
static uint64_t count[7], bad[7], flagbad[7];
static unsigned flags_seen[7];
enum { RN, RD, RU, RZ };

__attribute__((noinline,noclone)) static void kernel (void)
{
  for (int i = 0; i < N; i++) cv[i] = av[i] / bv[i];
}

static uint32_t random32 (void)
{
  static uint64_t state = UINT64_C(0x4b4e434449563131);
  state ^= state >> 12; state ^= state << 25; state ^= state >> 27;
  return (uint32_t)((state * UINT64_C(2685821657736338717)) >> 32);
}

/* A normalized integer significand and its unbiased binade exponent. */
static uint32_t unpack (uint32_t x, int *e)
{
  uint32_t a = x & 0x7fffff;
  *e = (int)(x >> 23) - 127;
  if (*e != -127) return a | 0x800000;
  *e = -126;
  while (a < 0x800000) { a <<= 1; --*e; }
  return a;
}

/* Round from the exact integer residual n-q*d.  n and d need at most
   48 bits, including every subnormal midpoint. */
static uint64_t round_ratio (uint64_t n, uint64_t d, int sign, int *ix)
{
  uint64_t q = n / d, r = n - q * d;
  *ix = r != 0;
  int up = mode == RN ? (r > d-r || (r == d-r && (q & 1)))
           : mode == RU ? (!sign && r != 0)
           : mode == RD ? (sign && r != 0) : 0;
  return q + up;
}

static uint32_t overflow (uint32_t sign, int *flags)
{
  *flags |= FE_OVERFLOW | FE_INEXACT;
  int inf = mode == RN || (mode == RU && !sign) || (mode == RD && sign);
  return sign | (inf ? 0x7f800000 : 0x7f7fffff);
}

static uint32_t reference (uint32_t a, uint32_t b, int *flags)
{
  uint32_t sign = (a ^ b) & 0x80000000;
  a &= 0x7fffffff; b &= 0x7fffffff;
  *flags = 0;
  if (a > 0x7f800000 || b > 0x7f800000) {
    if ((a > 0x7f800000 && !(a & 0x400000))
        || (b > 0x7f800000 && !(b & 0x400000))) *flags = FE_INVALID;
    return 0x7fc00000;
  }
  if ((!a && !b) || (a == 0x7f800000 && b == 0x7f800000)) {
    *flags = FE_INVALID; return 0x7fc00000;
  }
  if (a == 0x7f800000) return sign | 0x7f800000;
  if (!b) { *flags = FE_DIVBYZERO; return sign | 0x7f800000; }
  if (!a || b == 0x7f800000) return sign;
  int ea, eb, ix;
  uint32_t A = unpack (a, &ea), B = unpack (b, &eb);
  int lower = A < B, e = ea - eb - lower;
  if (e > 127) return overflow (sign, flags);
  uint64_t q = round_ratio ((uint64_t) A << (23 + lower), B, sign != 0, &ix);
  int rounded_e = e + (q == 0x1000000);
  if (e >= -126) {
    if (q == 0x1000000) { q >>= 1; ++e; }
    if (e > 127) return overflow (sign, flags);
    if (ix) *flags = FE_INEXACT;
    return sign | ((uint32_t)(e + 127) << 23) | ((uint32_t)q & 0x7fffff);
  }
  int shift = ea - eb + 149;
  if (shift < -24) {
    ix = 1;
    q = (mode == RU && !sign) || (mode == RD && sign);
  } else {
    uint64_t num = A, den = B;
    if (shift >= 0) num <<= shift; else den <<= -shift;
    q = round_ratio (num, den, sign != 0, &ix);
  }
  if (ix) {
    *flags = FE_INEXACT;
    /* Intel 327364-001 p.59: tiny after rounding with unbounded exponent. */
    if (rounded_e < -126) *flags |= FE_UNDERFLOW;
  }
  return sign | (uint32_t)q;
}

static void flush (unsigned set)
{
  if (!used) return;
  for (unsigned i = used; i < N; ++i) ax[i] = bx[i] = 0x3f800000;
  memcpy (av, ax, sizeof av); memcpy (bv, bx, sizeof bv);
  feclearexcept (FE_ALL_EXCEPT);
  kernel ();
  int flags = fetestexcept (FE_ALL_EXCEPT), expected_flags = 0;
  flags_seen[set] |= flags;
  for (unsigned i = 0; i < used; ++i) {
    uint32_t got; int want_flags;
    memcpy (&got, &cv[i], sizeof got);
    uint32_t want = reference (ax[i], bx[i], &want_flags);
    expected_flags |= want_flags;
    int nan = (want & 0x7fffffff) > 0x7f800000;
    int ok = nan ? ((got & 0x7fffffff) > 0x7f800000 && (got & 0x400000))
                 : got == want;
    bad[set] += !ok; ++count[set];
  }
  flagbad[set] += flags != expected_flags;
  used = 0;
}

static void pair (unsigned set, uint32_t a, uint32_t b)
{
  ax[used] = a; bx[used++] = b;
  if (used == N) flush (set);
}

static int64_t inv_mod (int64_t a, int64_t m)
{
  int64_t g = m, x = 0, x1 = 1, a1 = a % m;
  while (a1) {
    int64_t q = g/a1, t = g-q*a1; g = a1; a1 = t;
    t = x-q*x1; x = x1; x1 = t;
  }
  return (x % m + m) % m;
}

/* (a) modular near-midpoints, (b) near-one/Markstein class; the S5-03
   E4 generator, with the two sets counted separately.  Negative signs
   exercise both directed-mode mirror images. */
static void hard (unsigned sa, unsigned sb)
{
  for (int64_t B = 0x800000; B < 0x1000000; ++B) {
    if (B & 1) for (int s = 24; s <= 25; ++s) {
      int64_t inv = inv_mod ((INT64_C(1) << s) % B, B);
      for (int n = 1; n <= 4; ++n) for (int sg = -1; sg <= 1; sg += 2) {
        int64_t a0 = inv * (sg > 0 ? n : B-n) % B;
        for (int64_t A = a0; A < 0x1000000; A += B)
          if (A >= 0x800000 && ((s == 24) == (A >= B))) {
            pair (sa, 0x3f000000 + A, 0x3f000000 + B);
            pair (sa, 0xbf000000 + A, 0x3f000000 + B);
          }
      }
    }
  }
  flush (sa);
  for (int64_t B = 0x800000; B < 0x1000000; ++B) {
    for (int64_t A = B-3; A <= B+3; ++A)
      if (A >= 0x800000 && A < 0x1000000) {
        pair (sb, 0x3f000000 + A, 0x3f000000 + B);
        pair (sb, 0xbf000000 + A, 0x3f000000 + B);
      }
    pair (sb, 0x3f800000, 0x3f000000 + B);
    pair (sb, 0xbf800000, 0x3f000000 + B);
  }
  flush (sb);
}

/* (d) q with d low bits 100..0; A is the nearest product q*B,
   and its neighbours.  Retain precisely the pairs whose RN reduced
   quotient is that midpoint.  a is in the lowest normal binade. */
static void midpoints (unsigned set)
{
  int saved = mode;
  for (int d = 1; d <= 24; ++d) for (int j = 0; j < 4096; ++j) {
    uint32_t q = ((random32 () & 0x7fffff) | 0x800000);
    q = (q >> d << d) | (1u << (d-1));
    if (q < 0x800000) continue;
    uint32_t B = (random32 () & 0x7fffff) | 0x800000;
    uint32_t center = (uint64_t)q * B >> 23;
    for (int delta = -1; delta <= 1; ++delta) {
      uint32_t A = center + delta;
      if (A < 0x800000 || A >= 0x1000000) continue;
      int unused_flags;
      mode = RN;
      uint32_t reduced = reference (0x3f000000 + A, 0x3f000000 + B, &unused_flags);
      mode = saved;
      if (reduced != 0x3f000000 + q) continue;
      pair (set, A, ((uint32_t)(d+127) << 23) | (B & 0x7fffff));
      pair (set, A | 0x80000000, ((uint32_t)(d+127) << 23) | (B & 0x7fffff));
    }
  }
  flush (set);
}

int main (void)
{
  const int modes[] = { FE_TONEAREST, FE_DOWNWARD, FE_UPWARD, FE_TOWARDZERO };
  /* All four modes for (a), (b), (d); g counts the three extra modes. */
  for (mode = RN; mode <= RZ; ++mode) {
    if (fesetround (modes[mode])) return 2;
    hard (mode == RN ? 0 : 6, mode == RN ? 1 : 6);
    midpoints (mode == RN ? 3 : 6);
  }
  mode = RN; fesetround (FE_TONEAREST);
  /* (c) all exponent pairs, 64 significand pairs each, plus subnormals. */
  for (uint32_t ea = 1; ea <= 254; ++ea)
    for (uint32_t eb = 1; eb <= 254; ++eb)
      for (int j = 0; j < 64; ++j)
        pair (2, (ea << 23) | (random32 () & 0x807fffff),
                 (eb << 23) | (random32 () & 0x807fffff));
  for (uint32_t e = 0; e <= 254; ++e) for (int j = 0; j < 64; ++j) {
    uint32_t sub = (random32 () & 0x7fffff) | 1;
    uint32_t other = (e << 23) | (random32 () & 0x807fffff);
    pair (2, sub, other); pair (2, other, sub);
  }
  flush (2);
  /* (e) one active pair per call isolates the exception flags. */
  const uint32_t values[] = {0,0x80000000,1,0x80000001,0x00800000,0x80800000,
    0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,0x7fc00001,0x7f800001,
    0x3f800000,0xbf800000};
  for (mode = RN; mode <= RZ; ++mode) {
    fesetround (modes[mode]);
    for (unsigned i = 0; i < sizeof values / sizeof *values; ++i)
      for (unsigned j = 0; j < sizeof values / sizeof *values; ++j) {
        pair (4, values[i], values[j]); flush (4);
      }
  }
  mode = RN; fesetround (FE_TONEAREST);
  for (uint64_t i = 0; i < (UINT64_C(1) << 30); ++i)
    pair (5, random32 (), random32 ());
  flush (5);
  int failed = 0;
  for (int s = 0; s < 7; ++s) {
    printf ("set=%d count=%llu bad=%llu flagbad=%llu flags=%x\n", s,
            (unsigned long long)count[s], (unsigned long long)bad[s],
            (unsigned long long)flagbad[s], flags_seen[s]);
    failed |= bad[s] != 0 || flagbad[s] != 0 || count[s] == 0;
  }
  return failed;
}
