/* Qualification of libknc_vmath's v1a functions (S10-07, ADR-0014 point 4): sin, cos, tan, log10,
   atan2, sinh, cosh and tanh on 16 floats and on 8 doubles, and atanf; and of the v1b functions
   (S10-08): acos, asin, cbrt, erf, erfc, exp2, exp10, expm1, log1p, log2 and hypot on both. It
   calls what a vectorized loop calls, the by-value entry point __knc_vmath_<name>_<lanes>, and its
   masked form. The limit is 1 ULP, except where the table of functions gives the looser bound of
   the upstream routine (erf and erfc on doubles; libknc_vmath/README.md says why).

   Special cases come from the C99 Annex F table in annex_f(), never from a libm. The other lanes
   have one of two oracles:
   - exact (the host build, -DVMATH_MPFR): MPFR at 256 bits, so max_ulp is the true error;
   - screen (the card build, or --screen on the host): the x87 long double libm, which only
     screens. Every lane screened above --dump (default 0.5), every lane of the special grid and
     every lane of one block in 1024 (the "sample") prints a "check" line, and the host build's
     `qualify_v1 <function> --recheck` recomputes those lines exactly from its standard input. The
     sample measures the screen's own error, which bounds the lanes that were not dumped by --dump
     plus that error (tests/vmath/card_qualify.py).
   The inputs depend only on the block number, so any worker count, and a host build, sees the same
   set:
   - one argument: --blocks blocks spread evenly over all bit patterns of the type, each of
     consecutive patterns ("sweep"), and as many "dense" blocks: |x| up to the function's range,
     half uniform and half spread over the 40 binades below it; log10 and log2 take positive x of
     every exponent, a quarter of them near 1; log1p takes x of every exponent above -1, a quarter
     of them within 2^-63 to 1 of -1;
   - atan2 and hypot: --blocks blocks of random pairs (a quarter raw bit patterns, a quarter
     independent magnitudes in [2^-40, 2^40), half with magnitudes within 2^12 of each other;
     hypot's magnitudes span every exponent instead) and the grid of all pairs of special values.
   One block in 64 also runs masked, with random bits above the lanes' in the mask: an inactive
   lane must return its first argument's bits, an active lane the all-active result. Round to
   nearest only; errno and flags are not checked. */
#define _GNU_SOURCE
#include <float.h>
#include <math.h>
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef VMATH_MPFR
#include <mpfr.h>
#endif

#include "knc_vmath.h"

typedef __knc_vmath_v16sf vf;
typedef __knc_vmath_v8df vd;
enum { SIN, COS, TAN, LOG10, ATAN, ATAN2, SINH, COSH, TANH,
       ACOS, ASIN, CBRT, ERF, ERFC, EXP2, EXP10, EXPM1, LOG1P, LOG2, HYPOT };
enum { GRID = 1, SAMPLE };

struct function {
  const char *name;
  int id, single;
  double range; /* of the dense inputs */
  double limit; /* ULP; 0 is 1 */
  vf (*f1)(vf); vf (*f1m)(vf,unsigned); vf (*f2)(vf,vf); vf (*f2m)(vf,vf,unsigned);
  vd (*d1)(vd); vd (*d1m)(vd,unsigned); vd (*d2)(vd,vd); vd (*d2m)(vd,vd,unsigned);
};
#define F1(n,id,range) { #n "f",id,1,range,.f1 = __knc_vmath_##n##f_16,.f1m = __knc_vmath_##n##f_16_m }
#define D1(n,id,range) { #n,id,0,range,.d1 = __knc_vmath_##n##_8,.d1m = __knc_vmath_##n##_8_m }
static const struct function functions[] = {
  F1(sin,SIN,128), F1(cos,COS,128), F1(tan,TAN,128), F1(log10,LOG10,0), F1(atan,ATAN,64),
  F1(sinh,SINH,90), F1(cosh,COSH,90), F1(tanh,TANH,10),
  { "atan2f",ATAN2,1,0,.f2 = __knc_vmath_atan2f_16,.f2m = __knc_vmath_atan2f_16_m },
  D1(sin,SIN,128), D1(cos,COS,128), D1(tan,TAN,128), D1(log10,LOG10,0),
  D1(sinh,SINH,711), D1(cosh,COSH,711), D1(tanh,TANH,22),
  { "atan2",ATAN2,0,0,.d2 = __knc_vmath_atan2_8,.d2m = __knc_vmath_atan2_8_m },
  F1(acos,ACOS,1), F1(asin,ASIN,1), F1(cbrt,CBRT,8), F1(erf,ERF,4), F1(erfc,ERFC,11),
  F1(exp2,EXP2,151), F1(exp10,EXP10,46), F1(expm1,EXPM1,89), F1(log1p,LOG1P,0), F1(log2,LOG2,0),
  { "hypotf",HYPOT,1,0,.f2 = __knc_vmath_hypotf_16,.f2m = __knc_vmath_hypotf_16_m },
  D1(acos,ACOS,1), D1(asin,ASIN,1), D1(cbrt,CBRT,8), D1(exp2,EXP2,1076), D1(exp10,EXP10,324),
  D1(expm1,EXPM1,710), D1(log1p,LOG1P,0), D1(log2,LOG2,0),
  /* Upstream's tables hold erf(r) and erfc(r) rounded to one double (README.md). */
  { "erf",ERF,0,6,1.05,.d1 = __knc_vmath_erf_8,.d1m = __knc_vmath_erf_8_m },
  { "erfc",ERFC,0,28,1.75,.d1 = __knc_vmath_erfc_8,.d1m = __knc_vmath_erfc_8_m },
  { "hypot",HYPOT,0,0,.d2 = __knc_vmath_hypot_8,.d2m = __knc_vmath_hypot_8_m },
};
static const struct function *f;
static int lanes, negative, negative_mask, workers, pairs;
static long double limit = 1;
#ifdef VMATH_MPFR
static int screen;
#else
enum { screen = 1 };
#endif
static uint64_t blocks = 1ULL << 16, block_stride, max_dump = 2000000, dumped;
static long double dump = -1;

struct stats {
  uint64_t inputs, special_errors, mask_errors, hist[6];
  long double max_ulp;
  uint64_t worst_x, worst_y, worst_out;
} __attribute__((aligned(64)));
static struct stats totals[256];

/* A lane travels as its bit pattern, a float's in the low half. */
static double value(uint64_t bits) {
  if (f->single) { uint32_t u = (uint32_t)bits; float s; memcpy(&s,&u,4); return s; }
  double d; memcpy(&d,&bits,8); return d;
}
static uint64_t bits_of(double v) {
  if (f->single) { float s = (float)v; uint32_t u; memcpy(&u,&s,4); return u; }
  uint64_t u; memcpy(&u,&v,8); return u;
}

/* The screen needs the x87's 64-bit significand. Linux starts with it; Windows (the host build
   under Cygwin) starts its threads with 53 bits. Set precision control to 64 bits in every
   thread. */
static void extended_precision(void) {
  unsigned short cw;
  __asm__ volatile ("fnstcw %0" : "=m" (cw));
  cw |= 0x300;
  __asm__ volatile ("fldcw %0" : : "m" (cw));
}

/* C99 Annex F (F.9.1 to F.9.3): what f(a) or atan2(a,b) must return where the standard says so.
   EXACT is that value with its sign, PI_QUARTERS that many quarters of pi. */
struct special { enum { COMPUTE, NOT_A_NUMBER, EXACT, PI_QUARTERS } kind; double value; };
static struct special annex_f(double a, double b) {
  const struct special nan = { NOT_A_NUMBER,0 }, compute = { COMPUTE,0 };
#define exact(v) ((struct special){ EXACT,v })
#define pi(quarters) ((struct special){ PI_QUARTERS,quarters })
  if (f->id == HYPOT) {
    if (isinf(a) || isinf(b)) return exact(INFINITY);
    return isnan(a) || isnan(b) ? nan : a == 0 ? exact(fabs(b)) : b == 0 ? exact(fabs(a)) : compute;
  }
  if (isnan(a) || (pairs && isnan(b))) return nan;
  switch (f->id) {
  case SIN: case TAN: return a == 0 ? exact(a) : isinf(a) ? nan : compute;
  case COS: return a == 0 ? exact(1) : isinf(a) ? nan : compute;
  case LOG10: case LOG2: return a == 0 ? exact(-INFINITY) : a < 0 ? nan : a == 1 ? exact(0) : isinf(a) ? exact(a) : compute;
  case ATAN: return a == 0 ? exact(a) : isinf(a) ? pi(copysign(2,a)) : compute;
  case SINH: return a == 0 || isinf(a) ? exact(a) : compute;
  case COSH: return a == 0 ? exact(1) : isinf(a) ? exact(INFINITY) : compute;
  case TANH: case ERF: return a == 0 ? exact(a) : isinf(a) ? exact(copysign(1,a)) : compute;
  case ACOS: return fabs(a) > 1 ? nan : a == 1 ? exact(0) : compute;
  case ASIN: return fabs(a) > 1 ? nan : a == 0 ? exact(a) : compute;
  case CBRT: return a == 0 || isinf(a) ? exact(a) : compute;
  case ERFC: return isinf(a) ? exact(a < 0 ? 2 : 0) : compute;
  case EXP2: case EXP10: return a == 0 ? exact(1) : isinf(a) ? exact(a < 0 ? 0 : a) : compute;
  case EXPM1: return a == 0 ? exact(a) : isinf(a) ? exact(a < 0 ? -1 : a) : compute;
  case LOG1P: return a == 0 ? exact(a) : a == -1 ? exact(-INFINITY) : a < -1 ? nan : isinf(a) ? exact(a) : compute;
  }
  double sign = copysign(1,a);
  if (a == 0) return signbit(b) ? pi(4*sign) : exact(a);
  if (b == 0) return pi(2*sign);
  if (isinf(a)) return pi(!isinf(b) ? 2*sign : b < 0 ? 3*sign : sign);
  if (isinf(b)) return b < 0 ? pi(4*sign) : exact(copysign(0,a));
  return compute;
#undef exact
#undef pi
}

/* Both oracles: the error of out in ULPs of the reference, or -1 where the reference overflows or
   out is not finite, and only the correctly rounded value will do. */
static long double screen_error(double a, double b, double out, struct special s) {
  long double ref;
  if (s.kind == PI_QUARTERS) ref = s.value*(3.14159265358979323846264338327950288L/4);
  else switch (f->id) {
  case SIN: ref = sinl(a); break;
  case COS: ref = cosl(a); break;
  case TAN: ref = tanl(a); break;
  case LOG10: ref = log10l(a); break;
  case ATAN: ref = atanl(a); break;
  case ATAN2: ref = atan2l(a,b); break;
  case SINH: ref = sinhl(a); break;
  case COSH: ref = coshl(a); break;
  case ACOS: ref = acosl(a); break;
  case ASIN: ref = asinl(a); break;
  case CBRT: ref = cbrtl(a); break;
  case ERF: ref = erfl(a); break;
  case ERFC: ref = erfcl(a); break;
  case EXP2: ref = exp2l(a); break;
  case EXP10: ref = powl(10,a); break;
  case EXPM1: ref = expm1l(a); break;
  case LOG1P: ref = log1pl(a); break;
  case LOG2: ref = log2l(a); break;
  case HYPOT: ref = hypotl(a,b); break;
  default: ref = tanhl(a); break;
  }
  double rounded = f->single ? (double)(float)ref : (double)ref;
  if (isnan(ref)) return -1;
  if (isinf(rounded) || isinf(out) || ref == 0) return bits_of(out) == bits_of(rounded) ? 0 : -1;
  int e = ilogbl(fabsl(ref)), emin = f->single ? -126 : -1022;
  return fabsl((long double)out-ref)/ldexpl(1.0L,(e < emin ? emin : e)-(f->single ? 23 : 52));
}

#ifdef VMATH_MPFR
static long double exact_error(double a, double b, double out, struct special s) {
  static __thread mpfr_t x, y, r;
  static __thread int ready;
  if (!ready) { mpfr_inits2(256,x,y,r,(mpfr_ptr)0); ready = 1; }
  mpfr_set_d(x,a,MPFR_RNDN); mpfr_set_d(y,b,MPFR_RNDN);
  if (s.kind == PI_QUARTERS) { mpfr_const_pi(r,MPFR_RNDN); mpfr_mul_d(r,r,s.value/4,MPFR_RNDN); }
  else switch (f->id) {
  case SIN: mpfr_sin(r,x,MPFR_RNDN); break;
  case COS: mpfr_cos(r,x,MPFR_RNDN); break;
  case TAN: mpfr_tan(r,x,MPFR_RNDN); break;
  case LOG10: mpfr_log10(r,x,MPFR_RNDN); break;
  case ATAN: mpfr_atan(r,x,MPFR_RNDN); break;
  case ATAN2: mpfr_atan2(r,x,y,MPFR_RNDN); break;
  case SINH: mpfr_sinh(r,x,MPFR_RNDN); break;
  case COSH: mpfr_cosh(r,x,MPFR_RNDN); break;
  case ACOS: mpfr_acos(r,x,MPFR_RNDN); break;
  case ASIN: mpfr_asin(r,x,MPFR_RNDN); break;
  case CBRT: mpfr_cbrt(r,x,MPFR_RNDN); break;
  case ERF: mpfr_erf(r,x,MPFR_RNDN); break;
  case ERFC: mpfr_erfc(r,x,MPFR_RNDN); break;
  case EXP2: mpfr_exp2(r,x,MPFR_RNDN); break;
  case EXP10: mpfr_exp10(r,x,MPFR_RNDN); break;
  case EXPM1: mpfr_expm1(r,x,MPFR_RNDN); break;
  case LOG1P: mpfr_log1p(r,x,MPFR_RNDN); break;
  case LOG2: mpfr_log2(r,x,MPFR_RNDN); break;
  case HYPOT: mpfr_hypot(r,x,y,MPFR_RNDN); break;
  default: mpfr_tanh(r,x,MPFR_RNDN); break;
  }
  double rounded = f->single ? (double)mpfr_get_flt(r,MPFR_RNDN) : mpfr_get_d(r,MPFR_RNDN);
  if (mpfr_nan_p(r)) return -1;
  if (isinf(rounded) || isinf(out) || mpfr_zero_p(r)) return bits_of(out) == bits_of(rounded) ? 0 : -1;
  long e = mpfr_get_exp(r)-1, emin = f->single ? -126 : -1022;
  mpfr_sub_d(r,r,out,MPFR_RNDN); mpfr_abs(r,r,MPFR_RNDN);
  mpfr_div_2si(r,r,(e < emin ? emin : e)-(f->single ? 23 : 52),MPFR_RNDN);
  return mpfr_get_ld(r,MPFR_RNDN);
}
#endif

static long double lane_error(uint64_t x, uint64_t y, uint64_t out) {
  double a = value(x), b = value(y), o = value(out);
  struct special s = annex_f(a,b);
  if (s.kind == NOT_A_NUMBER) return isnan(o) ? 0 : -1;
  if (s.kind == EXACT) return out == bits_of(s.value) ? 0 : -1;
#ifdef VMATH_MPFR
  if (!screen) return exact_error(a,b,o,s);
#endif
  return screen_error(a,b,o,s);
}

static void record(struct stats *s, uint64_t x, uint64_t y, uint64_t out, int tag) {
  long double e = lane_error(x,y,out);
  s->inputs++;
  if (e < 0 || e > dump || (screen && tag)) {
    if (__atomic_fetch_add(&dumped,1,__ATOMIC_RELAXED) < max_dump)
      printf("check 0x%016llx 0x%016llx 0x%016llx %.6Lf%s\n",(unsigned long long)x,(unsigned long long)y,
             (unsigned long long)out,e < 0 ? -1.0L : e,tag == GRID ? " grid" : tag == SAMPLE ? " sample" : "");
  }
  if (e < 0) { s->special_errors++; s->hist[5]++; e = 1e9L; }
  else s->hist[e <= 0.5L ? 0 : e <= 1 ? 1 : e <= 2 ? 2 : e <= 4 ? 3 : 4]++;
  if (e > s->max_ulp) { s->max_ulp = e; s->worst_x = x; s->worst_y = y; s->worst_out = out; }
}

static void call(const uint64_t *x, const uint64_t *y, int masked, unsigned mask, uint64_t *out) {
  if (f->single) {
    union { vf v; uint32_t w[16]; } a, b, r;
    for (int l = 0; l < 16; ++l) { a.w[l] = (uint32_t)x[l]; b.w[l] = (uint32_t)y[l]; }
    if (f->f2) r.v = masked ? f->f2m(a.v,b.v,mask) : f->f2(a.v,b.v);
    else r.v = masked ? f->f1m(a.v,mask) : f->f1(a.v);
    for (int l = 0; l < 16; ++l) out[l] = r.w[l];
  } else {
    union { vd v; uint64_t w[8]; } a, b, r;
    for (int l = 0; l < 8; ++l) { a.w[l] = x[l]; b.w[l] = y[l]; }
    if (f->d2) r.v = masked ? f->d2m(a.v,b.v,mask) : f->d2(a.v,b.v);
    else r.v = masked ? f->d1m(a.v,mask) : f->d1(a.v);
    for (int l = 0; l < 8; ++l) out[l] = r.w[l];
  }
}

static uint64_t next(uint64_t *s) { *s ^= *s << 13; *s ^= *s >> 7; *s ^= *s << 17; return *s; }
static uint64_t seed(uint64_t b) { return 0x9e3779b97f4a7c15ULL ^ (b+1)*0xbf58476d1ce4e5b9ULL; }
static double unit(uint64_t r) { return (double)(r >> 11)*0x1p-53; }

static uint64_t dense_input(uint64_t *rng) {
  uint64_t r = next(rng);
  double u = unit(next(rng)), v;
  if (f->id != LOG10 && f->id != LOG2 && f->id != LOG1P) {
    v = r & 2 ? u*f->range : ldexp(u*f->range,-(int)((r >> 8) % 40));
    if (r & 1) v = -v;
  } else if ((r & 3) == 0) {
    v = f->id == LOG1P ? ldexp(u,-(int)(r >> 8 & 63)) - 1 : 1 + (u-0.5)*ldexp(1.0,-(int)(r >> 8 & 31));
  } else {
    v = ldexp(1 + u,(int)((r >> 8) % (f->single ? 277 : 2098)) - (f->single ? 149 : 1074));
    if (f->id == LOG1P && (r & 4) && v < 1) v = -v;
  }
  return bits_of(v);
}

static void pair_input(uint64_t *rng, uint64_t *a, uint64_t *b) {
  uint64_t r = next(rng);
  if ((r & 3) == 0) {
    *a = next(rng); *b = next(rng);
    if (f->single) { *a = (uint32_t)*a; *b = (uint32_t)*b; }
    return;
  }
  int span = f->id != HYPOT ? 40 : f->single ? 150 : 1075;
  int e = (int)((r >> 8) % (2*span)) - span;
  int gap = (r & 3) == 1 ? (int)((r >> 24) % (2*span)) - span - e : (int)((r >> 24) % 25) - 12;
  double x = ldexp(1 + unit(next(rng)),e), y = ldexp(1 + unit(next(rng)),e + gap);
  *a = bits_of(r & 4 ? -y : y); *b = bits_of(r & 8 ? -x : x);
}

static void block(struct stats *s, uint64_t *rng, const uint64_t *x, const uint64_t *y, int tag) {
  uint64_t out[16], masked[16], r = next(rng);
  if (!tag && (r >> 6 & 1023) == 0) tag = SAMPLE;
  call(x,y,0,0,out);
  if (negative) out[3] ^= 1;
  for (int l = 0; l < lanes; ++l) record(s,x[l],y[l],out[l],tag);
  if ((r & 63) == 0) {
    unsigned mask = (unsigned)next(rng);
    call(x,y,1,mask,masked);
    if (negative_mask && !(mask & 1)) masked[0] ^= 1;
    for (int l = 0; l < lanes; ++l) {
      uint64_t want = mask >> l & 1 ? out[l] : x[l];
      if (negative && l == 3 && (mask >> 3 & 1)) want ^= 1;
      if (masked[l] != want) s->mask_errors++;
    }
  }
}

/* atan2 and hypot: block b is random pairs. Others: block b < blocks is a sweep block and block blocks + b
   the matching dense block. */
static void run_block(struct stats *s, uint64_t b) {
  uint64_t rng = seed(b), x[16], y[16] = {0};
  for (int l = 0; l < lanes; ++l)
    if (pairs) pair_input(&rng,&x[l],&y[l]);
    else if (b < blocks) x[l] = b*block_stride*(uint64_t)lanes + (uint64_t)l;
    else x[l] = dense_input(&rng);
  block(s,&rng,x,y,0);
}

static void *worker(void *arg) {
  int w = (int)(intptr_t)arg;
  uint64_t total = pairs ? blocks : 2*blocks;
  extended_precision();
  for (uint64_t b = (uint64_t)w; b < total; b += (uint64_t)workers) run_block(&totals[w],b);
  return NULL;
}

static void specials(struct stats *s) {
  static const double v[] = {0.0,-0.0,1.0,-1.0,2.0,-2.0,0.5,-0.5,3.0,-3.0,10.0,100.0,1e-5,1e10,1e22,
                             INFINITY,-INFINITY,NAN,-NAN,DBL_MIN,-DBL_MIN,DBL_MAX,-DBL_MAX,
                             0x1p-1074,-0x1p-1074,0x1.fffffffffffffp-1023,FLT_MIN,FLT_MAX,-FLT_MAX,
                             0x1p-149,0x1.fffffcp-127,0x1.0000000000001p0,0x1.fffffffffffffp-1,
                             0x1.000002p0,0x1.fffffep-1,0x1p-27,0x1p-28,0x1p-13,
                             0x1.921fb54442d18p-1,0x1.921fb54442d18p0,-0x1.921fb54442d18p0,
                             0x1.921fb54442d18p1,0x1.2d97c7f3321d2p1,0x1.921fb54442d18p2,
                             0x1.921fb6p0,0x1.921fb6p1,0x1p63,0x1p64,-0x1p120,0x1p1023,
                             9.0,19.0,20.0,-22.0,88.72283,89.41598629223294,89.5,
                             710.4758600739439,-710.4758600739439,710.5,711.0,
                             0.25,-0.25,8.0,27.0,-27.0,64.0,5.9921875,-6.0,27.2421875,27.25,28.0,10.0625,
                             127.5,128.0,-149.5,-150.0,38.53184,-45.0,1023.5,1024.0,-1074.5,-1075.0,
                             308.25,308.2547155599168,-323.5,-324.0,709.782712893384,-745.2,-37.5,
                             1e300,1e-300,0x1p-537,0x1p-538,0x1.6a09e667f3bcdp+1023,0x1.6a09e6p+127,
                             -0x1.fffffffffffffp-1,-0x1.fffffep-1,-0x1.0000000000001p0};
  enum { N = sizeof v/sizeof *v };
  uint64_t rng = 1, x[16], y[16] = {0};
  int n = 0;
  for (int i = 0; i < N; ++i)
    for (int j = 0; j < (pairs ? N : 1); ++j) {
      x[n] = bits_of(v[i]);
      if (pairs) y[n] = bits_of(v[j]);
      if (++n == lanes) { block(s,&rng,x,y,GRID); n = 0; }
    }
  if (n) { for (; n < lanes; ++n) { x[n] = x[0]; y[n] = y[0]; } block(s,&rng,x,y,GRID); }
}

#ifdef VMATH_MPFR
/* The card's "check" lines on standard input, each recomputed exactly. screen_error is the largest
   difference between a screened and an exact error; the grid does not count, as every one of its
   lanes is rechecked. */
static int recheck(void) {
  char line[256], tag[16];
  unsigned long long x, y, out, checked = 0, special_errors = 0, worst[3] = {0};
  long double screened, max_ulp = 0, screen_error = 0;
  while (fgets(line,sizeof line,stdin)) {
    tag[0] = 0;
    if (sscanf(line,"check %llx %llx %llx %Lf %15s",&x,&y,&out,&screened,tag) < 4) continue;
    long double e = lane_error(x,y,out);
    checked++;
    if (e < 0) { special_errors++; continue; }
    if (screened >= 0 && strcmp(tag,"grid") && fabsl(screened-e) > screen_error) screen_error = fabsl(screened-e);
    if (e > max_ulp) { max_ulp = e; worst[0] = x; worst[1] = y; worst[2] = out; }
  }
  int pass = max_ulp <= limit && !special_errors;
  printf("qualify_v1 function=%s mode=recheck checked=%llu max_ulp=%.6Lf worst_x=0x%016llx worst_y=0x%016llx "
         "worst_out=0x%016llx special_errors=%llu screen_error=%.6Lf result=%s\n",f->name,checked,max_ulp,
         worst[0],worst[1],worst[2],special_errors,screen_error,pass ? "PASS" : "FAIL");
  return !pass;
}
#endif

int main(int argc, char **argv) {
  int rechecking = 0;
  for (unsigned i = 0; argc > 1 && i < sizeof functions/sizeof *functions; ++i)
    if (!strcmp(argv[1],functions[i].name)) f = &functions[i];
  if (!f) { fprintf(stderr,"usage: qualify_v1 FUNCTION [--negative] [--negative-mask] [--blocks N] [--dump ULP] [--max-dump N] [--screen] [--recheck]\n"); return 2; }
  for (int i = 2; i < argc; ++i) {
    if (!strcmp(argv[i],"--negative")) negative = 1;
    else if (!strcmp(argv[i],"--negative-mask")) negative_mask = 1;
    else if (!strcmp(argv[i],"--blocks") && i+1 < argc) blocks = strtoull(argv[++i],NULL,0);
    else if (!strcmp(argv[i],"--dump") && i+1 < argc) dump = strtold(argv[++i],NULL);
    else if (!strcmp(argv[i],"--max-dump") && i+1 < argc) max_dump = strtoull(argv[++i],NULL,0);
#ifdef VMATH_MPFR
    else if (!strcmp(argv[i],"--screen")) screen = 1;
    else if (!strcmp(argv[i],"--recheck")) rechecking = 1;
#else
    else if (!strcmp(argv[i],"--screen")) ;
#endif
    else { fprintf(stderr,"unknown argument %s\n",argv[i]); return 2; }
  }
  lanes = f->single ? 16 : 8;
  pairs = f->f2 || f->d2;
  if (f->limit != 0) limit = f->limit;
  /* The exact oracle dumps only what fails, whatever --dump says. */
  if (!screen) dump = limit;
  else if (dump < 0) dump = 0.5L;
  uint64_t space = f->single ? 1ULL << 28 : 1ULL << 61; /* blocks of consecutive bit patterns */
  if (!blocks || blocks > space) { fprintf(stderr,"blocks must be 1 to %llu\n",(unsigned long long)space); return 2; }
  block_stride = space/blocks;
  extended_precision();
#ifdef VMATH_MPFR
  if (rechecking) return recheck();
#endif
  (void)rechecking;
  struct stats all = {0};
  specials(&all);
  cpu_set_t set;
  if (sched_getaffinity(0,sizeof set,&set)) { perror("sched_getaffinity"); return 2; }
  workers = CPU_COUNT(&set);
  if (workers > 256) workers = 256;
#ifdef VMATH_MPFR
  if (!mpfr_buildopt_tls_p()) workers = 1;
#endif
  pthread_attr_t attr;
  pthread_t threads[256];
  if (pthread_attr_init(&attr) || pthread_attr_setstacksize(&attr,1024*1024)) return 2;
  for (int w = 0; w < workers; ++w)
    if (pthread_create(&threads[w],&attr,worker,(void *)(intptr_t)w)) { perror("pthread_create"); return 2; }
  for (int w = 0; w < workers; ++w) pthread_join(threads[w],NULL);
  for (int w = 0; w < workers; ++w) {
    struct stats *s = &totals[w];
    all.inputs += s->inputs; all.special_errors += s->special_errors; all.mask_errors += s->mask_errors;
    for (int h = 0; h < 6; ++h) all.hist[h] += s->hist[h];
    /* Ties go to the smaller input so that the worst case does not depend on the workers. */
    if (s->max_ulp > all.max_ulp || (s->max_ulp == all.max_ulp && s->max_ulp > 0 &&
        (s->worst_x < all.worst_x || (s->worst_x == all.worst_x && s->worst_y < all.worst_y)))) {
      all.max_ulp = s->max_ulp; all.worst_x = s->worst_x; all.worst_y = s->worst_y; all.worst_out = s->worst_out;
    }
  }
  int pass = all.max_ulp <= limit && !all.special_errors && !all.mask_errors && dumped <= max_dump;
  printf("qualify_v1 function=%s mode=%s negative=%d negative_mask=%d blocks=%llu workers=%d inputs=%llu "
         "max_ulp=%.6Lf worst_x=0x%016llx worst_y=0x%016llx worst_out=0x%016llx ulp_le_0.5=%llu ulp_le_1=%llu "
         "ulp_le_2=%llu ulp_le_4=%llu ulp_gt_4=%llu special_errors=%llu mask_errors=%llu dump=%.3Lf "
         "dumped=%llu result=%s\n",
         f->name,screen ? "screen" : "exact",negative,negative_mask,(unsigned long long)blocks,workers,
         (unsigned long long)all.inputs,all.max_ulp,(unsigned long long)all.worst_x,
         (unsigned long long)all.worst_y,(unsigned long long)all.worst_out,
         (unsigned long long)all.hist[0],(unsigned long long)all.hist[1],(unsigned long long)all.hist[2],
         (unsigned long long)all.hist[3],(unsigned long long)all.hist[4],
         (unsigned long long)all.special_errors,(unsigned long long)all.mask_errors,dump,
         (unsigned long long)dumped,pass ? "PASS" : "FAIL");
  return pass ? 0 : 1;
}
