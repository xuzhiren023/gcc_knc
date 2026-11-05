/* S5-09: native probe of the IMCI estimate and normalize instructions that
   the FP32 division and square-root sequences rely on
   (docs/research/knc-div-sqrt.md sections 1 and 5.1; Intel 327364-001:
   VRCP23PS pp.577-579, VRSQRT23PS pp.588-590, VGETMANTPS p.324,
   VGETMANTPD p.319, MXCSR/exception flags sections 4.1.3, 4.6.1).
   The proofs then rest on measured error bounds, not on the manual's wording.

   Items (one summary line each, no per-input output; every line starts "S5-09"):
     P1a  vrcp23ps over all 2^23 significands in [1,2): maximum error in ulps
          of the result against the exact 1/x, checked against 0.912.
     P1b  vrsqrt23ps over all 2^24 values in [1/2,2): the same, against 0.775.
     P1c  vgetmantps and vgetmantpd on subnormal inputs with MXCSR.DAZ=0, for
          every interval and sign control.  The manual's prose says denormals
          are "explicitly normalized"; its pseudo-code (p.325) does not show
          that step.  The line says which of the two the hardware follows
          (prose= normalized, literal= pseudo-code taken as written, neither=).
          A few normal inputs are controls for the immediate.
     P1d  a masked-off lane raises no flag: vrcp23ps of 0 (#Z), vrsqrt23ps of -1
          (#I) and vrcp23ps of a signalling NaN (#I) in a lane whose mask bit is
          clear.  Each has an unmasked control that must raise the flag.
     P1e  vrcp23ps of 0x3FFFFFFF (2 - 2^-23).  Result 0x3F000000 (1/2) means
          S5-03 step 15 is needed on this part; 0x3F000001 means it is not (the
          proof keeps step 15 anyway).

   Reference arithmetic is exact integer arithmetic, never x87 or double
   division.  With x = S*2^ex and a result y = Y*2^ey (24-bit integers S, Y):
     rcp:    error in ulps of y = |Y*S - 2^q| / S, q = -(ex+ey): an exact
             fraction, compared with a bound by cross-multiplication in 128 bits.
     rsqrt:  1/sqrt(x) is irrational.  "error > t micro-ulps" is decided exactly
             from the squares (S*(1e6*Y+t)^2 < 1e12*2^p, p = -(ex+2*ey), and the
             matching test from below); the printed maximum is
             floor(sqrt(1e12*2^p/S)) minus 1e6*Y, correct to 1e-6 ulp.
   ulps are measured in the binade of the returned value y.
   Every input is checked in a register of 16 consecutive values; every result
   must be a positive normal float32, else it counts as bad_results.

   Build on the host (Git Bash, from the repository root; -O0, inline asm):
     T=$PWD/.work/_shared/toolchain; B=$PWD/.work/_shared/gcc-build/gcc
     PATH=$T/cygwin/bin:$T/cross/bin:$PATH $B/xgcc -B$B/ -march=knc -O0 \
       -Wall -Wextra -Wa,--march=k1om tests/regress/knc-estimate-probe.c \
       -o knc-estimate-probe.mic
   Run on the card only:  ./knc-estimate-probe.mic --native
   Memory: a few KiB (static buffers, nothing is accessed outside them, so there
   is no guard-page case to probe).  Time: seconds.  tools/knc_lint passes on
   the binary and the .s.

   Host self-check of the reference arithmetic (no KNC code is built or run;
   asm and the card paths are removed by -DHOST_LOGIC):
     PATH=$T/cygwin/bin:$PATH gcc -O1 -Wall -Wextra -DHOST_LOGIC \
       tests/regress/knc-estimate-probe.c -o estimate-selftest.exe
     ./estimate-selftest.exe --selftest
   It checks the error fractions and micro-ulp values against values computed
   independently in Python (rational and integer-sqrt arithmetic), the exact
   threshold tests at their boundaries, and the vgetmant models (prose and
   literal) on hand-derived subnormal cases.  It prints "S5-09 selftest ok".  */
#define _GNU_SOURCE 1
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef unsigned __int128 u128;
#define MICRO 1000000u

/* ---- Reference arithmetic (host and card) -------------------------------- */

/* Positive normal float32 as m*2^e with a 24-bit integer m. */
static int decode32(uint32_t bits, uint64_t *m, int *e)
{
  unsigned ef = (bits >> 23) & 0xffu;
  if ((bits >> 31) || ef == 0 || ef == 255) return 0;
  *m = (bits & 0x7fffffu) | 0x800000u;
  *e = (int)ef - 150;
  return 1;
}

/* Error of reciprocal result y for input x, in ulps of y, as num/den.
   Returns 0 when x or y is not a positive normal float32 or the scale is out
   of the range this arithmetic covers. */
static int rcp_err(uint32_t x, uint32_t y, uint64_t *num, uint64_t *den)
{
  uint64_t s, ym, t, d;
  int ex, ey, q;
  if (!decode32(x, &s, &ex) || !decode32(y, &ym, &ey)) return 0;
  q = -(ex + ey);
  if (q < 0 || q > 62) return 0;
  t = ym * s;
  d = (uint64_t)1 << q;
  *num = t > d ? t - d : d - t;
  *den = s;
  return 1;
}

static uint64_t micro_of(uint64_t num, uint64_t den)
{
  return (uint64_t)((u128)num * MICRO / den);
}

/* 1 when the error is strictly more than t micro-ulps (exact), 0 when not,
   -1 when the result is not a usable float32. */
static int rcp_exceeds(uint32_t x, uint32_t y, uint64_t t)
{
  uint64_t num, den;
  if (!rcp_err(x, y, &num, &den)) return -1;
  return (u128)num * MICRO > (u128)t * den;
}

static int cmp_frac(uint64_t n1, uint64_t d1, uint64_t n2, uint64_t d2)
{
  u128 a = (u128)n1 * d2, b = (u128)n2 * d1;
  return a < b ? -1 : a > b;
}

static uint64_t isqrt128(u128 n)
{
  uint64_t r = 0;
  int b;
  for (b = 63; b >= 0; --b) {
    uint64_t c = r | ((uint64_t)1 << b);
    if ((u128)c * c <= n) r = c;
  }
  return r;
}

/* Common set-up of the rsqrt comparison: x = s*2^ex, y = ym*2^ey, p = -(ex+2ey). */
static int rsqrt_setup(uint32_t x, uint32_t y, uint64_t *s, uint64_t *ym, int *p)
{
  int ex, ey;
  if (!decode32(x, s, &ex) || !decode32(y, ym, &ey)) return 0;
  *p = -(ex + 2 * ey);
  return *p >= 0 && *p <= 80;
}

/* r = 1/sqrt(x); error = |y - r| / ulp(y).  1 when strictly above t micro-ulps. */
static int rsqrt_exceeds(uint32_t x, uint32_t y, uint64_t t)
{
  uint64_t s, ym, a, b;
  int p;
  u128 r;
  if (!rsqrt_setup(x, y, &s, &ym, &p)) return -1;
  r = ((u128)MICRO * MICRO) << p;
  a = (uint64_t)MICRO * ym + t;                   /* r/u > a/1e6 */
  if ((u128)s * ((u128)a * a) < r) return 1;
  b = (uint64_t)MICRO * ym;
  if (b >= t) {                                   /* r/u < (b-t)/1e6 */
    b -= t;
    if ((u128)s * ((u128)b * b) > r) return 1;
  }
  return 0;
}

/* Error in micro-ulps, correct to +-1. */
static uint64_t rsqrt_micro(uint32_t x, uint32_t y)
{
  uint64_t s, ym, z, b;
  int p;
  if (!rsqrt_setup(x, y, &s, &ym, &p)) return ~(uint64_t)0;
  z = isqrt128((((u128)MICRO * MICRO) << p) / s);
  b = (uint64_t)MICRO * ym;
  return z >= b ? z - b : b - z;
}

/* GetMant model for finite nonzero inputs.  literal=0: subnormals are
   normalized first (the manual's prose); literal=1: the pseudo-code on p.325
   taken as written (exponent field 0 stays, fraction copied unchanged). */
static uint64_t getmant_ref(int dbl, uint64_t bits, int imm, int literal)
{
  int nb = dbl ? 52 : 23, eb = dbl ? 11 : 8, bias = dbl ? 1023 : 127;
  uint64_t mask = ((uint64_t)1 << nb) - 1, fract = bits & mask, fr = fract, sign;
  unsigned ef = (unsigned)((bits >> nb) & (((uint64_t)1 << eb) - 1));
  int interv = imm & 3, sc = imm >> 2, k, hi;
  sign = bits >> (nb + eb);
  if ((sc & 2) && sign) return dbl ? UINT64_C(0xfff8000000000000) : 0xffc00000u;
  if (sc & 1) sign = 0;
  if (ef != 0) k = (int)ef - bias;
  else if (literal) k = -bias;
  else {
    int l = 0;
    while ((fract >> (l + 1)) != 0) ++l;
    k = l + 1 - bias - nb;
    fr = (fract << (nb - l)) & mask;
  }
  hi = interv == 2 || (interv == 1 && (k & 1)) ||
       (interv == 3 && ((fr >> (nb - 1)) & 1));
  return (sign << (nb + eb)) | ((uint64_t)(hi ? bias - 1 : bias) << nb) | fr;
}

/* ---- Host self-check ------------------------------------------------------ */

#define REQUIRE(x) do { if (!(x)) { \
  fprintf(stderr, "selftest failed line %d: %s\n", __LINE__, #x); return 1; } } while (0)

static int near(uint64_t a, uint64_t b) { return a + 1 >= b && a <= b + 1; }

static int selftest(void)
{
  uint64_t n, d;
  /* rcp: values from Python Fractions. */
  REQUIRE(rcp_err(0x3f800000, 0x3f800000, &n, &d) && n == 0);
  REQUIRE(rcp_err(0x3fc00000, 0x3f2aaaab, &n, &d) && d == 0xc00000 &&
          n == (uint64_t)1 << 22 && micro_of(n, d) == 333333);
  REQUIRE(rcp_err(0x3fc00000, 0x3f2aaaaa, &n, &d) && micro_of(n, d) == 666666);
  REQUIRE(rcp_err(0x3fffffff, 0x3f000000, &n, &d) && micro_of(n, d) == 500000);
  REQUIRE(rcp_err(0x3fffffff, 0x3f000001, &n, &d) && micro_of(n, d) == 499999);
  REQUIRE(rcp_err(0x3f800001, 0x3f7ffffe, &n, &d) && micro_of(n, d) == 0);
  REQUIRE(rcp_err(0x3f800000, 0x3f800001, &n, &d) && micro_of(n, d) == 1000000);
  REQUIRE(!rcp_err(0x3f800000, 0x7f800000, &n, &d));   /* inf is not usable */
  REQUIRE(!rcp_err(0x3f800000, 0x00400000, &n, &d));   /* subnormal */
  REQUIRE(!rcp_err(0x3f800000, 0xbf800000, &n, &d));   /* negative */
  REQUIRE(rcp_exceeds(0x3fc00000, 0x3f2aaaaa, 666665) == 1);
  REQUIRE(rcp_exceeds(0x3fc00000, 0x3f2aaaaa, 666666) == 1);   /* 0.6666666... */
  REQUIRE(rcp_exceeds(0x3fc00000, 0x3f2aaaaa, 666667) == 0);
  REQUIRE(rcp_exceeds(0x3f800000, 0x3f800001, 999999) == 1);
  REQUIRE(rcp_exceeds(0x3f800000, 0x3f800001, 1000000) == 0);   /* exactly 1 ulp */
  REQUIRE(rcp_exceeds(0x3f800000, 0x7fc00000, 1000000) == -1);
  {
    uint64_t n1, d1;
    rcp_err(0x3fc00000, 0x3f2aaaaa, &n1, &d1);
    rcp_err(0x3fc00000, 0x3f2aaaab, &n, &d);
    REQUIRE(cmp_frac(n, d, n1, d1) < 0 && cmp_frac(n1, d1, n, d) > 0 &&
            cmp_frac(n, d, n, d) == 0);
  }
  /* rsqrt: micro-ulp values from Python (integer sqrt of Fraction), +-1. */
  REQUIRE(near(rsqrt_micro(0x3f000000, 0x3fb504f3), 203031));
  REQUIRE(near(rsqrt_micro(0x3f000000, 0x3fb504f4), 796969));
  REQUIRE(rsqrt_micro(0x3f800000, 0x3f800000) == 0);
  REQUIRE(rsqrt_micro(0x3f800000, 0x3f800001) == 1000000);
  REQUIRE(rsqrt_micro(0x3f800000, 0x3f7fffff) == 1000000);
  REQUIRE(near(rsqrt_micro(0x3f7fffff, 0x3f800000), 250000));
  REQUIRE(near(rsqrt_micro(0x3fffffff, 0x3f3504f3), 556584));
  REQUIRE(near(rsqrt_micro(0x3f000001, 0x3fb504f3), 504076));
  REQUIRE(rsqrt_micro(0x3f800000, 0x00400000) == ~(uint64_t)0);
  /* Exact thresholds: 1/sqrt(0.5) vs 0x3fb504f3 has error 0.203031x. */
  REQUIRE(rsqrt_exceeds(0x3f000000, 0x3fb504f3, 203030) == 1);
  REQUIRE(rsqrt_exceeds(0x3f000000, 0x3fb504f3, 203032) == 0);
  REQUIRE(rsqrt_exceeds(0x3f000000, 0x3fb504f4, 796967) == 1);   /* y above r */
  REQUIRE(rsqrt_exceeds(0x3f000000, 0x3fb504f4, 796969) == 0);
  REQUIRE(rsqrt_exceeds(0x3f800000, 0x3f800001, 999999) == 1);
  REQUIRE(rsqrt_exceeds(0x3f800000, 0x3f800001, 1000000) == 0);
  REQUIRE(rsqrt_exceeds(0x3f800000, 0x3f7fffff, 999999) == 1);   /* below r */
  REQUIRE(rsqrt_exceeds(0x3f800000, 0x3f7fffff, 1000000) == 0);
  REQUIRE(rsqrt_exceeds(0x3f800000, 0x3f800000, 0) == 0);
  REQUIRE(rsqrt_exceeds(0x3f800000, 0x7f800000, 775000) == -1);
  /* getmant, float32.  Subnormal 2^-149 (k=-149, odd) and 2^-148 (even). */
  REQUIRE(getmant_ref(0, 0x00000001, 0, 0) == 0x3f800000);
  REQUIRE(getmant_ref(0, 0x00000001, 1, 0) == 0x3f000000);
  REQUIRE(getmant_ref(0, 0x00000002, 1, 0) == 0x3f800000);
  REQUIRE(getmant_ref(0, 0x00000002, 2, 0) == 0x3f000000);
  REQUIRE(getmant_ref(0, 0x00000001, 3, 0) == 0x3f800000);   /* m=1.0 < 1.5 */
  REQUIRE(getmant_ref(0, 0x00600000, 3, 0) == 0x3f400000);   /* m=1.5 -> 0.75 */
  REQUIRE(getmant_ref(0, 0x007fffff, 0, 0) == 0x3ffffffeu);
  REQUIRE(getmant_ref(0, 0x80000001, 0, 0) == 0xbf800000u);   /* sign kept */
  REQUIRE(getmant_ref(0, 0x80000001, 4, 0) == 0x3f800000u);   /* sign 0 */
  REQUIRE(getmant_ref(0, 0x80000001, 8, 0) == 0xffc00000u);   /* negative: NaN */
  REQUIRE(getmant_ref(0, 0x00000001, 8, 0) == 0x3f800000u);   /* positive: ok */
  REQUIRE(getmant_ref(0, 0x00400000, 0, 1) == 0x3fc00000u);   /* literal reading */
  REQUIRE(getmant_ref(0, 0x00400000, 0, 0) == 0x3f800000u);
  REQUIRE(getmant_ref(0, 0x40000000, 1, 0) == 0x3f000000u);   /* normal 2.0, k=1 */
  REQUIRE(getmant_ref(0, 0x40400000, 3, 0) == 0x3f400000u);   /* normal 3.0 */
  REQUIRE(getmant_ref(0, 0x40400000, 3, 1) == 0x3f400000u);   /* same when normal */
  /* getmant, float64. */
  REQUIRE(getmant_ref(1, 1, 0, 0) == UINT64_C(0x3ff0000000000000));
  REQUIRE(getmant_ref(1, 1, 1, 0) == UINT64_C(0x3ff0000000000000));   /* k=-1074 even */
  REQUIRE(getmant_ref(1, 2, 1, 0) == UINT64_C(0x3fe0000000000000));   /* k=-1073 odd */
  REQUIRE(getmant_ref(1, UINT64_C(0x000fffffffffffff), 0, 0) ==
          UINT64_C(0x3ffffffffffffffe));
  REQUIRE(getmant_ref(1, UINT64_C(0x8000000000000001), 8, 0) ==
          UINT64_C(0xfff8000000000000));
  printf("S5-09 selftest ok\n");
  return 0;
}

#ifndef HOST_LOGIC
/* ---- Native part (KNC only) ------------------------------------------------ */

typedef union {
  uint32_t u[16]; float f[16]; uint64_t q[8];
} vec;
static vec vin __attribute__((aligned(64)));
static vec vout __attribute__((aligned(64)));

static unsigned get_mxcsr(void)
{
  unsigned m;
  __asm__ volatile ("stmxcsr %0" : "=m"(m));
  return m;
}
static void set_mxcsr(unsigned m) { __asm__ volatile ("ldmxcsr %0" : : "m"(m)); }
static unsigned base_mxcsr;   /* default control bits with DAZ and FZ clear */
static void arm_flags(void) { set_mxcsr(base_mxcsr); }
static unsigned read_flags(void)
{
  unsigned f = get_mxcsr() & 0x3fu;   /* PE UE OE ZE DE IE = bits 5..0 */
  set_mxcsr(base_mxcsr);
  return f;
}

/* vout = estimate(vin) under mask k; vout keeps its contents in the other lanes. */
#define EST_ASM(INSN) __asm__ volatile ( \
  "vmovaps (%[i]), %%zmm1\n\tvmovaps (%[o]), %%zmm0\n\tkmov %[k], %%k1\n\t" \
  INSN " %%zmm1, %%zmm0%{%%k1%}\n\tvmovaps %%zmm0, (%[o])" \
  : : [i] "r"(vin.u), [o] "r"(vout.u), [k] "r"(k) : "zmm0", "zmm1", "k1", "memory")
static void estimate(int rsqrt, unsigned k)
{
  if (rsqrt) EST_ASM("vrsqrt23ps"); else EST_ASM("vrcp23ps");
}

static void print_micro(uint64_t m) { printf("%u.%06u", (unsigned)(m / MICRO), (unsigned)(m % MICRO)); }

static int probe_rcp(void)
{
  uint32_t base, w_x = 0, w_y = 0;
  uint64_t wn = 0, wd = 1;
  uint64_t bad = 0, over = 0, over1 = 0;
  int i;
  arm_flags();
  for (base = 0; base < (1u << 23); base += 16) {
    for (i = 0; i < 16; ++i) vin.u[i] = 0x3f800000u + base + (uint32_t)i;
    estimate(0, 0xffff);
    for (i = 0; i < 16; ++i) {
      uint64_t n, d;
      if (!rcp_err(vin.u[i], vout.u[i], &n, &d)) { ++bad; continue; }
      if ((u128)n * MICRO > (u128)912000 * d) ++over;
      if (n > d) ++over1;
      if (cmp_frac(n, d, wn, wd) > 0) { wn = n; wd = d; w_x = vin.u[i]; w_y = vout.u[i]; }
    }
  }
  printf("S5-09 P1a vrcp23ps n=8388608 max_err_ulp=");
  print_micro(micro_of(wn, wd));
  printf(" at_x=0x%08x y=0x%08x over_0.912=%llu over_1ulp=%llu bad_results=%llu flags=0x%02x bound=0.912 check=%s\n",
         w_x, w_y, (unsigned long long)over, (unsigned long long)over1,
         (unsigned long long)bad, read_flags(), over == 0 && bad == 0 ? "ok" : "FAIL");
  return over != 0 || bad != 0;
}

static int probe_rsqrt(void)
{
  uint32_t base, w_x = 0, w_y = 0;
  uint64_t t = 0, bad = 0, over = 0, over1 = 0;
  int i;
  arm_flags();
  for (base = 0; base < (1u << 24); base += 16) {
    for (i = 0; i < 16; ++i) vin.u[i] = 0x3f000000u + base + (uint32_t)i;
    estimate(1, 0xffff);
    for (i = 0; i < 16; ++i) {
      int r = rsqrt_exceeds(vin.u[i], vout.u[i], 775000);
      if (r < 0) { ++bad; continue; }
      over += r;
      over1 += rsqrt_exceeds(vin.u[i], vout.u[i], MICRO) == 1;
      if (rsqrt_exceeds(vin.u[i], vout.u[i], t) == 1) {
        uint64_t e = rsqrt_micro(vin.u[i], vout.u[i]);
        if (e > t) t = e;
        w_x = vin.u[i]; w_y = vout.u[i];
      }
    }
  }
  printf("S5-09 P1b vrsqrt23ps n=16777216 max_err_ulp=");
  print_micro(t);
  printf(" at_x=0x%08x y=0x%08x over_0.775=%llu over_1ulp=%llu bad_results=%llu flags=0x%02x bound=0.775 check=%s\n",
         w_x, w_y, (unsigned long long)over, (unsigned long long)over1,
         (unsigned long long)bad, read_flags(), over == 0 && bad == 0 ? "ok" : "FAIL");
  return over != 0 || bad != 0;
}

/* ---- P1c ------------------------------------------------------------------ */
#define GM_ASM(INSN, IMM, KM) __asm__ volatile ( \
  "vmovaps (%[i]), %%zmm1\n\tkmov %[k], %%k1\n\t" \
  INSN " $" #IMM ", %%zmm1, %%zmm0%{%%k1%}\n\tvmovaps %%zmm0, (%[o])" \
  : : [i] "r"(vin.u), [o] "r"(vout.u), [k] "r"(KM) : "zmm0", "zmm1", "k1", "memory")
#define GM_CASE(IMM) \
  case IMM: \
    if (dbl) { GM_ASM("vgetmantpd", IMM, 0xffu); } \
    else { GM_ASM("vgetmantps", IMM, 0xffffu); } \
    break;
static void getmant(int dbl, int imm)
{
  switch (imm) {
    GM_CASE(0) GM_CASE(1) GM_CASE(2) GM_CASE(3) GM_CASE(4) GM_CASE(5)
    GM_CASE(6) GM_CASE(7) GM_CASE(8) GM_CASE(9) GM_CASE(10) GM_CASE(11)
    GM_CASE(12) GM_CASE(13) GM_CASE(14) GM_CASE(15)
  }
}

/* Subnormal fractions first (both signs), then normal controls. */
static int make_inputs(int dbl, uint64_t *v, int *nsub)
{
  int nb = dbl ? 52 : 23, n = 0, i, nf = 0;
  uint64_t ones = ((uint64_t)1 << nb) - 1, fr[96], sgn = (uint64_t)1 << (dbl ? 63 : 31);
  for (i = 0; i < nb; ++i) fr[nf++] = (uint64_t)1 << i;
  fr[nf++] = ones; fr[nf++] = ones - 1; fr[nf++] = 3; fr[nf++] = 0xb;
  fr[nf++] = ((uint64_t)1 << (nb - 1)) | 1; fr[nf++] = (uint64_t)3 << (nb - 2);
  fr[nf++] = ((uint64_t)3 << (nb - 2)) - 1; fr[nf++] = ones / 3; fr[nf++] = ones / 6;
  for (i = 0; i < nf; ++i) { v[n++] = fr[i]; v[n++] = fr[i] | sgn; }
  *nsub = n;
  if (dbl) {
    v[n++] = UINT64_C(0x0010000000000000); v[n++] = UINT64_C(0x3ff0000000000000);
    v[n++] = UINT64_C(0x4000000000000000); v[n++] = UINT64_C(0x4008000000000000);
    v[n++] = UINT64_C(0x7fefffffffffffff); v[n++] = UINT64_C(0xc008000000000000);
  } else {
    v[n++] = 0x00800000u; v[n++] = 0x3f800000u; v[n++] = 0x40000000u;
    v[n++] = 0x40400000u; v[n++] = 0x7f7fffffu; v[n++] = 0xc0400000u;
  }
  return n;
}

static int probe_getmant(int dbl)
{
  uint64_t in[200], prose = 0, literal = 0, neither = 0, ctl_ok = 0, ctl = 0;
  int n, nsub, imm, i, lanes = dbl ? 8 : 16, j;
  unsigned flags = 0;
  n = make_inputs(dbl, in, &nsub);
  for (imm = 0; imm < 16; ++imm)
    for (i = 0; i < n; i += lanes) {
      int cnt = n - i < lanes ? n - i : lanes;
      for (j = 0; j < lanes; ++j) {
        uint64_t b = in[i + (j < cnt ? j : cnt - 1)];
        if (dbl) vin.q[j] = b; else vin.u[j] = (uint32_t)b;
      }
      arm_flags();
      getmant(dbl, imm);
      flags |= read_flags();
      for (j = 0; j < cnt; ++j) {
        uint64_t hw = dbl ? vout.q[j] : vout.u[j], b = in[i + j];
        uint64_t p = getmant_ref(dbl, b, imm, 0), l = getmant_ref(dbl, b, imm, 1);
        if (i + j < nsub) {
          if (hw == p) ++prose; else if (hw == l) ++literal; else ++neither;
        } else {
          ++ctl;
          ctl_ok += hw == p;
        }
      }
    }
  printf("S5-09 P1c %s daz=0 mxcsr=0x%04x subnormal_cases=%llu prose=%llu literal=%llu neither=%llu "
         "normal_controls_ok=%llu/%llu flags_or=0x%02x check=%s\n",
         dbl ? "vgetmantpd" : "vgetmantps", base_mxcsr,
         (unsigned long long)(prose + literal + neither), (unsigned long long)prose,
         (unsigned long long)literal, (unsigned long long)neither,
         (unsigned long long)ctl_ok, (unsigned long long)ctl, flags,
         neither == 0 && literal == 0 && ctl_ok == ctl ? "ok" : "FAIL");
  return !(neither == 0 && literal == 0 && ctl_ok == ctl);
}

/* ---- P1d ------------------------------------------------------------------ */
static unsigned flags_of(int rsqrt, uint32_t special, unsigned k)
{
  int i;
  for (i = 0; i < 16; ++i) { vin.u[i] = 0x3f800000u; vout.u[i] = 0x12345678u; }
  vin.u[0] = special;
  arm_flags();
  estimate(rsqrt, k);
  return read_flags();
}

static int probe_masked(void)
{
  /* Order: rcp(0) #Z, rsqrt(-1) #I, rcp(sNaN) #I.  Lane 0 holds the special value. */
  unsigned zc = flags_of(0, 0x00000000u, 0x0001), zm0 = flags_of(0, 0x00000000u, 0x0000),
           zm1 = flags_of(0, 0x00000000u, 0xfffe);
  unsigned ic = flags_of(1, 0xbf800000u, 0x0001), im0 = flags_of(1, 0xbf800000u, 0x0000),
           im1 = flags_of(1, 0xbf800000u, 0xfffe);
  unsigned sc = flags_of(0, 0x7fa00000u, 0x0001), sm0 = flags_of(0, 0x7fa00000u, 0x0000),
           sm1 = flags_of(0, 0x7fa00000u, 0xfffe);
  int ok = zc == 0x04 && ic == 0x01 && sc == 0x01 &&
           !zm0 && !zm1 && !im0 && !im1 && !sm0 && !sm1;
  printf("S5-09 P1d masked-lane-flags rcp0: enabled=0x%02x mask0=0x%02x lane0-off=0x%02x "
         "rsqrt-1: enabled=0x%02x mask0=0x%02x lane0-off=0x%02x "
         "rcp-sNaN: enabled=0x%02x mask0=0x%02x lane0-off=0x%02x "
         "(controls must be 0x04, 0x01, 0x01; the rest 0x00) check=%s\n",
         zc, zm0, zm1, ic, im0, im1, sc, sm0, sm1, ok ? "ok" : "FAIL");
  return !ok;
}

/* ---- P1e ------------------------------------------------------------------ */
static int probe_all_ones(void)
{
  uint64_t n, d;
  uint32_t y;
  int i, same = 1;
  for (i = 0; i < 16; ++i) vin.u[i] = 0x3fffffffu;
  arm_flags();
  estimate(0, 0xffff);
  y = vout.u[0];
  for (i = 1; i < 16; ++i) same &= vout.u[i] == y;
  printf("S5-09 P1e vrcp23ps(0x3fffffff)=0x%08x lanes_equal=%d ", y, same);
  if (rcp_err(0x3fffffffu, y, &n, &d)) {
    printf("err_ulp=");
    print_micro(micro_of(n, d));
  } else
    printf("err_ulp=n/a");
  printf(" step15=%s flags=0x%02x check=%s\n",
         y == 0x3f000000u ? "needed(returns 1/2)" : y == 0x3f000001u ? "not-needed(returns RN)" : "other",
         read_flags(), same && (y == 0x3f000000u || y == 0x3f000001u) ? "ok" : "FAIL");
  return !(same && (y == 0x3f000000u || y == 0x3f000001u));
}

static int native(void)
{
  int bad = 0;
  setvbuf(stdout, NULL, _IOLBF, 0);
  base_mxcsr = get_mxcsr() & ~0x80c0u & ~0x3fu;   /* DAZ (bit 6) and FZ (bit 15) clear, no flags */
  printf("S5-09 estimate probe, mxcsr=0x%04x\n", base_mxcsr);
  bad += probe_rcp();
  bad += probe_rsqrt();
  bad += probe_getmant(0);
  bad += probe_getmant(1);
  bad += probe_masked();
  bad += probe_all_ones();
  printf("S5-09 done failures=%d\n", bad);
  return bad != 0;
}
#endif

int main(int argc, char **argv)
{
  if (argc == 2 && !strcmp(argv[1], "--selftest")) return selftest();
#ifndef HOST_LOGIC
  if (argc == 2 && !strcmp(argv[1], "--native")) return native();
#endif
  fprintf(stderr, "usage: %s --selftest (reference arithmetic; host or KNC build)%s\n", argv[0],
#ifndef HOST_LOGIC
          " or --native (KNC build, card only)"
#else
          ""
#endif
          );
  return 2;
}
