/* S9-16 C14: VPU cost of subnormal operands.  IMCI keeps subnormals (gaps
   G6); this measures what packed single add, mul and FMA cost when 0, 1 or 16
   lanes of one operand are subnormal and every result is normal, plus a mul
   whose results stay subnormal.  Eight independent destinations per round,
   so the figure is issue cost, not latency.  Run with 1 or 4 threads on core
   0's siblings (--threads N); each row is the median over threads of each
   thread's median of 9 runs, in ticks per instruction per thread, with the
   slowest thread in brackets and the ratio to 0 subnormal lanes.  Prints the
   MXCSR so a DAZ or FZ setting is visible.  Standalone. */
#define _GNU_SOURCE
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { RUNS = 9, ITERS = 1 << 14, OPS = 4, LANES = 3 };

static float c14_a[16] __attribute__((aligned(64)));
static float c14_b[LANES][16] __attribute__((aligned(64)));
static float c14_one[16] __attribute__((aligned(64)));
static float c14_out[16] __attribute__((aligned(64)));
static int c14_threads = 1, c14_cpu[4];
static pthread_barrier_t c14_barrier;
static double c14_result[OPS][LANES][4];

static uint64_t ticks(void) {
    unsigned a, b, c, d, lo, hi;
    __asm__ volatile("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d) : "a"(0) : "memory");
    __asm__ volatile("rdtsc" : "=a"(lo), "=d"(hi) : : "memory");
    __asm__ volatile("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d) : "a"(0) : "memory");
    return ((uint64_t)hi << 32) | lo;
}

#define X8(i) i "%%zmm3\n\t" i "%%zmm4\n\t" i "%%zmm5\n\t" i "%%zmm6\n\t" \
              i "%%zmm7\n\t" i "%%zmm8\n\t" i "%%zmm9\n\t" i "%%zmm10\n\t"
#define C14_CLOBBERS "memory", "cc", "zmm0", "zmm1", "zmm2", "zmm3", "zmm4", "zmm5", \
                     "zmm6", "zmm7", "zmm8", "zmm9", "zmm10"
/* zmm0 = a, zmm1 = b (the subnormal lanes), destinations start at c. */
static void c14_run(int op, const float *a, const float *b) {
    long n = ITERS;
    const float *c = c14_one;
    float *out = c14_out;
#define C14_BODY(insn) \
    __asm__ volatile("vmovaps (%1), %%zmm0\n\tvmovaps (%2), %%zmm1\n\tvmovaps (%3), %%zmm2\n\t" \
                     X8("vmovaps %%zmm2, ") \
                     "1:\n\t" X8(insn) "dec %0\n\tjnz 1b\n\t" \
                     "vaddps %%zmm4, %%zmm3, %%zmm3\n\tvmovaps %%zmm3, (%4)" \
                     : "+r"(n) : "r"(a), "r"(b), "r"(c), "r"(out) : C14_CLOBBERS)
    if (op == 0) C14_BODY("vaddps %%zmm1, %%zmm0, ");
    else if (op == 2) C14_BODY("vfmadd231ps %%zmm1, %%zmm0, ");
    else C14_BODY("vmulps %%zmm1, %%zmm0, ");
#undef C14_BODY
}

static int c14_cmp(const void *x, const void *y) {
    double p = *(const double *)x, q = *(const double *)y;
    return p < q ? -1 : p > q;
}

static void *c14_worker(void *arg) {
    int id = (int)(intptr_t)arg;
    cpu_set_t set;
    CPU_ZERO(&set); CPU_SET(c14_cpu[id], &set);
    if (pthread_setaffinity_np(pthread_self(), sizeof(set), &set)) exit(2);
    /* mul.subout multiplies by 1, so its results stay subnormal. */
    for (int op = 0; op < OPS; ++op)
        for (int l = 0; l < LANES; ++l) {
            const float *a = op == 3 ? c14_one : c14_a;
            double t[RUNS];
            pthread_barrier_wait(&c14_barrier);
            c14_run(op, a, c14_b[l]);
            for (int r = 0; r < RUNS; ++r) {
                uint64_t t0 = ticks();
                c14_run(op, a, c14_b[l]);
                t[r] = (double)(ticks() - t0) / (8.0 * ITERS);
            }
            qsort(t, RUNS, sizeof(t[0]), c14_cmp);
            c14_result[op][l][id] = t[RUNS/2];
        }
    return NULL;
}

static float c14_bits(uint32_t u) {
    float f;
    memcpy(&f, &u, 4);
    return f;
}

int main(int argc, char **argv) {
    if (argc == 3 && !strcmp(argv[1], "--threads") && (!strcmp(argv[2], "1") || !strcmp(argv[2], "4")))
        c14_threads = argv[2][0] - '0';
    else if (argc != 1) {
        fprintf(stderr, "usage: c14.mic [--threads 1|4]\n");
        return 2;
    }
    /* Core 0's siblings, lowest CPU first. */
    FILE *f = fopen("/proc/cpuinfo", "r");
    char line[512];
    int cpu = -1, found = 0;
    if (!f) return 2;
    while (fgets(line, sizeof(line), f) && found < 4) {
        int core;
        if (sscanf(line, "processor : %d", &cpu) == 1) continue;
        if (sscanf(line, "core id : %d", &core) == 1 && core == 0 && cpu >= 0) c14_cpu[found++] = cpu;
    }
    fclose(f);
    if (found < c14_threads) {
        fprintf(stderr, "core 0 has %d siblings\n", found);
        return 2;
    }
    for (int i = 0; i < c14_threads; ++i) printf("pin %d %d\n", i, c14_cpu[i]);
    /* Normal b lanes 2^-100, subnormal 2^-140; a = 2^24 lifts every product
       above the normal range; c = 1. */
    for (int i = 0; i < 16; ++i) {
        c14_a[i] = c14_bits(0x4b800000u);
        c14_one[i] = 1.0f;
        for (int l = 0; l < LANES; ++l) {
            int sub = l == 2 || (l == 1 && i == 0);
            c14_b[l][i] = c14_bits(sub ? 0x00000400u : 0x0d800000u);
        }
    }
    /* DAZ is bit 6 and FZ bit 15 (ISA 327364-001, table 2.15). */
    uint32_t mxcsr;
    __asm__ volatile("stmxcsr %0" : "=m"(mxcsr));
    printf("c14 mxcsr=0x%08x daz=%u fz=%u\n", mxcsr, (mxcsr >> 6) & 1, (mxcsr >> 15) & 1);
    if (pthread_barrier_init(&c14_barrier, NULL, c14_threads)) return 2;
    pthread_t th[4];
    for (int i = 1; i < c14_threads; ++i)
        if (pthread_create(&th[i], NULL, c14_worker, (void *)(intptr_t)i)) return 2;
    c14_worker(0);
    for (int i = 1; i < c14_threads; ++i) pthread_join(th[i], NULL);
    static const char *const names[OPS] = {"add", "mul", "fma", "mul.subout"};
    static const int lanes[LANES] = {0, 1, 16};
    printf("c14 op subnormal_lanes threads ticks_per_insn (slowest) ratio_to_0\n");
    for (int op = 0; op < OPS; ++op) {
        double base = 0;
        for (int l = 0; l < LANES; ++l) {
            double v[4];
            memcpy(v, c14_result[op][l], sizeof(v));
            qsort(v, c14_threads, sizeof(v[0]), c14_cmp);
            double med = v[(c14_threads - 1)/2], slow = v[c14_threads - 1];
            if (!l) base = med;
            printf("c14 %s %d %d %.3f (%.3f) %.3f\n", names[op], lanes[l], c14_threads,
                   med, slow, med / base);
        }
    }
    return 0;
}
