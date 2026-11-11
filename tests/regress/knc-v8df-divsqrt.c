/* S10-09: FP64 vector division and square root, docs/research/knc-div-sqrt.md
   sections 3 and 5.2.  Run on the card by the lead:
     xgcc -O2 -march=knc -fno-math-errno knc-v8df-divsqrt.c -lm
   Every expected value comes from 128-bit integer arithmetic: an exact long
   division or integer square root, rounded from the exact remainder, or
   (random sets) the residual test of tests/acceptance/s5_ops.  No scalar FP
   division or square root is a reference.  Output is counts and flag masks
   only.  FZ=DAZ=0 is required.

   tests/regress/knc-v8df-model.c includes this file with
   KNC_V8DF_HOST_MODEL defined, for the references and the set generators.  */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <fenv.h>

typedef unsigned __int128 u128;
enum { RN, RD, RU, RZ };
#define SIGN UINT64_C (0x8000000000000000)
#define INF UINT64_C (0x7ff0000000000000)
#define QBIT UINT64_C (0x0008000000000000)
#define QNAN UINT64_C (0xfff8000000000000)
#define HID UINT64_C (0x0010000000000000)
#define FRAC UINT64_C (0x000fffffffffffff)
#define ONE UINT64_C (0x3ff0000000000000)

static uint64_t state = UINT64_C (0x4b4e435638444631);
static uint64_t
rnd64 (void)
{
  state ^= state >> 12; state ^= state << 25; state ^= state >> 27;
  return state * UINT64_C (2685821657736338717);
}
/* A random 53-bit significand with its leading bit set.  */
static uint64_t rsig (void) { return (rnd64 () >> 12) | HID; }

/* |x| = M * 2^(e-52) with 2^52 <= M < 2^53, for finite nonzero x.  */
static uint64_t
unpack (uint64_t x, int *e)
{
  uint64_t m = x & FRAC;
  int be = (x >> 52) & 0x7ff;
  if (be) { *e = be - 1023; return m | HID; }
  int s = __builtin_clzll (m) - 11;
  *e = -1022 - s;
  return m << s;
}

/* (-1)^sign * M * 2^(e-52); below the normal range the low bits of M drop.  */
static uint64_t
mk (int sign, int e, uint64_t M)
{
  uint64_t s = sign ? SIGN : 0;
  if (e >= -1022) return s | ((uint64_t) (e + 1023) << 52) | (M & FRAC);
  return s | (M >> (-1022 - e));
}

/* REM: 0 exact, 1 below half, 2 half, 3 above half.  */
static int
round_up (int mode, int sign, int odd, int rem)
{
  if (!rem) return 0;
  if (mode == RN) return rem == 3 || (rem == 2 && odd);
  return mode == RU ? !sign : mode == RD ? sign : 0;
}

static int
remainder_class (u128 n, int sh, int sticky)
{
  u128 rem = n & (((u128) 1 << sh) - 1), half = (u128) 1 << (sh - 1);
  return rem > half || (rem == half && sticky) ? 3 : rem == half ? 2
	 : rem || sticky ? 1 : 0;
}

/* The IEEE double for (-1)^sign * (n + f) * 2^e, 0 <= f < 1 and f != 0 iff
   STICKY, with at least 56 bits in n, and its flags.  Tininess is detected
   after rounding (Intel 327364-001 p.59).  */
static uint64_t
pack (int mode, int sign, u128 n, int sticky, int e, int *flags)
{
  uint64_t s = sign ? SIGN : 0, hi = (uint64_t) (n >> 64);
  int nb = hi ? 128 - __builtin_clzll (hi) : 64 - __builtin_clzll ((uint64_t) n);
  int sh = nb - 53;
  int r = remainder_class (n, sh, sticky);
  u128 q = (n >> sh) + round_up (mode, sign, (n >> sh) & 1, r);
  int E = e + sh + 52;
  if (q >> 53) { q >>= 1; ++E; }
  if (E > 1023)
    {
      *flags |= FE_OVERFLOW | FE_INEXACT;
      int inf = mode == RN || (mode == RU && !sign) || (mode == RD && sign);
      return s | (inf ? INF : INF - 1);
    }
  if (E >= -1022)
    {
      if (r) *flags |= FE_INEXACT;
      return s | ((uint64_t) (E + 1023) << 52) | ((uint64_t) q & FRAC);
    }
  sh = -1074 - e;
  if (sh > nb) { q = 0; r = 1; }
  else { q = n >> sh; r = remainder_class (n, sh, sticky); }
  q += round_up (mode, sign, q & 1, r);
  if (r) *flags |= FE_UNDERFLOW | FE_INEXACT;
  return s | (uint64_t) q;
}

static uint64_t
ref_div (uint64_t a, uint64_t b, int mode, int *flags)
{
  uint64_t aa = a & ~SIGN, bb = b & ~SIGN, s = (a ^ b) & SIGN;
  *flags = 0;
  if (aa > INF || bb > INF)
    {
      if ((aa > INF && !(a & QBIT)) || (bb > INF && !(b & QBIT)))
	*flags = FE_INVALID;
      return (aa > INF ? a : b) | QBIT;
    }
  if ((!aa && !bb) || (aa == INF && bb == INF))
    { *flags = FE_INVALID; return QNAN; }
  if (aa == INF) return s | INF;
  if (!bb) { *flags = FE_DIVBYZERO; return s | INF; }
  if (!aa || bb == INF) return s;
  int ea, eb;
  uint64_t A = unpack (aa, &ea), B = unpack (bb, &eb);
  u128 num = (u128) A << 70, n = num / B;
  return pack (mode, s != 0, n, n * B != num, ea - eb - 70, flags);
}

static uint64_t
ref_sqrt (uint64_t x, int mode, int *flags)
{
  *flags = 0;
  if ((x & ~SIGN) > INF)
    { if (!(x & QBIT)) *flags = FE_INVALID; return x | QBIT; }
  if (!(x & ~SIGN) || x == INF) return x;
  if (x & SIGN) { *flags = FE_INVALID; return QNAN; }
  int e;
  uint64_t M = unpack (x, &e);
  e -= 52;
  if (e & 1) { M <<= 1; --e; }
  u128 v = (u128) M << 60, r = 0;
  for (u128 bit = (u128) 1 << 56; bit; bit >>= 1)
    if ((r | bit) * (r | bit) <= v) r |= bit;
  return pack (mode, 0, r, r * r != v, e / 2 - 30, flags);
}

/* The s5_ops residual tests, for a normal RN result of finite nonzero
   operands.  A quotient of doubles is never a midpoint: q = RN(a/b) iff
   |a - q b| < |b| g / 2, g the gap from q towards a/b.  *EXACT says whether
   the residual is zero.  */
static int
div_ok (uint64_t a, uint64_t b, uint64_t q, int *exact)
{
  int ea, eb, eq;
  uint64_t A = unpack (a & ~SIGN, &ea), B = unpack (b & ~SIGN, &eb);
  uint64_t Q = unpack (q & ~SIGN, &eq);
  int d = ea - eq - eb + 52;
  *exact = 0;
  if (((a ^ b ^ q) & SIGN) || (q & ~SIGN) >= INF || (q & ~SIGN) < HID
      || d < 51 || d > 53)
    return 0;
  u128 x = (u128) A << d, y = (u128) Q * B;
  u128 r = x > y ? x - y : y - x;
  *exact = r == 0;
  return (r << (x < y && Q == HID ? 2 : 1)) < B;
}
/* q = RN(sqrt x) iff (2Q - 1)^2 < 4X < (2Q + 1)^2 in units of q's last
   place, or Q^2 = X.  A root just below a power of two never rounds up to
   it, so the narrower gap below a power of two only admits the exact case.  */
static int
sqrt_ok (uint64_t x, uint64_t q, int *exact)
{
  int e, eq;
  uint64_t M = unpack (x, &e), Q = unpack (q, &eq);
  e -= 52;
  if (e & 1) { M <<= 1; --e; }
  int s = e - 2 * eq + 106;
  *exact = 0;
  if ((q & SIGN) || q >= INF || q < HID || s < 50 || s > 56) return 0;
  u128 X = (u128) M << s, c = 2 * (u128) Q;
  *exact = X == c * c;
  if (Q == HID && X < c * c) return 0;
  return (c - 1) * (c - 1) < X && X < (c + 1) * (c + 1);
}

typedef void pair_fn (unsigned set, uint64_t a, uint64_t b);
typedef void one_fn (unsigned set, uint64_t x);

static int64_t
inv_mod (int64_t a, int64_t m)
{
  int64_t g = m, x = 0, x1 = 1, a1 = a % m;
  while (a1)
    {
      int64_t q = g / a1, t = g - q * a1; g = a1; a1 = t;
      t = x - q * x1; x = x1; x1 = t;
    }
  return (x % m + m) % m;
}

/* Section 5.2 (a) and (b).  For NB random odd divisor significands B and
   64 at the ends of the range: every A with A 2^s = Q B +- n, n = 1..4,
   Q a 54-bit integer, so that a/b is within n u/(2B) of a midpoint (Q odd)
   or of a double (Q even), in both quotient binades; then A = B-3..B+3 and
   a = 1 (the Markstein class, which holds the all-ones divisor).  Both
   quotient signs, as RD on a negative quotient mirrors RU.  */
static void
div_hard (pair_fn *pair, unsigned sa, unsigned sb, long nb)
{
  for (long i = -64; i < nb; ++i)
    {
      uint64_t B = i < -32 ? HID + (i + 64) : i < 0 ? 2 * HID + i : rsig () | 1;
      if (B & 1)
	for (int s = 53; s <= 54; ++s)
	  {
	    uint64_t inv = inv_mod ((int64_t) (((u128) 1 << s) % B), B);
	    for (int n = 1; n <= 4; ++n)
	      for (int sg = 0; sg < 2; ++sg)
		{
		  uint64_t A0 = (uint64_t) ((u128) inv * (sg ? n : B - n) % B);
		  for (uint64_t A = A0; A < 2 * HID; A += B)
		    if (A >= HID && ((s == 53) == (A >= B)))
		      {
			pair (sa, mk (0, 0, A), mk (0, 0, B));
			pair (sa, mk (1, 0, A), mk (0, 0, B));
		      }
		}
	  }
      for (uint64_t A = B - 3; A <= B + 3; ++A)
	if (A >= HID && A < 2 * HID)
	  {
	    pair (sb, mk (0, 0, A), mk (0, 0, B));
	    pair (sb, mk (1, 0, A), mk (0, 0, B));
	  }
      pair (sb, ONE, mk (0, 0, B));
      pair (sb, ONE | SIGN, mk (0, 0, B));
    }
}

/* (c) Exponent pairs over the whole range, subnormal operands included:
   every numerator exponent against every STEP-th divisor exponent.  Then
   the exponent differences at the overflow threshold and through the
   subnormal results, CNT random significand pairs each.  */
static void
div_sweep (pair_fn *pair, unsigned set, int step, int cnt)
{
  for (int ea = -1074; ea <= 1023; ++ea)
    for (int eb = -1074 + (int) (rnd64 () % step); eb <= 1023; eb += step)
      pair (set, mk (rnd64 () & 1, ea, rsig ()), mk (rnd64 () & 1, eb, rsig ()));
  for (int k = -1080; k <= 1026; k = k == -1018 ? 1021 : k + 1)
    for (int i = 0; i < cnt; ++i)
      {
	int span = 2046 - (k < 0 ? -k : k);
	int lo = -1022 + (int) (rnd64 () % span);
	int ea = k < 0 ? lo : lo + k, eb = ea - k;
	pair (set, mk (rnd64 () & 1, ea, rsig ()), mk (rnd64 () & 1, eb, rsig ()));
      }
}

/* (d) Quotients whose 53-bit RN significand ends in a one and d-1 zeros,
   scaled so that exactly d bits drop on the subnormal grid: the scaled
   significand is a subnormal midpoint, which a second rounding gets wrong
   half the time.  A is the product Q B and its neighbours; a pair is kept
   when its RN significand quotient is Q.  */
static void
div_midpoints (pair_fn *pair, unsigned set, int cnt)
{
  for (int d = 1; d <= 53; ++d)
    for (int j = 0; j < cnt; ++j)
      {
	uint64_t Q = (d == 53 ? 0 : rsig () >> d << d) | (UINT64_C (1) << (d - 1)) | HID;
	uint64_t B = rsig (), center = (uint64_t) ((u128) Q * B >> 52);
	for (int delta = -1; delta <= 1; ++delta)
	  {
	    uint64_t A = center + delta;
	    int flags;
	    if (A < HID || A >= 2 * HID
		|| ref_div (mk (0, 0, A), mk (0, 0, B), RN, &flags) != mk (0, 0, Q))
	      continue;
	    pair (set, mk (0, -1022, A), mk (0, d, B));
	    pair (set, mk (1, -1022, A), mk (0, d, B));
	  }
      }
}

static const uint64_t special[] =
  { 0, SIGN, 1, SIGN | 1, HID, SIGN | HID, INF - 1, SIGN | (INF - 1), INF,
    SIGN | INF, INF | QBIT | 1, INF | 1, SIGN | INF | QBIT | 5, ONE,
    SIGN | ONE, UINT64_C (0x4004000000000000), UINT64_C (0xc004000000000000) };
#define NSPECIAL (sizeof special / sizeof *special)

/* Square-root hard cases by Hensel lifting.  The roots G with BITS bits of
   G^2 = -n (mod 2^BITS), n = 7 (mod 8), give M = (G^2 + n) / 2^BITS with
   sqrt(M 2^BITS) within |n| / (2G) of the integer G.  With G a 54-bit odd
   integer the root is that close to a midpoint; with G a 53-bit integer,
   to a double.  LO <= G < HI selects the binade.  */
static void
sqrt_lift (one_fn *one, unsigned set, int bits, uint64_t lo, uint64_t hi,
	   int e, long n)
{
  uint64_t mask = (UINT64_C (1) << bits) - 1, c = (uint64_t) -n & mask, r = 1;
  for (int i = 3; i < bits; ++i)
    if ((r * r - c) >> i & 1) r += UINT64_C (1) << (i - 1);
  for (int v = 0; v < 4; ++v)
    {
      uint64_t G = ((v & 1 ? -r : r) + ((uint64_t) (v >> 1) << (bits - 1))) & mask;
      for (; G < hi; G += mask + 1)
	if (G >= lo)
	  {
	    uint64_t M = (uint64_t) (((u128) G * G + (__int128) n) >> bits);
	    if (M >= HID && M < 2 * HID) one (set, mk (0, e, M));
	  }
    }
}

/* (a) every reduced argument whose root is within NMAX units of a midpoint
   (unit: 2^-107 / sqrt m in [1,2), 2^-109 / sqrt m in [1/2,1)), and (b) of a
   double, in units four times as large.  0x16a09e667f3bcd is 2^52.5.  */
static void
sqrt_hard (one_fn *one, unsigned sa, unsigned sb, long nmax)
{
  const uint64_t r2 = UINT64_C (0x16a09e667f3bcd);
  for (long n = 7; n <= nmax; n += 8)
    for (int sg = 0; sg < 2; ++sg)
      {
	long v = sg ? 6 - n : n;
	sqrt_lift (one, sa, 54, 2 * HID, 2 * r2 + 1, 0, v);
	sqrt_lift (one, sa, 55, 2 * r2 + 1, 4 * HID, -1, v);
	sqrt_lift (one, sb, 52, HID, r2 + 1, 0, v);
	sqrt_lift (one, sb, 53, r2 + 1, 2 * HID, -1, v);
      }
}

/* Exact squares and their neighbours, CNT random ones; the binade ends;
   then (c) every exponent, subnormals included, with a random, an
   all-ones and a one-ulp significand.  */
static void
sqrt_sweep (one_fn *one, unsigned set, int cnt)
{
  for (int i = 0; i < cnt; ++i)
    {
      uint64_t j = (UINT64_C (1) << 26) + rnd64 () % UINT64_C (27797000);
      for (int d = -1; d <= 1; ++d) one (set, mk (0, 0, j * j + d));
      j = (j >> 13) << 13;
      one (set, mk (0, 2 * (int) (rnd64 () % 1000) - 1000, j * j));
    }
  for (int e = -1; e <= 0; ++e)
    for (uint64_t d = 0; d < 512; ++d)
      { one (set, mk (0, e, HID + d)); one (set, mk (0, e, 2 * HID - 1 - d)); }
  for (int e = -1074; e <= 1023; ++e)
    {
      one (set, mk (0, e, rsig ()));
      one (set, mk (0, e, 2 * HID - 1));
      one (set, mk (0, e, HID + 1));
      one (set, mk (0, e, HID));
    }
}

#ifndef KNC_V8DF_HOST_MODEL
#define N 8
static double av[N] __attribute__ ((aligned (64)));
static double bv[N] __attribute__ ((aligned (64)));
static double cv[N] __attribute__ ((aligned (64)));
static uint64_t ax[N], bx[N];
static unsigned used;
static int mode;
enum { NSET = 15 };
static const char *const name[NSET] =
  { "div-midpoint", "div-markstein", "div-exponent", "div-tiny-midpoint",
    "div-special", "div-random", "div-modes", "div-masked", "sqrt-midpoint",
    "sqrt-double", "sqrt-exponent", "sqrt-special", "sqrt-random",
    "sqrt-modes", "sqrt-masked" };
static uint64_t count[NSET], bad[NSET], flagbad[NSET];
static unsigned flags_seen[NSET];

__attribute__ ((noinline, noclone)) static void
div_kernel (void)
{
  for (int i = 0; i < N; i++) cv[i] = av[i] / bv[i];
}
/* The masked form: lanes from n on are not computed and raise nothing.  */
__attribute__ ((noinline, noclone)) static void
div_kernel_n (double *restrict c, const double *restrict a,
	      const double *restrict b, int n)
{
  c = __builtin_assume_aligned (c, 64);
  a = __builtin_assume_aligned (a, 64);
  b = __builtin_assume_aligned (b, 64);
  for (int i = 0; i < n; i++) c[i] = a[i] / b[i];
}
__attribute__ ((noinline, noclone)) static void
sqrt_kernel (void)
{
  for (int i = 0; i < N; i++) cv[i] = __builtin_sqrt (av[i]);
}

__attribute__ ((noinline, noclone)) static void
sqrt_kernel_n (double *restrict c, const double *restrict a, int n)
{
  c = __builtin_assume_aligned (c, 64);
  a = __builtin_assume_aligned (a, 64);
  for (int i = 0; i < n; i++) c[i] = __builtin_sqrt (a[i]);
}

static void
check (unsigned set, int sqrt_p, int residual)
{
  int flags = fetestexcept (FE_ALL_EXCEPT), expected = 0;
  flags_seen[set] |= flags;
  for (unsigned i = 0; i < used; ++i)
    {
      uint64_t got;
      int f = 0, ok, exact;
      memcpy (&got, &cv[i], sizeof got);
      if (residual)
	{
	  ok = sqrt_p ? sqrt_ok (ax[i], got, &exact)
		      : div_ok (ax[i], bx[i], got, &exact);
	  if (!exact) f = FE_INEXACT;
	}
      else
	{
	  uint64_t want = sqrt_p ? ref_sqrt (ax[i], mode, &f)
				 : ref_div (ax[i], bx[i], mode, &f);
	  ok = (want & ~SIGN) > INF ? (got & ~SIGN) > INF && (got & QBIT)
				    : got == want;
	}
      expected |= f;
      bad[set] += !ok;
      ++count[set];
    }
  flagbad[set] += flags != expected;
  used = 0;
}

static void
flush_div (unsigned set, int residual, int masked)
{
  if (!used) return;
  /* An unmasked lane of 0/0 would raise invalid.  */
  for (unsigned i = used; i < N; ++i) { ax[i] = masked ? 0 : ONE; bx[i] = ax[i]; }
  memcpy (av, ax, sizeof av); memcpy (bv, bx, sizeof bv);
  feclearexcept (FE_ALL_EXCEPT);
  if (masked) div_kernel_n (cv, av, bv, used); else div_kernel ();
  check (set, 0, residual);
}
static void
flush_sqrt (unsigned set, int residual, int masked)
{
  if (!used) return;
  /* An unmasked lane of sqrt (-1) would raise invalid.  */
  for (unsigned i = used; i < N; ++i) ax[i] = masked ? SIGN | ONE : ONE;
  memcpy (av, ax, sizeof av);
  feclearexcept (FE_ALL_EXCEPT);
  if (masked) sqrt_kernel_n (cv, av, used); else sqrt_kernel ();
  check (set, 1, residual);
}
static void
pair (unsigned set, uint64_t a, uint64_t b)
{
  ax[used] = a; bx[used++] = b;
  if (used == N) flush_div (set, 0, 0);
}
static void
one (unsigned set, uint64_t x)
{
  ax[used++] = x;
  if (used == N) flush_sqrt (set, 0, 0);
}

int
main (void)
{
  const int modes[] = { FE_TONEAREST, FE_DOWNWARD, FE_UPWARD, FE_TOWARDZERO };
  for (mode = RN; mode <= RZ; ++mode)
    {
      if (fesetround (modes[mode])) return 2;
      state = UINT64_C (0x4b4e435638444631);
      div_hard (pair, mode == RN ? 0 : 6, mode == RN ? 1 : 6, 1L << 17);
      flush_div (mode == RN ? 1 : 6, 0, 0);
      div_midpoints (pair, mode == RN ? 3 : 6, 2048);
      flush_div (mode == RN ? 3 : 6, 0, 0);
      div_sweep (pair, mode == RN ? 2 : 6, mode == RN ? 3 : 61, 1024);
      flush_div (mode == RN ? 2 : 6, 0, 0);
      sqrt_hard (one, mode == RN ? 8 : 13, mode == RN ? 9 : 13, 1L << 20);
      flush_sqrt (mode == RN ? 9 : 13, 0, 0);
      sqrt_sweep (one, mode == RN ? 10 : 13, 1 << 16);
      flush_sqrt (mode == RN ? 10 : 13, 0, 0);
      /* One active element per call isolates the exception flags.  */
      for (unsigned i = 0; i < NSPECIAL; ++i)
	{
	  for (unsigned j = 0; j < NSPECIAL; ++j)
	    {
	      pair (4, special[i], special[j]); flush_div (4, 0, 0);
	      /* The same pair in the last active lane of the masked loop.  */
	      for (used = 0; used < 1 + (i + j) % 6; ++used)
		{ ax[used] = ONE; bx[used] = ONE; }
	      pair (7, special[i], special[j]); flush_div (7, 0, 1);
	    }
	  one (11, special[i]); flush_sqrt (11, 0, 0);
	  /* The same argument in the last active lane of the masked loop.  */
	  for (used = 0; used < 1 + i % 6; ++used) ax[used] = ONE;
	  one (14, special[i]); flush_sqrt (14, 0, 1);
	}
    }
  mode = RN; fesetround (FE_TONEAREST);
  /* 2^28 random operands each: quotients and roots are normal, so the
     residual decides each lane and the batch's inexact flag.  */
  for (uint64_t i = 0; i < (UINT64_C (1) << 28); ++i)
    {
      ax[used] = mk (rnd64 () & 1, (int) (rnd64 () % 1001) - 500, rsig ());
      bx[used++] = mk (rnd64 () & 1, (int) (rnd64 () % 1001) - 500, rsig ());
      if (used == N) flush_div (5, 1, 0);
    }
  for (uint64_t i = 0; i < (UINT64_C (1) << 28); ++i)
    {
      ax[used++] = mk (0, (int) (rnd64 () % 2098) - 1074, rsig ());
      if (used == N) flush_sqrt (12, 1, 0);
    }
  int failed = 0;
  for (int s = 0; s < NSET; ++s)
    {
      printf ("set=%s count=%llu bad=%llu flagbad=%llu flags=%x\n", name[s],
	      (unsigned long long) count[s], (unsigned long long) bad[s],
	      (unsigned long long) flagbad[s], flags_seen[s]);
      failed |= bad[s] != 0 || flagbad[s] != 0 || count[s] == 0;
    }
  return failed;
}
#endif
