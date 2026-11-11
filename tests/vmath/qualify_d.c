/* Qualification of libknc_vmath's 8-lane exp, log and pow cores (S10-02, ADR-0014 point 4), the
   double-precision companion of tests/acceptance/vecmath_qualify/qualify.c. The x87 long double
   expl/logl/powl (64-bit significand) only screen: powl's own error reaches about 0.4 double ULP
   where |y log x| is large. Every lane whose screened error exceeds --dump (default 0.5) prints a
   "check" line, and tests/vmath/card_qualify.py recomputes those lanes exactly on the host; the
   summary line's max_ulp and histogram are the screen's. The inputs depend
   only on the block number, so any worker count, and a host build, sees the same set:
   - exp, log: every block-stride-th block of 8 consecutive bit patterns of the whole 2^64 space
     ("sweep" blocks), and as many blocks of x uniform in the function's interesting range
     ("dense" blocks: exp [-746, 710], log [2^-1074, 2^1024) by exponent);
   - pow: random pairs (a quarter raw bit patterns, the rest finite x in [2^-40, 2^40) of either
     sign and y in [-512, 512), some integral) plus a grid of special pairs.
   One block in 64 also runs masked with random merge bits: inactive lanes must keep the merge
   bits, active lanes must equal the all-active result. Round to nearest only; errno and flags are
   not checked. */
#define _GNU_SOURCE
#include <float.h>
#include <math.h>
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "knc_vmath.h"

enum { EXP, LOG, POW };
static int function, negative, negative_mask, workers;
static uint64_t blocks = 1ULL << 22, block_stride; /* 0: spread the sweep over all 2^64 */
static long double dump = 0.5L;
static uint64_t max_dump = 2000000, dumped;

struct stats {
  uint64_t inputs, status_errors, special_errors, mask_errors, hist[6];
  long double max_ulp;
  uint64_t worst_x, worst_y, worst_out;
} __attribute__((aligned(64)));
static struct stats totals[256];

static double as_double(uint64_t u) { double d; memcpy(&d,&u,8); return d; }
static uint64_t as_bits(double d) { uint64_t u; memcpy(&u,&d,8); return u; }

/* The oracle needs the x87's 64-bit significand. Linux starts with it; Windows (the host build
   under Cygwin) starts its threads with 53 bits, which would round expl to double. Set precision control to
   64 bits in every thread. */
static void extended_precision(void) {
  unsigned short cw;
  __asm__ volatile ("fnstcw %0" : "=m" (cw));
  cw |= 0x300;
  __asm__ volatile ("fldcw %0" : : "m" (cw));
}

static long double reference(double x, double y) {
  if (function == EXP) return expl(x);
  if (function == LOG) return logl(x);
  return powl(x,y);
}

/* Error of out against ref in double ULPs of ref; -1 for a failure on the non-finite or exact-zero
   paths, where only the correctly rounded value (sign included) is acceptable. */
static long double ulp_error(double out, long double ref) {
  double rounded = (double)ref;
  if (isnan(ref)) return isnan(out) ? 0 : -1;
  if (isinf(rounded) || isinf(out) || ref == 0) return as_bits(out) == as_bits(rounded) ? 0 : -1;
  long double a = fabsl(ref), ulp;
  if (a < DBL_MIN) ulp = 0x1p-1074L;
  else ulp = ldexpl(1.0L, ilogbl(a)-52);
  return fabsl((long double)out-ref)/ulp;
}

static void record(struct stats *s, uint64_t x, uint64_t y, uint64_t out) {
  long double ref = reference(as_double(x),as_double(y)), e = ulp_error(as_double(out),ref);
  s->inputs++;
  if (e < 0 || e > dump) {
    if (__atomic_fetch_add(&dumped,1,__ATOMIC_RELAXED) < max_dump)
      printf("check 0x%016llx 0x%016llx 0x%016llx %.6Lf\n",(unsigned long long)x,(unsigned long long)y,
             (unsigned long long)out,e < 0 ? -1.0L : e);
  }
  if (e < 0) { s->special_errors++; s->hist[5]++; e = 1e9L; }
  else s->hist[e <= 0.5L ? 0 : e <= 1 ? 1 : e <= 2 ? 2 : e <= 4 ? 3 : 4]++;
  if (e > s->max_ulp) { s->max_ulp = e; s->worst_x = x; s->worst_y = y; s->worst_out = out; }
}

static int call(const uint64_t *x, const uint64_t *y, unsigned active, const uint64_t *merge,
                uint64_t *out) {
  if (function == EXP) return __knc_vmath_core_exp_8(x,active,merge,out);
  if (function == LOG) return __knc_vmath_core_log_8(x,active,merge,out);
  return __knc_vmath_core_pow_8(x,y,active,merge,out);
}

static uint64_t next(uint64_t *s) { *s ^= *s << 13; *s ^= *s >> 7; *s ^= *s << 17; return *s; }
static uint64_t seed(uint64_t b) { return 0x9e3779b97f4a7c15ULL ^ (b+1)*0xbf58476d1ce4e5b9ULL; }
static double unit(uint64_t r) { return (double)(r >> 11)*0x1p-53; }

static void dense_input(uint64_t *rng, uint64_t *x) {
  uint64_t r = next(rng);
  if (function == EXP) { *x = as_bits(-746.0 + unit(r)*1456.0); return; }
  /* log: positive normals and subnormals, every exponent equally likely. */
  int e = (int)(r % 2098) - 1074;
  double m = 1.0 + unit(next(rng));
  *x = as_bits(ldexp(m, e));
}

static void pow_input(uint64_t *rng, uint64_t *x, uint64_t *y) {
  uint64_t r = next(rng);
  if ((r & 3) == 0) { *x = r >> 2 | (r & 4) << 61; *y = next(rng); return; }
  double fx = ldexp(1.0 + unit(next(rng)), (int)((r >> 32) % 80) - 40);
  if (r & 16) fx = -fx;
  double fy = (unit(next(rng)) - 0.5)*1024.0;
  if ((r & 0x60) == 0x20) fy = rint(fy); /* integer y, for negative x */
  *x = as_bits(fx); *y = as_bits(fy);
}

static void block(struct stats *s, uint64_t *rng, const uint64_t *x, const uint64_t *y) {
  uint64_t out[8], merge[8], masked[8];
  if (call(x,y,0xff,x,out)) s->status_errors++;
  if (negative) out[3] ^= 1;
  for (int l = 0; l < 8; ++l) record(s,x[l],function == POW ? y[l] : 0,out[l]);
  if ((next(rng) & 63) == 0) {
    unsigned active = (unsigned)next(rng) & 0xff;
    for (int l = 0; l < 8; ++l) merge[l] = next(rng);
    if (call(x,y,active,merge,masked)) s->status_errors++;
    if (negative_mask && !(active & 1)) masked[0] ^= 1;
    for (int l = 0; l < 8; ++l) {
      uint64_t want = active >> l & 1 ? out[l] : merge[l];
      if (negative && l == 3 && (active >> 3 & 1)) want ^= 1;
      if (masked[l] != want) s->mask_errors++;
    }
  }
}

/* Block b < blocks is a sweep (exp, log) or random (pow) block; for exp and log, block
   blocks + b is the matching dense block. */
static void run_block(struct stats *s, uint64_t b) {
  uint64_t rng = seed(b), x[8], y[8] = {0};
  if (function == POW) for (int l = 0; l < 8; ++l) pow_input(&rng,&x[l],&y[l]);
  else if (b < blocks) for (int l = 0; l < 8; ++l) x[l] = b*block_stride*8 + (uint64_t)l;
  else for (int l = 0; l < 8; ++l) dense_input(&rng,&x[l]);
  block(s,&rng,x,y);
}

static void *worker(void *arg) {
  int w = (int)(intptr_t)arg;
  uint64_t total = function == POW ? blocks : 2*blocks;
  extended_precision();
  for (uint64_t b = (uint64_t)w; b < total; b += (uint64_t)workers) run_block(&totals[w],b);
  return NULL;
}

static void specials(struct stats *s) {
  static const double v[] = {0.0,-0.0,1.0,-1.0,2.0,-2.0,0.5,-0.5,3.0,-3.0,INFINITY,-INFINITY,NAN,
                             -NAN,DBL_MIN,-DBL_MIN,DBL_MAX,-DBL_MAX,0x1p-1074,-0x1p-1074,
                             0x1.fffffffffffffp-1023,0x1.0000000000001p0,0x1.fffffffffffffp-1,
                             709.782712893384,709.7827128933841,-708.3964185322641,
                             -745.1332191019411,-745.1332191019412,1023.0,1024.0,-1074.0,
                             -1075.0,1e300,-1e300,0x1p53,0x1p53+2,-0x1p53-2};
  enum { N = sizeof v/sizeof *v };
  uint64_t rng = 1, x[8], y[8] = {0};
  int n = 0;
  if (function != POW) {
    for (int i = 0; i < N; ++i) { x[n] = as_bits(v[i]); if (++n == 8) { block(s,&rng,x,y); n = 0; } }
  } else {
    for (int i = 0; i < N; ++i)
      for (int j = 0; j < N; ++j) {
        x[n] = as_bits(v[i]); y[n] = as_bits(v[j]);
        if (++n == 8) { block(s,&rng,x,y); n = 0; }
      }
  }
  if (n) { for (; n < 8; ++n) { x[n] = x[0]; y[n] = y[0]; } block(s,&rng,x,y); }
}

int main(int argc, char **argv) {
  const char *name = argc > 1 ? argv[1] : "";
  if (!strcmp(name,"exp")) function = EXP;
  else if (!strcmp(name,"log")) function = LOG;
  else if (!strcmp(name,"pow")) function = POW;
  else { fprintf(stderr,"usage: qualify_d exp|log|pow [--negative] [--negative-mask] [--blocks N] [--block-stride N] [--dump ULP] [--max-dump N]\n"); return 2; }
  for (int i = 2; i < argc; ++i) {
    if (!strcmp(argv[i],"--negative")) negative = 1;
    else if (!strcmp(argv[i],"--negative-mask")) negative_mask = 1;
    else if (!strcmp(argv[i],"--blocks") && i+1 < argc) blocks = strtoull(argv[++i],NULL,0);
    else if (!strcmp(argv[i],"--dump") && i+1 < argc) dump = strtold(argv[++i],NULL);
    else if (!strcmp(argv[i],"--max-dump") && i+1 < argc) max_dump = strtoull(argv[++i],NULL,0);
    else if (!strcmp(argv[i],"--block-stride") && i+1 < argc) block_stride = strtoull(argv[++i],NULL,0);
    else { fprintf(stderr,"unknown argument %s\n",argv[i]); return 2; }
  }
  extended_precision();
  if (!blocks) { fprintf(stderr,"blocks must be positive\n"); return 2; }
  if (!block_stride) block_stride = (1ULL << 61)/blocks;
  if (block_stride > (1ULL << 61)/blocks) {
    fprintf(stderr,"blocks*stride*8 must be within 2^64\n"); return 2;
  }
  cpu_set_t set;
  if (sched_getaffinity(0,sizeof set,&set)) { perror("sched_getaffinity"); return 2; }
  workers = CPU_COUNT(&set);
  if (workers > 256) workers = 256;
  pthread_attr_t attr;
  pthread_t threads[256];
  if (pthread_attr_init(&attr) || pthread_attr_setstacksize(&attr,256*1024)) return 2;
  for (int w = 0; w < workers; ++w)
    if (pthread_create(&threads[w],&attr,worker,(void *)(intptr_t)w)) { perror("pthread_create"); return 2; }
  for (int w = 0; w < workers; ++w) pthread_join(threads[w],NULL);
  struct stats all = {0};
  specials(&all);
  for (int w = 0; w < workers; ++w) {
    struct stats *s = &totals[w];
    all.inputs += s->inputs; all.status_errors += s->status_errors;
    all.special_errors += s->special_errors; all.mask_errors += s->mask_errors;
    for (int h = 0; h < 6; ++h) all.hist[h] += s->hist[h];
    /* Ties go to the smaller input so that the worst case does not depend on the workers. */
    if (s->max_ulp > all.max_ulp || (s->max_ulp == all.max_ulp && s->max_ulp > 0 &&
        (s->worst_x < all.worst_x || (s->worst_x == all.worst_x && s->worst_y < all.worst_y)))) {
      all.max_ulp = s->max_ulp; all.worst_x = s->worst_x; all.worst_y = s->worst_y; all.worst_out = s->worst_out;
    }
  }
  int pass = all.max_ulp <= 1.0L && !all.status_errors && !all.special_errors && !all.mask_errors &&
             dumped <= max_dump;
  printf("qualify_d function=%s negative=%d negative_mask=%d blocks=%llu block_stride=%llu workers=%d inputs=%llu "
         "max_ulp=%.6Lf worst_x=0x%016llx worst_y=0x%016llx worst_out=0x%016llx ulp_le_0.5=%llu ulp_le_1=%llu "
         "ulp_le_2=%llu ulp_le_4=%llu ulp_gt_4=%llu special_errors=%llu status_errors=%llu mask_errors=%llu "
         "dump=%.3Lf dumped=%llu result=%s\n",
         name,negative,negative_mask,(unsigned long long)blocks,(unsigned long long)block_stride,workers,
         (unsigned long long)all.inputs,all.max_ulp,(unsigned long long)all.worst_x,
         (unsigned long long)all.worst_y,(unsigned long long)all.worst_out,
         (unsigned long long)all.hist[0],(unsigned long long)all.hist[1],(unsigned long long)all.hist[2],
         (unsigned long long)all.hist[3],(unsigned long long)all.hist[4],
         (unsigned long long)all.special_errors,(unsigned long long)all.status_errors,
         (unsigned long long)all.mask_errors,dump,(unsigned long long)dumped,pass ? "PASS" : "FAIL");
  return pass ? 0 : 1;
}
