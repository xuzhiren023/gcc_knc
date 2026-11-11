/* S9-19: three loop shapes with no OpenMP in the plain variants, for -ftree-parallelize-loops=N.
   Built by tools/s9_19_auto.py once per variant with -DV=<name>:
     -DOMP=0  plain loops; the variant's parallelism comes only from -ftree-parallelize-loops=N
     -DOMP=T  the same loops with "#pragma omp parallel for num_threads(T)" (built with -fopenmp)
   and once with -DDRIVER for main().  Data are small integers so every sum is exact in any order,
   and every variant must give the serial checksum bit for bit. */
#define NX 4096 /* stencil grid NX x NX */
#define CAT2(a, b) a##_##b
#define CAT(a, b) CAT2(a, b)

#ifndef DRIVER
#if OMP
#define PRAGMA(x) _Pragma(#x)
#define PAR PRAGMA(omp parallel for num_threads(OMP))
#define PAR_SUM PRAGMA(omp parallel for num_threads(OMP) reduction(+ : s))
#else
#define PAR
#define PAR_SUM
#endif

/* Streaming triad: one store and two loads per element. */
void CAT(triad, V)(double *restrict a, const double *restrict b, const double *restrict c,
                   double q, long n)
{
    PAR
    for (long i = 0; i < n; i++)
        a[i] = b[i] + q * c[i];
}

/* Five-point Jacobi step on the interior of an NX x NX grid. */
void CAT(stencil, V)(double (*restrict out)[NX], const double (*restrict in)[NX])
{
    PAR
    for (long i = 1; i < NX - 1; i++)
        for (long j = 1; j < NX - 1; j++)
            out[i][j] = 0.25 * (in[i - 1][j] + in[i + 1][j] + in[i][j - 1] + in[i][j + 1]);
}

/* Dot product: a floating-point sum reduction. */
double CAT(reduce, V)(const double *restrict a, const double *restrict b, long n)
{
    double s = 0;
    PAR_SUM
    for (long i = 0; i < n; i++)
        s += a[i] * b[i];
    return s;
}

#else /* DRIVER */
/* prog [ROUNDS [SECONDS [N]]]: per kernel and round, every variant once in a shuffled order: an
   untimed checked call, then a batch of about SECONDS. N is the triad and reduction length. */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#ifndef CLOCK_MONOTONIC_RAW
#define CLOCK_MONOTONIC_RAW CLOCK_MONOTONIC
#endif

#define VARIANTS(X) X(par1) X(par60) X(par120) X(par240) X(omp60) X(omp120) X(omp240)
#define DECL(v)                                                                                 \
    void triad_##v(double *restrict, const double *restrict, const double *restrict, double, long); \
    void stencil_##v(double (*restrict)[NX], const double (*restrict)[NX]);                     \
    double reduce_##v(const double *restrict, const double *restrict, long);
VARIANTS(DECL)

static double *A, *B, *C, (*G)[NX], (*H)[NX];
static long N;

/* One call of a kernel; with CHECK, also its checksum (a serial sum, kept out of timed batches). */
#define CALLS(v)                                                                             \
    static double t_##v(int check) { triad_##v(A, B, C, 3.0, N); return check ? sum(A, N) : 0; } \
    static double s_##v(int check)                                                           \
    { stencil_##v(H, (const double (*)[NX])G); return check ? sum(*H, (long)NX * NX) : 0; }   \
    static double r_##v(int check) { (void)check; return reduce_##v(A, B, N); }

static double sum(const double *x, long n)
{
    double s = 0;
    for (long i = 0; i < n; i++)
        s += x[i];
    return s;
}
VARIANTS(CALLS)

#define ROWS_T(v) { #v, t_##v },
#define ROWS_S(v) { #v, s_##v },
#define ROWS_R(v) { #v, r_##v },
static const struct { const char *name; double (*fn)(int); } T[][7] = {
    { VARIANTS(ROWS_T) }, { VARIANTS(ROWS_S) }, { VARIANTS(ROWS_R) } };
static const char *const KERNEL[] = { "triad", "stencil", "reduce" };
#define NV 7

static double now(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC_RAW, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
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

int main(int argc, char **argv)
{
    int rounds = argc > 1 ? atoi(argv[1]) : 11, bad = 0;
    double target = argc > 2 ? atof(argv[2]) : 0.1;
    N = argc > 3 ? atol(argv[3]) : 8L << 20;
    if (rounds < 1 || target <= 0 || N < 1)
        return 2;
    A = malloc(sizeof *A * N), B = malloc(sizeof *B * N), C = malloc(sizeof *C * N);
    G = malloc(sizeof *G * NX), H = malloc(sizeof *H * NX);
    if (!A || !B || !C || !G || !H)
        return printf("RESULT FAIL: out of memory\n"), 2;
    for (long i = 0; i < N; i++)
        A[i] = i % 7, B[i] = i % 5 - 2.0, C[i] = i % 3;
    for (long i = 0; i < NX; i++)
        for (long j = 0; j < NX; j++)
            G[i][j] = (i * 3 + j) % 9, H[i][j] = 0;
    printf("SETUP n=%ld nx=%d rounds=%d target=%.3f\n", N, NX, rounds, target);
    double *ms = malloc(sizeof *ms * NV * rounds), *ratio = malloc(sizeof *ratio * NV * rounds);
    for (int k = 0; k < 3; k++) {
        double ref = T[k][0].fn(1), t;
        long reps[NV];
        for (int v = 0; v < NV; v++) {
            double c = T[k][v].fn(1);
            bad += c != ref;
            printf("CHECK %s %s checksum=%.17g %s\n", KERNEL[k], T[k][v].name, c,
                   c == ref ? "ok" : "MISMATCH");
            double t0 = now();
            T[k][v].fn(0);
            t = now() - t0;
            reps[v] = t > 0 && target / t > 1 ? (long)(target / t) : 1;
            printf("PILOT %s %s ms_per_call=%.3f reps=%ld\n", KERNEL[k], T[k][v].name, t * 1e3,
                   reps[v]);
        }
        unsigned seed = 12345;
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
                int v = order[i];
                if (T[k][v].fn(1) != ref) { /* warm-up: sizes the thread team */
                    bad++;
                    printf("MISMATCH %s %s round=%d\n", KERNEL[k], T[k][v].name, r);
                }
                double t0 = now();
                for (long n = 0; n < reps[v]; n++)
                    T[k][v].fn(0);
                ms[v * rounds + r] = (now() - t0) * 1e3 / reps[v];
            }
            for (int v = 0; v < NV; v++) {
                ratio[v * rounds + r] = ms[v * rounds + r] / ms[r];
                printf("ROUND %s %d %s ms=%.4f ratio=%.4f\n", KERNEL[k], r, T[k][v].name,
                       ms[v * rounds + r], ratio[v * rounds + r]);
            }
        }
        for (int v = 0; v < NV; v++) {
            double *m = ms + v * rounds, *q = ratio + v * rounds;
            double med = median(m, rounds), rmed = median(q, rounds);
            printf("SUMMARY %s %s median_ms=%.4f ratio_median=%.4f ratio_min=%.4f ratio_max=%.4f "
                   "rounds=%d\n", KERNEL[k], T[k][v].name, med, rmed, q[0], q[rounds - 1], rounds);
        }
    }
    printf("RESULT %s\n", bad ? "FAIL: checksum mismatch" : "ok");
    return bad != 0;
}
#endif
