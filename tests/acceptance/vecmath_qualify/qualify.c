/* Card qualification of the copied 16-lane expf, logf and powf cores (ADR-0011 point 4) as built
   by GCC-KNC. The oracle is the card's x87 long double expl/logl/powl (64-bit significand, far
   finer than a float ULP). expf and logf: all 2^32 inputs, or every stride-th block of 16.
   powf: a fixed random set plus a grid of special pairs. Masked calls: inactive lanes must keep the merge bits and active
   lanes must equal the all-active result. Round-to-nearest only; errno and flags are not checked. */
#define _GNU_SOURCE
#include <float.h>
#include <math.h>
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int phi_host_expf_e16(const uint32_t *, unsigned, const uint32_t *, uint32_t *);
int phi_host_logf_e16(const uint32_t *, unsigned, const uint32_t *, uint32_t *);
int phi_host_powf_e16(const uint32_t *, const uint32_t *, unsigned, const uint32_t *, uint32_t *);

enum { EXPF, LOGF, POWF };
static int function, negative, negative_mask, workers;
static uint64_t pow_count = 1ULL << 28, limit_blocks = UINT64_MAX, block_stride = 1;

struct stats {
  uint64_t inputs, status_errors, special_errors, mask_errors, hist[6];
  long double max_ulp;
  uint32_t worst_x, worst_y, worst_out;
} __attribute__((aligned(64)));
static struct stats totals[256];

static float as_float(uint32_t u) { float f; memcpy(&f,&u,4); return f; }
static uint32_t as_bits(float f) { uint32_t u; memcpy(&u,&f,4); return u; }

static long double reference(float x, float y) {
  if (function == EXPF) return expl(x);
  if (function == LOGF) return logl(x);
  return powl(x,y);
}

/* Error of out against ref in float ULPs of ref; -1 for an exact-match failure on the
   non-finite or overflow paths, where only the correctly rounded value is acceptable. */
static long double ulp_error(float out, long double ref) {
  float rounded = (float)ref;
  if (isnan(ref)) return isnan(out) ? 0 : -1;
  if (isinf(rounded) || isinf(out) || ref == 0) return as_bits(out) == as_bits(rounded) ? 0 : -1;
  long double a = fabsl(ref), ulp;
  if (a < FLT_MIN) ulp = 0x1p-149L;
  else ulp = ldexpl(1.0L, ilogbl(a)-23);
  return fabsl((long double)out-ref)/ulp;
}

static void record(struct stats *s, uint32_t x, uint32_t y, uint32_t out) {
  long double ref = reference(as_float(x),as_float(y)), e = ulp_error(as_float(out),ref);
  s->inputs++;
  if (e < 0) { s->special_errors++; s->hist[5]++; e = 1e9L; }
  else s->hist[e <= 0.5L ? 0 : e <= 1 ? 1 : e <= 2 ? 2 : e <= 4 ? 3 : 4]++;
  if (e > s->max_ulp) { s->max_ulp = e; s->worst_x = x; s->worst_y = y; s->worst_out = out; }
}

static int call(const uint32_t *x, const uint32_t *y, unsigned active, const uint32_t *merge, uint32_t *out) {
  if (function == EXPF) return phi_host_expf_e16(x,active,merge,out);
  if (function == LOGF) return phi_host_logf_e16(x,active,merge,out);
  return phi_host_powf_e16(x,y,active,merge,out);
}

static uint64_t next(uint64_t *s) { *s ^= *s << 13; *s ^= *s >> 7; *s ^= *s << 17; return *s; }

/* powf inputs: a quarter fully random bit patterns, the rest finite x in [2^-20, 2^20) of either
   sign and y in [-64, 64), where results are mostly finite and normal. */
static void pow_input(uint64_t *rng, uint32_t *x, uint32_t *y) {
  uint64_t r = next(rng);
  if ((r & 3) == 0) { *x = (uint32_t)(r >> 2); *y = (uint32_t)(next(rng) >> 7); return; }
  float fx = ldexpf(1.0f + (float)((r >> 8) & 0x7fffff)/0x800000, (int)((r >> 32) % 40) - 20);
  if (r & 16) fx = -fx;
  float fy = ((float)(int32_t)(next(rng) >> 32))/(float)(1U << 25);
  if ((r & 0x60) == 0x20) fy = rintf(fy); /* integer y for negative x */
  *x = as_bits(fx); *y = as_bits(fy);
}

static void block(struct stats *s, uint64_t *rng, const uint32_t *x, const uint32_t *y) {
  uint32_t out[16], merge[16], masked[16];
  if (call(x,y,0xffff,x,out)) s->status_errors++;
  if (negative) out[3] ^= 1;
  for (int l = 0; l < 16; ++l) record(s,x[l],function == POWF ? y[l] : 0,out[l]);
  /* One block in 64 also runs masked, with random merge bits. */
  if ((next(rng) & 63) == 0) {
    unsigned active = (unsigned)next(rng) & 0xffff;
    for (int l = 0; l < 16; ++l) merge[l] = (uint32_t)next(rng);
    if (call(x,y,active,merge,masked)) s->status_errors++;
    if (negative_mask && !(active & 1)) masked[0] ^= 1;
    for (int l = 0; l < 16; ++l) {
      uint32_t want = active >> l & 1 ? out[l] : merge[l];
      if (negative && l == 3 && (active >> 3 & 1)) want ^= 1;
      if (masked[l] != want) s->mask_errors++;
    }
  }
}

static void *worker(void *arg) {
  int w = (int)(intptr_t)arg;
  struct stats *s = &totals[w];
  uint64_t rng = 0x9e3779b97f4a7c15ULL ^ (uint64_t)(w+1)*0xbf58476d1ce4e5b9ULL;
  uint32_t x[16], y[16] = {0};
  if (function != POWF) {
    /* Blocks of 16 consecutive bit patterns, every stride-th block, interleaved across workers:
       stride 1 is exhaustive; larger strides sample every exponent evenly. */
    uint64_t done = 0;
    for (uint64_t b = (uint64_t)w*block_stride; b < (1ULL << 28) && done < limit_blocks;
         b += (uint64_t)workers*block_stride, ++done) {
      for (int l = 0; l < 16; ++l) x[l] = (uint32_t)(b*16+l);
      block(s,&rng,x,y);
    }
  } else {
    for (uint64_t b = (uint64_t)w; b < pow_count/16; b += workers) {
      for (int l = 0; l < 16; ++l) pow_input(&rng,&x[l],&y[l]);
      block(s,&rng,x,y);
    }
  }
  return NULL;
}

/* Special pairs for powf, every combination, run once on the main thread. */
static void pow_specials(struct stats *s) {
  static const float v[] = {0.0f,-0.0f,1.0f,-1.0f,2.0f,-2.0f,0.5f,-0.5f,3.0f,-3.0f,
                            INFINITY,-INFINITY,NAN,FLT_MIN,FLT_MAX,0x1p-149f,-0x1p-149f,
                            1.0000001f,0.99999994f,127.0f,-127.0f,128.0f,-150.0f,1e10f,-1e10f};
  enum { N = sizeof v/sizeof *v };
  uint64_t rng = 1;
  uint32_t x[16], y[16];
  int n = 0;
  for (int i = 0; i < N; ++i)
    for (int j = 0; j < N; ++j) {
      x[n] = as_bits(v[i]); y[n] = as_bits(v[j]);
      if (++n == 16) { block(s,&rng,x,y); n = 0; }
    }
  if (n) { for (; n < 16; ++n) { x[n] = x[0]; y[n] = y[0]; } block(s,&rng,x,y); }
}

int main(int argc, char **argv) {
  const char *name = argc > 1 ? argv[1] : "";
  if (!strcmp(name,"expf")) function = EXPF;
  else if (!strcmp(name,"logf")) function = LOGF;
  else if (!strcmp(name,"powf")) function = POWF;
  else { fprintf(stderr,"usage: qualify expf|logf|powf [--negative] [--negative-mask] [--pow-count N] [--limit-blocks N] [--block-stride N]\n"); return 2; }
  for (int i = 2; i < argc; ++i) {
    if (!strcmp(argv[i],"--negative")) negative = 1;
    else if (!strcmp(argv[i],"--negative-mask")) negative_mask = 1;
    else if (!strcmp(argv[i],"--pow-count") && i+1 < argc) pow_count = strtoull(argv[++i],NULL,0);
    else if (!strcmp(argv[i],"--limit-blocks") && i+1 < argc) limit_blocks = strtoull(argv[++i],NULL,0);
    else if (!strcmp(argv[i],"--block-stride") && i+1 < argc) block_stride = strtoull(argv[++i],NULL,0);
    else { fprintf(stderr,"unknown argument %s\n",argv[i]); return 2; }
  }
  if (!block_stride) { fprintf(stderr,"block stride must be positive\n"); return 2; }
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
  if (function == POWF) pow_specials(&all);
  for (int w = 0; w < workers; ++w) {
    struct stats *s = &totals[w];
    all.inputs += s->inputs; all.status_errors += s->status_errors;
    all.special_errors += s->special_errors; all.mask_errors += s->mask_errors;
    for (int h = 0; h < 6; ++h) all.hist[h] += s->hist[h];
    if (s->max_ulp > all.max_ulp) {
      all.max_ulp = s->max_ulp; all.worst_x = s->worst_x; all.worst_y = s->worst_y; all.worst_out = s->worst_out;
    }
  }
  int pass = all.max_ulp <= 1.0L && !all.status_errors && !all.special_errors && !all.mask_errors;
  printf("qualify function=%s negative=%d negative_mask=%d block_stride=%llu workers=%d inputs=%llu max_ulp=%.6Lf worst_x=0x%08x "
         "worst_y=0x%08x worst_out=0x%08x ulp_le_0.5=%llu ulp_le_1=%llu ulp_le_2=%llu ulp_le_4=%llu "
         "ulp_gt_4=%llu special_errors=%llu status_errors=%llu mask_errors=%llu result=%s\n",
         name,negative,negative_mask,(unsigned long long)block_stride,workers,(unsigned long long)all.inputs,all.max_ulp,all.worst_x,all.worst_y,
         all.worst_out,(unsigned long long)all.hist[0],(unsigned long long)all.hist[1],
         (unsigned long long)all.hist[2],(unsigned long long)all.hist[3],
         (unsigned long long)all.hist[4],(unsigned long long)all.special_errors,
         (unsigned long long)all.status_errors,(unsigned long long)all.mask_errors,
         pass ? "PASS" : "FAIL");
  return pass ? 0 : 1;
}
