/* S10-09 host model of the V8DF division and square root sequences of
   ix86_knc_expand_div and ix86_knc_expand_sqrt (i386-knc.cc), after
   docs/research/knc-div-sqrt.md section 3.  Each emulated instruction is
   one correctly rounded MPFR operation at 53 bits; the estimate is every
   24-bit value within one ulp of the reciprocal (square root) of the
   operand rounded to 24 bits, which contains everything vrcp23ps and
   vrsqrt23ps may return (0.912 and 0.775 ulp).  Results and flags are
   compared with the integer references of knc-v8df-divsqrt.c, in all four
   rounding modes.  --omit-div-blend and --omit-sqrt-blend drop the
   all-ones blends, and must fail.

   gcc -O2 -std=gnu11 knc-v8df-model.c -lmpfr -lgmp  */
#define KNC_V8DF_HOST_MODEL
#include "knc-v8df-divsqrt.c"
#include <stdlib.h>
#include <mpfr.h>

#define N MPFR_RNDN
static const mpfr_rnd_t MR[4] = { MPFR_RNDN, MPFR_RNDD, MPFR_RNDU, MPFR_RNDZ };
static const char *const mname[4] = { "RN", "RD", "RU", "RZ" };
static int P, PE, div_blend = 1, sqrt_blend = 1;
static long failures;

enum { NT = 40, NW = 8, NE = 8 };
static mpfr_t T[NT], W[NW], EST[NE], VF, Y, R53;
#define one T[0]
#define half T[1]
#define c38 T[2]
#define c516 T[3]
#define all1 T[4]	/* 2 - 2^(1-P), the all-ones divisor */
#define yall1 T[5]	/* RN(1/all1) = 1/2 + 2^-P */
#define sall1 T[6]	/* 1 - 2^-P, the all-ones root argument */
#define neg T[7]

static void
set_precision (int p, int pe)
{
  static int init;
  P = p; PE = pe;
  for (int i = 0; i < NT; ++i)
    { if (!init) mpfr_init2 (T[i], p); else mpfr_set_prec (T[i], p); }
  for (int i = 0; i < NE; ++i)
    { if (!init) mpfr_init2 (EST[i], pe); else mpfr_set_prec (EST[i], pe); }
  if (!init)
    {
      for (int i = 0; i < NW; ++i) mpfr_init2 (W[i], 512);
      mpfr_init2 (VF, pe); mpfr_init2 (Y, pe); mpfr_init2 (R53, 53);
    }
  else { mpfr_set_prec (VF, pe); mpfr_set_prec (Y, pe); }
  init = 1;
  mpfr_set_ui (one, 1, N);
  mpfr_set_ui_2exp (half, 1, -1, N);
  mpfr_set_ui_2exp (c38, 3, -3, N);
  mpfr_set_ui_2exp (c516, 5, -4, N);
  mpfr_set_ui_2exp (all1, 1, 1 - p, N); mpfr_ui_sub (all1, 2, all1, N);
  mpfr_set_ui_2exp (yall1, 1, -p, N); mpfr_add (yall1, yall1, half, N);
  mpfr_set_ui_2exp (sall1, 1, -p, N); mpfr_ui_sub (sall1, 1, sall1, N);
}

/* z - x y, and whether it was inexact.  */
static int
fnma (mpfr_t r, mpfr_t x, mpfr_t y, mpfr_t z, int m)
{
  mpfr_neg (neg, x, N);
  return mpfr_fma (r, neg, y, z, MR[m]) != 0;
}

/* The PE-bit values within one ulp (in their own binade) of 1/v or
   1/sqrt(v), v being X rounded to PE bits; left in EST.  */
static int
estimates (mpfr_t x, int rsqrt)
{
  int n = 0;
  mpfr_set (VF, x, N);
  if (rsqrt) mpfr_rec_sqrt (W[0], VF, N); else mpfr_ui_div (W[0], 1, VF, N);
  mpfr_set (Y, W[0], N);
  for (int i = 0; i < 3; ++i) mpfr_nextbelow (Y);
  for (int i = 0; i < 7; ++i, mpfr_nextabove (Y))
    {
      mpfr_sub (W[1], Y, W[0], N);
      mpfr_set_ui_2exp (W[2], 1, mpfr_get_exp (Y) - PE, N);
      if (mpfr_cmpabs (W[1], W[2]) <= 0) mpfr_set (EST[n++], Y, N);
    }
  return n;
}

/* ---- Division core (section 3.1).  ---- */
#define e0 T[8]
#define tt T[9]
#define pp T[10]
#define y1 T[11]
#define e1 T[12]
#define y2 T[13]
#define q0 T[14]
#define r0 T[15]
#define q1 T[16]
#define r1 T[17]
#define qm T[18]
#define lo T[19]
#define hi T[20]
#define ma T[21]
#define mb T[22]
#define rr T[23]
#define t1 T[24]

static long y1_unfaithful, e1_inexact, y2_not_rn, condc_fail, q1_unfaithful,
  r1_inexact;

/* y2 from the estimate Y0 of 1/mb; counts the claims of the proof.  */
static void
reciprocal (mpfr_t y0)
{
  fnma (e0, mb, y0, one, RN);
  mpfr_fma (tt, e0, e0, e0, N);
  mpfr_fma (pp, tt, e0, e0, N);
  mpfr_fma (y1, y0, pp, y0, N);
  e1_inexact += fnma (e1, mb, y1, one, RN);
  mpfr_fma (y2, e1, y1, y1, N);
  mpfr_ui_div (lo, 1, mb, MPFR_RNDD); mpfr_ui_div (hi, 1, mb, MPFR_RNDU);
  y1_unfaithful += mpfr_cmp (y1, lo) && mpfr_cmp (y1, hi);
  if (div_blend && !mpfr_cmp (mb, all1)) mpfr_set (y2, yall1, N);
}

/* Lemma B's condition |mb y2 - 1| < 1/(B+1), and y2 = RN(1/mb).  */
static void
reciprocal_claims (unsigned long B)
{
  mpfr_mul (W[1], mb, y2, N); mpfr_sub_ui (W[1], W[1], 1, N);
  mpfr_mul_ui (W[1], W[1], B + 1, N);
  condc_fail += mpfr_cmpabs (W[1], one) >= 0;
  mpfr_ui_div (lo, 1, mb, N);
  y2_not_rn += mpfr_cmp (y2, lo) != 0;
}

/* q1 and r1 from ma, mb and y2.  */
static void
quotient (void)
{
  mpfr_mul (q0, ma, y2, N);
  fnma (r0, mb, q0, ma, RN);
  mpfr_fma (q1, r0, y2, q0, N);
  r1_inexact += fnma (r1, mb, q1, ma, RN);
  mpfr_div (lo, ma, mb, MPFR_RNDD); mpfr_div (hi, ma, mb, MPFR_RNDU);
  q1_unfaithful += mpfr_cmp (q1, lo) && mpfr_cmp (q1, hi);
}

static void
d1_reciprocal (long nb)
{
  long cands = 0;
  y1_unfaithful = e1_inexact = y2_not_rn = condc_fail = 0;
  for (long i = -64; i < nb; ++i)
    {
      unsigned long B = i < -32 ? HID + (i + 64) : i < 0 ? 2 * HID + i : rsig ();
      mpfr_set_ui_2exp (mb, B, -52, N);
      int n = estimates (mb, 0);
      for (int c = 0; c < n; ++c, ++cands)
	{ reciprocal (EST[c]); reciprocal_claims (B); }
    }
  long bad = y1_unfaithful + e1_inexact + condc_fail;
  /* Without the blend, y2 = RN(1/b) fails for the all-ones divisor only.  */
  failures += bad + (div_blend ? y2_not_rn : 0);
  printf ("D1 reciprocal p=53: b=%ld estimates=%ld y1_unfaithful=%ld "
	  "e1_inexact=%ld y2_not_RN=%ld condC_fail=%ld\n", nb + 64, cands,
	  y1_unfaithful, e1_inexact, y2_not_rn, condc_fail);
}

/* Every pair of P-bit significands, every estimate, four modes.  */
static void
d2_exhaustive (int p, int pe)
{
  long runs = 0, fail[4] = { 0 }, flag = 0;
  set_precision (p, pe);
  y1_unfaithful = e1_inexact = y2_not_rn = condc_fail = q1_unfaithful
    = r1_inexact = 0;
  for (unsigned long B = 1UL << (p - 1); B < 1UL << p; ++B)
    {
      mpfr_set_ui_2exp (mb, B, 1 - p, N);
      int n = estimates (mb, 0);
      for (int c = 0; c < n; ++c)
	{
	  reciprocal (EST[c]); reciprocal_claims (B);
	  for (unsigned long A = 1UL << (p - 1); A < 1UL << p; ++A, ++runs)
	    {
	      mpfr_set_ui_2exp (ma, A, 1 - p, N);
	      quotient ();
	      for (int m = 0; m < 4; ++m)
		{
		  int ix = mpfr_fma (qm, r1, y2, q1, MR[m]) != 0;
		  int rx = mpfr_div (lo, ma, mb, MR[m]) != 0;
		  fail[m] += mpfr_cmp (qm, lo) != 0;
		  flag += ix != rx;
		}
	    }
	}
    }
  failures += fail[0] + fail[1] + fail[2] + fail[3] + flag + y1_unfaithful
	      + e1_inexact + condc_fail + q1_unfaithful + r1_inexact;
  printf ("D2 div p=%d estimate=%d bits: runs=%ld y1_unfaithful=%ld "
	  "condC_fail=%ld q1_unfaithful=%ld r1_inexact=%ld fail RN=%ld RD=%ld "
	  "RU=%ld RZ=%ld inexact_flag_wrong=%ld\n", p, pe, runs, y1_unfaithful,
	  condc_fail, q1_unfaithful, r1_inexact, fail[0], fail[1], fail[2],
	  fail[3], flag);
}

/* ---- Whole paths on bit patterns.  ---- */
static uint64_t
dbits (mpfr_t v)
{
  double d = mpfr_get_d (v, N);
  uint64_t b;
  memcpy (&b, &d, sizeof b);
  return b;
}

/* An exact value rounded as vmulpd rounds its product: gradual underflow,
   tininess after rounding.  Independent of pack () in the reference.  */
static uint64_t
ieee (mpfr_t v, int mode, int *flags)
{
  uint64_t s = mpfr_signbit (v) ? SIGN : 0;
  if (mpfr_zero_p (v)) return s;
  int t = mpfr_set (R53, v, MR[mode]);
  mpfr_exp_t e = mpfr_get_exp (R53);
  if (e > 1024)
    {
      *flags |= FE_OVERFLOW | FE_INEXACT;
      int inf = mode == RN || (mode == RU && !s) || (mode == RD && s);
      return s | (inf ? INF : INF - 1);
    }
  if (e >= -1021)
    {
      if (t) *flags |= FE_INEXACT;
      return dbits (R53);
    }
  mpfr_mul_2si (W[6], v, 1074, N);
  if (mpfr_rint (R53, W[6], MR[mode])) *flags |= FE_UNDERFLOW | FE_INEXACT;
  mpfr_abs (R53, R53, N);
  return s | mpfr_get_ui (R53, N);
}

/* vmulpd on operands that are zero, one, infinite or NaN.  */
static uint64_t
mul_special (uint64_t x, uint64_t y, int *flags)
{
  uint64_t xa = x & ~SIGN, ya = y & ~SIGN, s = (x ^ y) & SIGN;
  if (xa > INF || ya > INF)
    {
      if ((xa > INF && !(x & QBIT)) || (ya > INF && !(y & QBIT)))
	*flags |= FE_INVALID;
      return (xa > INF ? x : y) | QBIT;
    }
  if ((xa == INF && !ya) || (!xa && ya == INF))
    { *flags |= FE_INVALID; return QNAN; }
  return s | (xa == INF || ya == INF ? INF : !xa || !ya ? 0 : ONE);
}

enum { NSET = 12 };
static const char *const sname[NSET] =
  { "div-midpoint", "div-markstein", "div-exponent", "div-tiny-midpoint",
    "div-special", "5", "6", "7", "sqrt-midpoint", "sqrt-double",
    "sqrt-exponent", "sqrt-special" };
static long cases[NSET], runs[NSET], fail[NSET][4], flagfail[NSET];

static void
compare (unsigned set, int m, uint64_t got, int gf, uint64_t want, int wf)
{
  ++runs[set];
  fail[set][m] += got != want;
  flagfail[set] += gf != wf;
}

static void
pair (unsigned set, uint64_t a, uint64_t b)
{
  uint64_t aa = a & ~SIGN, bb = b & ~SIGN, sb = b & SIGN;
  int afin = aa - 1 < INF - 1, bfin = bb - 1 < INF - 1;
  ++cases[set];
  if (!afin || !bfin)
    {
      /* Rare path, special lanes: regular operands become signed one, the
	 divisor becomes its reciprocal class, and one vmulpd gives the
	 result and flags; a masked vrcp23ps of zero adds #Z.  */
      uint64_t ap = afin ? (a & SIGN) | ONE : a;
      uint64_t rp = !bb ? sb | INF : bb == INF ? sb : bfin ? sb | ONE : b;
      for (int m = 0; m < 4; ++m)
	{
	  int gf = 0, wf;
	  uint64_t got = mul_special (ap, rp, &gf);
	  if (!bb && afin) gf |= FE_DIVBYZERO;
	  uint64_t want = ref_div (a, b, m, &wf);
	  compare (set, m, got, gf, want, wf);
	}
      return;
    }
  int ea, eb;
  unsigned long A = unpack (aa, &ea), B = unpack (bb, &eb);
  int k = ea - eb;
  mpfr_set_ui_2exp (ma, A, -52, N);
  if ((a ^ b) & SIGN) mpfr_neg (ma, ma, N);
  mpfr_set_ui_2exp (mb, B, -52, N);
  int n = estimates (mb, 0);
  for (int c = 0; c < n; ++c)
    {
      reciprocal (EST[c]);
      quotient ();
      for (int m = 0; m < 4; ++m)
	{
	  int gf = mpfr_fma (qm, r1, y2, q1, MR[m]) ? FE_INEXACT : 0, wf;
	  uint64_t got;
	  if ((uint32_t) (k + 1021) <= 2044)
	    got = dbits (qm) + ((uint64_t) (int64_t) k << 52);
	  else
	    {
	      /* Rare path, range lanes: qm 2^h is exact and the second
		 multiply rounds once.  */
	      int kc = k < -1100 ? -1100 : k > 1100 ? 1100 : k, h = kc >> 1;
	      mpfr_mul_2si (t1, qm, h, N);
	      mpfr_mul_2si (W[3], t1, kc - h, N);
	      got = ieee (W[3], m, &gf);
	      r1_inexact += fnma (rr, mb, qm, ma, RN);
	      int nonexact = !mpfr_zero_p (rr);
	      /* Tiny and inexact, though the scaling itself was exact.  */
	      if (nonexact && (got & ~SIGN) < HID)
		gf |= FE_UNDERFLOW | FE_INEXACT;
	      if (m == RN && k < 0)
		{
		  /* w = RZ(2 t1 s2 - 2 res) is nonzero only on a tie; then
		     the residual's sign says which neighbour a/b rounds to.  */
		  int dummy = 0;
		  double d;
		  memcpy (&d, &got, sizeof d);
		  mpfr_set_d (W[5], d, N);
		  mpfr_sub (W[4], W[3], W[5], N);
		  mpfr_mul_2si (W[4], W[4], 1, N);
		  uint64_t w = ieee (W[4], RZ, &dummy);
		  if ((w & ~SIGN) && nonexact
		      && !mpfr_signbit (rr) == !(w & SIGN))
		    got = (w ^ got) & SIGN ? got - 1 : got + 1;
		}
	    }
	  uint64_t want = ref_div (a, b, m, &wf);
	  compare (set, m, got, gf, want, wf);
	}
    }
}

/* ---- Square root core (section 3.2).  ---- */
#define mm T[25]
#define ss T[26]
#define eps T[27]
#define p1 T[28]
#define p2 T[29]
#define g0 T[30]
#define eg T[31]
#define g1 T[32]
#define hy T[33]
#define h1 T[34]
#define dd T[35]
#define g2 T[36]

static long s_inexact, eg_inexact, g1_unfaithful, g1_not_rn, d_inexact;

static void
root (mpfr_t y0)
{
  s_inexact += mpfr_mul (ss, y0, y0, N) != 0;
  fnma (eps, mm, ss, one, RN);
  mpfr_fma (p1, eps, c516, c38, N);
  mpfr_fma (p2, eps, p1, half, N);
  mpfr_mul (pp, eps, p2, N);
  mpfr_mul (g0, mm, y0, N);
  eg_inexact += mpfr_fms (eg, mm, y0, g0, N) != 0;
  mpfr_fma (tt, g0, pp, eg, N);
  mpfr_add (g1, g0, tt, N);
  if (sqrt_blend && !mpfr_cmp (mm, sall1)) mpfr_set (g1, mm, N);
  mpfr_mul (hy, half, y0, N);
  mpfr_fma (h1, hy, pp, hy, N);
  d_inexact += fnma (dd, g1, g1, mm, RN);
  mpfr_sqrt (lo, mm, MPFR_RNDD); mpfr_sqrt (hi, mm, MPFR_RNDU);
  g1_unfaithful += mpfr_cmp (g1, lo) && mpfr_cmp (g1, hi);
  mpfr_sqrt (lo, mm, N);
  g1_not_rn += mpfr_cmp (g1, lo) != 0;
}

/* Every P-bit argument in [1/2,2), every estimate, four modes.  */
static void
s2_exhaustive (int p, int pe)
{
  long nruns = 0, bad[4] = { 0 }, flag = 0;
  set_precision (p, pe);
  s_inexact = eg_inexact = g1_unfaithful = g1_not_rn = d_inexact = 0;
  for (int e = -p; e <= 1 - p; ++e)
    for (unsigned long M = 1UL << (p - 1); M < 1UL << p; ++M)
      {
	mpfr_set_ui_2exp (mm, M, e, N);
	int n = estimates (mm, 1);
	for (int c = 0; c < n; ++c, ++nruns)
	  {
	    root (EST[c]);
	    for (int m = 0; m < 4; ++m)
	      {
		int ix = mpfr_fma (g2, dd, h1, g1, MR[m]) != 0;
		int rx = mpfr_sqrt (lo, mm, MR[m]) != 0;
		bad[m] += mpfr_cmp (g2, lo) != 0;
		flag += ix != rx;
	      }
	  }
      }
  failures += bad[0] + bad[1] + bad[2] + bad[3] + flag + s_inexact
	      + eg_inexact + g1_unfaithful;
  printf ("S2 sqrt p=%d estimate=%d bits: runs=%ld s_inexact=%ld "
	  "eg_inexact=%ld g1_unfaithful=%ld g1_not_RN=%ld d_inexact=%ld "
	  "fail RN=%ld RD=%ld RU=%ld RZ=%ld inexact_flag_wrong=%ld\n", p, pe,
	  nruns, s_inexact, eg_inexact, g1_unfaithful, g1_not_rn, d_inexact,
	  bad[0], bad[1], bad[2], bad[3], flag);
}

static void
single (unsigned set, uint64_t x)
{
  uint64_t xa = x & ~SIGN;
  int e = 0, n = 1;
  /* The quiet compares 0 < x < inf, and x < 0 (-inf included, -0 not).  */
  int kreg = !(x & SIGN) && xa - 1 < INF - 1;
  int kneg = (x & SIGN) && xa - 1 < INF;
  ++cases[set];
  /* vgetmantpd: [1/2,2) by exponent parity; subnormals are normalized.  */
  if (kreg)
    {
      unsigned long M = unpack (xa, &e);
      mpfr_set_ui_2exp (mm, M, e & 1 ? -53 : -52, N);
    }
  int j = (e + 1) >> 1;
  if (kreg) n = estimates (mm, 1);
  for (int c = 0; c < n; ++c)
    {
      if (kreg) root (EST[c]);
      for (int m = 0; m < 4; ++m)
	{
	  int gf = 0, wf;
	  uint64_t got = 0;
	  if (kreg)
	    {
	      if (mpfr_fma (g2, dd, h1, g1, MR[m])) gf = FE_INEXACT;
	      got = dbits (g2) + ((uint64_t) (int64_t) j << 52);
	    }
	  /* The masked vrsqrt23ps of -1 raises invalid.  */
	  if (kneg) gf |= FE_INVALID;
	  /* vfixupnanpd, table 0x206ad.  */
	  if (xa > INF)
	    { if (!(x & QBIT)) gf |= FE_INVALID; got = x | QBIT; }
	  else if (!xa || x == INF) got = x;
	  else if (x & SIGN) got = QNAN;
	  uint64_t want = ref_sqrt (x, m, &wf);
	  compare (set, m, got, gf, want, wf);
	}
    }
}

static void
report (int first, int last)
{
  for (int s = first; s <= last; ++s)
    {
      failures += fail[s][0] + fail[s][1] + fail[s][2] + fail[s][3]
		  + flagfail[s] + !cases[s];
      printf ("%s: cases=%ld runs=%ld fail RN=%ld RD=%ld RU=%ld RZ=%ld "
	      "flags_wrong=%ld\n", sname[s], cases[s], runs[s], fail[s][0],
	      fail[s][1], fail[s][2], fail[s][3], flagfail[s]);
    }
}

int
main (int argc, char **argv)
{
  setbuf (stdout, NULL);
  for (int i = 1; i < argc; ++i)
    if (!strcmp (argv[i], "--omit-div-blend")) div_blend = 0;
    else if (!strcmp (argv[i], "--omit-sqrt-blend")) sqrt_blend = 0;
    else return 2;
  (void) mname;

  for (int p = 8; p <= 11; ++p) d2_exhaustive (p, 6);
  set_precision (53, 24);
  d1_reciprocal (200000);
  y1_unfaithful = e1_inexact = q1_unfaithful = r1_inexact = 0;
  div_hard (pair, 0, 1, 20000);
  div_sweep (pair, 2, 131, 96);
  div_midpoints (pair, 3, 128);
  for (unsigned i = 0; i < NSPECIAL; ++i)
    for (unsigned j = 0; j < NSPECIAL; ++j)
      pair (4, special[i], special[j]);
  report (0, 4);
  failures += y1_unfaithful + e1_inexact + q1_unfaithful + r1_inexact;
  printf ("div p=53 claims: y1_unfaithful=%ld e1_inexact=%ld "
	  "q1_unfaithful=%ld r1_inexact=%ld\n", y1_unfaithful, e1_inexact,
	  q1_unfaithful, r1_inexact);

  s2_exhaustive (12, 6);
  s2_exhaustive (14, 7);
  s2_exhaustive (16, 8);
  s2_exhaustive (18, 9);
  s2_exhaustive (20, 10);
  set_precision (53, 24);
  s_inexact = eg_inexact = g1_unfaithful = g1_not_rn = d_inexact = 0;
  sqrt_hard (single, 8, 9, 1L << 16);
  sqrt_sweep (single, 10, 4096);
  for (unsigned i = 0; i < NSPECIAL; ++i) single (11, special[i]);
  report (8, 11);
  failures += s_inexact + eg_inexact + g1_unfaithful;
  printf ("sqrt p=53 claims: s_inexact=%ld eg_inexact=%ld g1_unfaithful=%ld "
	  "g1_not_RN=%ld d_inexact=%ld\n", s_inexact, eg_inexact,
	  g1_unfaithful, g1_not_rn, d_inexact);
  printf ("div_blend=%d sqrt_blend=%d failures=%ld\n", div_blend, sqrt_blend,
	  failures);
  return failures != 0;
}
