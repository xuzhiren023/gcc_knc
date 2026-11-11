/* S9-20: instruction scheduling on the in-order KNC core.
   Built by tools/s9_20_sched.py once per scheduling variant with -DV=<name> (the two scalar
   kernels below; the M2 kernels come from tests/acceptance/m2_kernels/kernels.c with
   -DBUILD=<name>), and once with -DDRIVER for main().  Every variant must give the baseline's
   output bit for bit: scheduling reorders, it never changes arithmetic.  The FP data are quarter
   integers, so x87 values are exact whether a temporary is spilled to memory or kept in 80 bits. */
#define CAT2(a, b) a##_##b
#define CAT(a, b) CAT2(a, b)

#ifndef DRIVER
/* Dependent integer chain fed by loads: h is one serial multiply chain through every element;
   g is a second, independent chain.  Four elements per trip in source order, so the scheduler
   has loads and the g chain to move under the h multiplies. */
void CAT(ichain, V)(void *restrict yy, const void *restrict xx, const void *restrict pp,
                    unsigned long n)
{
    long *restrict y = yy;
    const long *restrict a = xx, *restrict b = pp;
    unsigned long h = 1, g = 0;
    for (unsigned long i = 0; i + 4 <= n; i += 4) {
        h = (h ^ (unsigned long)a[i]) * 0x9e3779b97f4a7c15ul;
        g += (unsigned long)(b[i] * a[i + 1]);
        h = (h ^ (unsigned long)a[i + 1]) * 0x9e3779b97f4a7c15ul;
        g += (unsigned long)(b[i + 1] * a[i + 2]);
        h = (h ^ (unsigned long)a[i + 2]) * 0x9e3779b97f4a7c15ul;
        g += (unsigned long)(b[i + 2] * a[i + 3]);
        h = (h ^ (unsigned long)a[i + 3]) * 0x9e3779b97f4a7c15ul;
        g += (unsigned long)(b[i + 3] * a[i]);
        h ^= h >> 29;
    }
    y[0] = (long)(h + g);
}

/* Scalar double loop on x87: two independent Horner chains per trip (elements i and i+1, in
   source order one after the other) and one serial running sum. */
void CAT(x87poly, V)(void *restrict yy, const void *restrict xx, const void *restrict pp,
                     unsigned long n)
{
    double *restrict y = yy;
    const double *restrict x = xx, *restrict c = pp;
    double s = 0;
    for (unsigned long i = 0; i + 2 <= n; i += 2) {
        double u = ((c[3] * x[i] + c[2]) * x[i] + c[1]) * x[i] + c[0];
        double v = ((c[3] * x[i + 1] + c[2]) * x[i + 1] + c[1]) * x[i + 1] + c[0];
        y[i] = u;
        y[i + 1] = v;
        s = s + u;
        s = s + v;
    }
    y[n] = s;
}

#else /* DRIVER */
/* prog MODE THREADS_PER_CORE [ROUNDS [SECONDS [MAX_CORES]]]
   MODE m2: six M2 kernels at the L2 working set (16384 outputs per worker at 1 thread per core,
   4096 at 4), on every whole core the affinity mask allows, up to MAX_CORES (default 60).
   MODE scalar: the two scalar kernels on one core, as 1 pinned thread or 4 copies (THREADS=4).
   Per kernel and round, every variant runs once in a shuffled order (ADR-0010 pairing): an untimed
   checked call on every worker, then a batch of about SECONDS on all workers at once, timed from
   the start barrier to the end barrier.  ratio = ms(variant) / ms(base) in the same round. */
#define _GNU_SOURCE
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "kernels.h"
#ifndef CLOCK_MONOTONIC_RAW
#define CLOCK_MONOTONIC_RAW CLOCK_MONOTONIC
#endif

#define VARIANTS(X) X(base) X(nosched) X(pre) X(prepress) X(prepress1)
#define NV 5
#define M2K(X, v) X(affine_f32, v) X(affine_f64, v) X(stencil1, v) X(stencil2, v) X(mat8, v) \
    X(mat16, v)
#define DECL1(k, v) void k##_##v(void *restrict, const void *restrict, const void *restrict, \
                                 unsigned long);
#define DECL2(k, v) DECL1(m2_##k, v)
#define DECL(v) M2K(DECL2, v) DECL1(ichain, v) DECL1(x87poly, v)
VARIANTS(DECL)

static const char *const VNAME[NV] = { "base", "nosched", "pre", "prepress", "prepress1" };
enum { AFF32, AFF64, ST1, ST2, MAT8, MAT16, ICHAIN, X87POLY, NK };
static const char *const KNAME[NK] = { "affine_f32", "affine_f64", "stencil1", "stencil2", "mat8",
                                       "mat16", "ichain", "x87poly" };
#define ROW(k) { m2_##k##_base, m2_##k##_nosched, m2_##k##_pre, m2_##k##_prepress, \
                 m2_##k##_prepress1 }
static const kernel_fn FN[NK][NV] = {
    ROW(affine_f32), ROW(affine_f64), ROW(stencil1), ROW(stencil2), ROW(mat8), ROW(mat16),
    { ichain_base, ichain_nosched, ichain_pre, ichain_prepress, ichain_prepress1 },
    { x87poly_base, x87poly_nosched, x87poly_pre, x87poly_prepress, x87poly_prepress1 } };
enum { SCALAR_N = 256 };

struct worker {
    pthread_t thread;
    int id, cpu;
    void *y, *x, *p, *alloc;
    size_t ybytes;
    unsigned long n;
} W[MAX_WORKERS];
static int nworkers, kernel, variant;
static long reps;
static volatile int quit;
static pthread_barrier_t start, finish;

static double now(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC_RAW, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}

void die(const char *what)
{
    printf("RESULT FAIL: %s\n", what);
    exit(2);
}

static void *aligned(size_t bytes)
{
    void *p;
    if (posix_memalign(&p, 64, bytes))
        die("out of memory");
    memset(p, 0, bytes);
    return p;
}

/* Buffers for kernel K on worker w, first-touched by that worker (it is already pinned). */
static void setup(struct worker *w, int k, unsigned long n)
{
    free(w->alloc ? w->alloc : w->x), free(w->p); /* stencil x points inside alloc */
    w->alloc = w->x = w->p = 0;
    w->n = n;
    if (k == ICHAIN) {
        long *a = aligned(n * sizeof *a), *b = aligned(n * sizeof *b);
        for (unsigned long i = 0; i < n; i++)
            a[i] = (long)(i * 2654435761u % 1000003) - 500000, b[i] = (long)(i % 97) - 48;
        w->x = a, w->p = b, w->ybytes = sizeof(long);
    } else if (k == X87POLY) {
        double *x = aligned(n * sizeof *x), *c = aligned(4 * sizeof *c);
        for (unsigned long i = 0; i < n; i++)
            x[i] = (double)((long)(i % 63) - 31) / 4;
        c[0] = 0.5, c[1] = -1.25, c[2] = 0.75, c[3] = 0.25;
        w->x = x, w->p = c, w->ybytes = (n + 1) * sizeof(double);
    } else if (k == AFF32 || k == AFF64) {
        size_t e = k == AFF64 ? 8 : 4;
        w->x = aligned(n * e), w->p = aligned(16), w->ybytes = n * e;
        for (unsigned long i = 0; i < n; i++)
            if (k == AFF64)
                ((double *)w->x)[i] = (double)((long)(i % 127) - 63) / 4;
            else
                ((float *)w->x)[i] = (float)((long)(i % 127) - 63) / 4;
        if (k == AFF64)
            ((double *)w->p)[0] = 2, ((double *)w->p)[1] = 0.5;
        else
            ((float *)w->p)[0] = 2, ((float *)w->p)[1] = 0.5;
    } else if (k == ST1) {
        float *x = aligned((n + 32) * sizeof *x);
        for (unsigned long i = 0; i < n + 32; i++)
            x[i] = (float)((long)(i % 127) - 63) / 4;
        w->alloc = x, w->x = 0, w->ybytes = n * sizeof(float);
        w->x = x + 16; /* x[-1] and x[n] are initialized halo */
    } else if (k == ST2) {
        unsigned long rows = (n + WIDTH - 1) / WIDTH;
        size_t count = (rows + 2) * PITCH + 32;
        float *x = aligned(count * sizeof *x);
        for (size_t i = 0; i < count; i++)
            x[i] = (float)((long)(i % 127) - 63) / 4;
        w->alloc = x, w->ybytes = n * sizeof(float);
        w->x = x + PITCH + 16;
    } else {
        unsigned d = k == MAT8 ? 8 : 16;
        size_t count = (n + d - 1) / d * 16;
        float *x = aligned(count * sizeof *x), *a = aligned(256 * sizeof *a);
        for (size_t i = 0; i < count; i++)
            x[i] = (float)((long)(i % 127) - 63) / 4;
        for (int i = 0; i < 256; i++)
            a[i] = (float)(i % 17 - 8) / 4;
        w->x = x, w->p = a, w->ybytes = n * sizeof(float);
    }
    free(w->y);
    w->y = aligned(w->ybytes + 64);
}

static void call(struct worker *w)
{
    FN[kernel][variant](w->y, w->x, w->p, w->n);
}

static void pin(int cpu)
{
    cpu_set_t m;
    CPU_ZERO(&m);
    CPU_SET(cpu, &m);
    if (sched_setaffinity(0, sizeof m, &m) || sched_getcpu() != cpu)
        die("pinning");
}

static void *run(void *arg)
{
    struct worker *w = arg;
    pin(w->cpu);
    for (;;) {
        pthread_barrier_wait(&start);
        if (quit)
            return 0;
        if (reps < 0)
            call(w); /* checked call: output is compared after the barrier */
        else if (reps == 0)
            setup(w, kernel, w->n);
        else
            for (long r = 0; r < reps; r++)
                call(w);
        pthread_barrier_wait(&finish);
    }
}

/* One phase on every worker (worker 0 is this thread); returns its wall time. */
static double phase(long r)
{
    reps = r;
    double t0 = now();
    pthread_barrier_wait(&start);
    if (r < 0)
        call(&W[0]);
    else if (r == 0)
        setup(&W[0], kernel, W[0].n);
    else
        for (long i = 0; i < r; i++)
            call(&W[0]);
    pthread_barrier_wait(&finish);
    return now() - t0;
}

static int cmp(const void *a, const void *b)
{
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}

static double median(double *v, int n)
{
    qsort(v, n, sizeof *v, cmp);
    return n % 2 ? v[n / 2] : (v[n / 2 - 1] + v[n / 2]) / 2;
}

/* Whole cores whose four siblings are all in the affinity mask, skipping the core of CPU 0. */
static int topology(int tpc, int maxcores)
{
    static int sib[64][4], cnt[64], os_core = -1;
    cpu_set_t allowed;
    FILE *f = fopen("/proc/cpuinfo", "r");
    if (!f || sched_getaffinity(0, sizeof allowed, &allowed))
        die("topology");
    char line[2048];
    int cpu = -1, core = -1, cores = 0;
    for (;;) {
        int end = !fgets(line, sizeof line, f);
        if (end || line[0] == '\n') {
            if (cpu >= 0 && core >= 0 && core < 64 && cnt[core] < 4) {
                sib[core][cnt[core]++] = cpu;
                if (cpu == 0)
                    os_core = core;
            }
            cpu = core = -1;
            if (end)
                break;
        } else if (sscanf(line, "processor : %d", &cpu) == 1) {
        } else if (sscanf(line, "core id : %d", &core) == 1) {
        }
    }
    fclose(f);
    for (int c = 0; c < 64 && cores < maxcores; c++) {
        int ok = cnt[c] == 4 && c != os_core;
        for (int i = 0; ok && i < 4; i++)
            ok = CPU_ISSET(sib[c][i], &allowed);
        if (!ok)
            continue;
        for (int i = 0; i < 4; i++) /* siblings in ascending CPU order */
            for (int j = i + 1; j < 4; j++)
                if (sib[c][j] < sib[c][i]) {
                    int t = sib[c][i];
                    sib[c][i] = sib[c][j], sib[c][j] = t;
                }
        for (int t = 0; t < tpc; t++) {
            W[nworkers].id = nworkers, W[nworkers].cpu = sib[c][t];
            nworkers++;
        }
        cores++;
    }
    if (!cores)
        die("no whole core allowed");
    return cores;
}

int main(int argc, char **argv)
{
    if (argc < 3)
        return printf("usage: %s m2|scalar 1|4 [ROUNDS [SECONDS [MAX_CORES]]]\n", argv[0]), 2;
    int m2 = !strcmp(argv[1], "m2"), tpc = atoi(argv[2]), bad = 0;
    int rounds = argc > 3 ? atoi(argv[3]) : 21;
    double target = argc > 4 ? atof(argv[4]) : 0.1;
    int maxcores = m2 ? (argc > 5 ? atoi(argv[5]) : 60) : 1;
    if ((!m2 && strcmp(argv[1], "scalar")) || (tpc != 1 && tpc != 4) || rounds < 1 || target <= 0
        || maxcores < 1)
        return printf("RESULT FAIL: bad arguments\n"), 2;
    int cores = topology(tpc, maxcores);
    unsigned long n = m2 ? (tpc == 1 ? 16384 : 4096) : SCALAR_N;
    printf("SETUP mode=%s threads_per_core=%d cores=%d workers=%d n=%lu rounds=%d target=%.3f\n",
           argv[1], tpc, cores, nworkers, n, rounds, target);
    for (int i = 0; i < nworkers; i++)
        printf("PLACEMENT worker=%d cpu=%d\n", i, W[i].cpu);
    pin(W[0].cpu);
    pthread_barrier_init(&start, 0, nworkers);
    pthread_barrier_init(&finish, 0, nworkers);
    for (int i = 0; i < nworkers; i++)
        W[i].n = n;
    for (int i = 1; i < nworkers; i++)
        if (pthread_create(&W[i].thread, 0, run, &W[i]))
            die("pthread_create");
    double *ms = malloc(sizeof *ms * NV * rounds), *ratio = malloc(sizeof *ratio * NV * rounds);
    unsigned char *ref = 0;
    int first = m2 ? AFF32 : ICHAIN, last = m2 ? MAT16 : X87POLY;
    for (kernel = first; kernel <= last; kernel++) {
        phase(0); /* allocate and first-touch on each worker */
        size_t bytes = W[0].ybytes;
        free(ref);
        ref = malloc(bytes);
        long nreps[NV];
        for (variant = 0; variant < NV; variant++) {
            phase(-1);
            int same = 1;
            for (int i = 0; i < nworkers; i++)
                same &= variant ? !memcmp(W[i].y, ref, bytes) : !memcmp(W[i].y, W[0].y, bytes);
            if (!variant)
                memcpy(ref, W[0].y, bytes);
            unsigned long sum = 0;
            for (size_t b = 0; b < bytes; b++)
                sum = sum * 131 + ((unsigned char *)W[0].y)[b];
            bad += !same;
            printf("CHECK %s %s checksum=%016lx %s\n", KNAME[kernel], VNAME[variant], sum,
                   same ? "ok" : "MISMATCH");
            double t = phase(1);
            nreps[variant] = t > 0 && target / t > 1 ? (long)(target / t) : 1;
            printf("PILOT %s %s ms_per_call=%.5f reps=%ld\n", KNAME[kernel], VNAME[variant],
                   t * 1e3, nreps[variant]);
        }
        unsigned seed = 2020u + kernel;
        for (int r = 0; r < rounds; r++) {
            int order[NV];
            for (int v = 0; v < NV; v++)
                order[v] = v;
            for (int v = NV - 1; v > 0; v--) {
                seed = seed * 1103515245u + 12345u;
                int j = (seed >> 16) % (v + 1), x = order[v];
                order[v] = order[j], order[j] = x;
            }
            for (int i = 0; i < NV; i++) {
                variant = order[i];
                phase(-1); /* warm caches and code for this variant, and check it */
                for (int w = 0; w < nworkers; w++)
                    if (memcmp(W[w].y, ref, bytes)) {
                        bad++;
                        printf("MISMATCH %s %s round=%d worker=%d\n", KNAME[kernel],
                               VNAME[variant], r, w);
                    }
                ms[variant * rounds + r] = phase(nreps[variant]) * 1e3 / nreps[variant];
            }
            for (int v = 0; v < NV; v++) {
                ratio[v * rounds + r] = ms[v * rounds + r] / ms[r];
                printf("ROUND %s %d %s first=%s ms=%.5f ratio=%.4f\n", KNAME[kernel], r, VNAME[v],
                       VNAME[order[0]], ms[v * rounds + r], ratio[v * rounds + r]);
            }
        }
        for (int v = 0; v < NV; v++) {
            double *m = ms + v * rounds, *q = ratio + v * rounds;
            double med = median(m, rounds), rmed = median(q, rounds);
            printf("SUMMARY %s tpc=%d %s median_ms=%.5f ns_per_element=%.4f ratio_median=%.4f "
                   "ratio_min=%.4f ratio_max=%.4f rounds=%d\n", KNAME[kernel], tpc, VNAME[v], med,
                   med * 1e6 / ((double)n * nworkers), rmed, q[0], q[rounds - 1], rounds);
        }
    }
    quit = 1;
    pthread_barrier_wait(&start);
    for (int i = 1; i < nworkers; i++)
        pthread_join(W[i].thread, 0);
    printf("RESULT %s\n", bad ? "FAIL: output mismatch" : "ok");
    return bad != 0;
}
#endif
