/* S6-01 research probe. Numeric record schema: docs/research/knc-measurement.md.
   Run only through the lead's exclusive card_run --benchmark window. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <limits.h>
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

enum { CORES = 60, THREADS = 240, REPS = 21, GROUPS = 5, CALLS = 10001 };
static int topology[61][4], count[61], cores = 60, density = 4, workers;
static size_t length = 262144;
static unsigned batch = 1;
static clockid_t wall = CLOCK_MONOTONIC;
static pthread_barrier_t barrier;
static cpu_set_t allowed;
struct worker {
    int id, cpu, observed;
    float *a, *b, *c;
    uint64_t start, end, ticks;
    unsigned long bad;
};
static struct worker data[THREADS];

static void fail(int stage, int error) {
    printf("99 %d %d\n", stage, error);
    fflush(stdout);
    exit(1);
}
static uint64_t clock_ns(clockid_t clock) {
    struct timespec t;
    if (clock_gettime(clock, &t)) fail(1, errno);
    return (uint64_t)t.tv_sec * 1000000000ULL + t.tv_nsec;
}
static uint64_t now(void) { return clock_ns(wall); }
static inline uint64_t tsc(void) {
    unsigned lo, hi;
    __asm__ volatile ("rdtsc" : "=a"(lo), "=d"(hi) : : "memory");
    return ((uint64_t)hi << 32) | lo;
}
static void cpuid(unsigned leaf, unsigned *a, unsigned *d) {
    unsigned b, c;
    __asm__ volatile ("cpuid" : "=a"(*a), "=b"(b), "=c"(c), "=d"(*d)
                      : "a"(leaf), "c"(0) : "memory");
}
/* CPUID works on KNC; LFENCE/RDTSCP must not be assumed. Both sides of
   RDTSC are serialized. The measured interval includes boundary overhead. */
static uint64_t ordered_tsc(void) {
    unsigned a, d;
    uint64_t t;
    cpuid(0, &a, &d);
    t = tsc();
    cpuid(0, &a, &d);
    return t;
}
static void pin(int cpu) {
    cpu_set_t mask, actual;
    CPU_ZERO(&mask);
    CPU_SET(cpu, &mask);
    if (!CPU_ISSET(cpu, &allowed)) fail(2, cpu);
    if (sched_setaffinity(0, sizeof(mask), &mask)) fail(3, errno);
    if (sched_getaffinity(0, sizeof(actual), &actual)) fail(4, errno);
    if (CPU_COUNT(&actual) != 1 || !CPU_ISSET(cpu, &actual)) fail(5, cpu);
}
static int compare(const void *a, const void *b) {
    uint64_t x = *(const uint64_t *)a, y = *(const uint64_t *)b;
    return (x > y) - (x < y);
}
static void topology_read(void) {
    FILE *f = fopen("/proc/cpuinfo", "r");
    char line[2048];
    int cpu = -1, core = -1, constant = 0, nonstop = 0;
    double mhz = 0;
    if (!f) fail(6, errno);
    /* Process a final unterminated block too. */
    for (;;) {
        int end = !fgets(line, sizeof(line), f);
        if (end || line[0] == '\n') {
            if (cpu >= 0) {
                if (core < 0 || core > 60 || cpu >= CPU_SETSIZE || count[core] == 4)
                    fail(7, cpu);
                topology[core][count[core]++] = cpu;
                printf("1 %d %d %.3f %d %d %d\n", cpu, core, mhz,
                       constant, nonstop, CPU_ISSET(cpu, &allowed) != 0);
            }
            cpu = core = -1;
            mhz = 0; constant = nonstop = 0;
            if (end) break;
        } else if (sscanf(line, "processor : %d", &cpu) == 1) {
        } else if (sscanf(line, "core id : %d", &core) == 1) {
        } else if (sscanf(line, "cpu MHz : %lf", &mhz) == 1) {
        } else if (!strncmp(line, "flags", 5)) {
            constant = strstr(line, "constant_tsc") != NULL;
            nonstop = strstr(line, "nonstop_tsc") != NULL;
        }
    }
    if (ferror(f)) fail(8, errno);
    fclose(f);
    for (int c = 0; c < cores; ++c) {
        if (count[c] != 4) fail(9, c);
        for (int i = 0; i < 4; ++i)
            for (int j = i + 1; j < 4; ++j)
                if (topology[c][i] > topology[c][j]) {
                    int tmp = topology[c][i];
                    topology[c][i] = topology[c][j]; topology[c][j] = tmp;
                }
    }
}
/* Encode names and contents as decimal bytes to preserve numbers-only stdout.
   Missing sysfs interfaces are evidence, not fatal measurement errors. */
static void policy_record(int phase, const char *path, int error,
                          const unsigned char *value, size_t size) {
    printf("10 %d %d %zu %zu", phase, error, strlen(path), size);
    for (const unsigned char *p = (const unsigned char *)path; *p; ++p)
        printf(" %u", (unsigned)*p);
    for (size_t i = 0; i < size; ++i) printf(" %u", (unsigned)value[i]);
    putchar('\n');
}
static void policy_file(int phase, const char *path) {
    unsigned char value[4096];
    size_t size = 0;
    int error = 0;
    FILE *f = fopen(path, "r");
    if (!f) error = errno;
    else {
        size = fread(value, 1, sizeof(value), f);
        if (ferror(f)) error = errno ? errno : EIO;
        else if (size == sizeof(value) && fgetc(f) != EOF) error = EOVERFLOW;
        if (ferror(f) && !error) error = errno ? errno : EIO;
        fclose(f);
    }
    policy_record(phase, path, error, value, size);
}
static void policy(int phase) {
    const char *base = "/sys/devices/system/cpu/cpu0/cpufreq";
    DIR *dir;
    struct dirent *entry;
    char path[PATH_MAX];
    policy_file(phase, "/sys/devices/system/clocksource/clocksource0/current_clocksource");
    policy_file(phase, "/sys/devices/system/clocksource/clocksource0/available_clocksource");
    dir = opendir(base);
    if (!dir) { policy_record(phase, base, errno, NULL, 0); return; }
    for (;;) {
        errno = 0;
        entry = readdir(dir);
        if (!entry) {
            policy_record(phase, base, errno, NULL, 0);
            break;
        }
        if (strncmp(entry->d_name, "scaling", 7) && !strstr(entry->d_name, "governor"))
            continue;
        int n = snprintf(path, sizeof(path), "%s/%s", base, entry->d_name);
        if (n < 0 || (size_t)n >= sizeof(path)) fail(27, ENAMETOOLONG);
        policy_file(phase, path);
    }
    closedir(dir);
}
static void clocks(void) {
    uint64_t delta[CALLS], begin, end, prev, cur, minimum;
    unsigned a, d, max;
    struct timespec res;
    cpuid(0x80000000U, &max, &d);
    d = 0;
    if (max >= 0x80000007U) cpuid(0x80000007U, &a, &d);
    printf("2 %u %u %u\n", max, d, (d >> 8) & 1);
    for (int kind = 0; kind < 3; ++kind) {
        minimum = UINT64_MAX;
        prev = kind == 0 ? now() : kind == 1 ? tsc() : ordered_tsc();
        for (int i = 0; i < CALLS; ++i) {
            cur = kind == 0 ? now() : kind == 1 ? tsc() : ordered_tsc();
            delta[i] = cur - prev;
            if (delta[i] && delta[i] < minimum) minimum = delta[i];
            prev = cur;
        }
        qsort(delta, CALLS, sizeof(*delta), compare);
        begin = now();
        for (int i = 0; i < CALLS; ++i) {
            if (kind == 0) (void)now();
            else if (kind == 1) (void)tsc();
            else (void)ordered_tsc();
        }
        end = now();
        if (clock_getres(wall, &res)) fail(10, errno);
        printf("3 %d %d %llu %llu %llu %.3f\n", kind, (int)wall,
               (unsigned long long)(kind ? 0 : (uint64_t)res.tv_sec * 1000000000ULL + res.tv_nsec),
               (unsigned long long)(minimum == UINT64_MAX ? 0 : minimum),
               (unsigned long long)delta[CALLS/2], (double)(end - begin)/CALLS);
    }
}
static void calibrate(int phase) {
#ifdef CLOCK_MONOTONIC_RAW
    struct timespec res, pause = {0, 200000000};
    if (clock_gettime(CLOCK_MONOTONIC_RAW, &res)) {
        printf("4 %d -1 -1 %d %d 0 0 0\n", phase, (int)CLOCK_MONOTONIC_RAW, errno);
        return;
    }
    for (int mode = 0; mode < 2; ++mode)
        for (int trial = 0; trial < 3; ++trial) {
            uint64_t w0 = clock_ns(CLOCK_MONOTONIC_RAW), t0 = ordered_tsc(), t1, w1;
            if (!mode) {
                struct timespec remain = pause;
                while (nanosleep(&remain, &remain))
                    if (errno != EINTR) fail(11, errno);
            } else {
                while (clock_ns(CLOCK_MONOTONIC_RAW) - w0 < 200000000ULL)
                    __asm__ volatile ("" ::: "memory");
            }
            t1 = ordered_tsc(); w1 = clock_ns(CLOCK_MONOTONIC_RAW);
            printf("4 %d %d %d %d 0 %llu %llu %.6f\n", phase, mode, trial,
                   (int)CLOCK_MONOTONIC_RAW,
                   (unsigned long long)(w1-w0), (unsigned long long)(t1-t0),
                   1000.0 * (double)(t1-t0)/(double)(w1-w0));
        }
#else
    printf("4 %d -1 -1 -1 %d 0 0 0\n", phase, ENOSYS);
#endif
}
static __attribute__((noinline)) void stream(struct worker *w) {
    float *restrict a = w->a, *restrict b = w->b, *restrict c = w->c;
    for (size_t i = 0; i < length; ++i) c[i] = a[i] + 2.0f * b[i];
    __asm__ volatile ("" ::: "memory");
}
static void wait_all(void) {
    int rc = pthread_barrier_wait(&barrier);
    if (rc && rc != PTHREAD_BARRIER_SERIAL_THREAD) fail(12, rc);
}
static void *work(void *arg) {
    struct worker *w = arg;
    pin(w->cpu);
    for (size_t i = 0; i < length; ++i) {
        w->a[i] = (float)(i & 15); w->b[i] = 0.5f; w->c[i] = 0;
    }
    for (int phase = 0; phase < 1 + GROUPS * (3 + REPS); ++phase) {
        uint64_t t;
        wait_all();
        w->observed = sched_getcpu();
        if (w->observed != w->cpu) fail(13, w->observed);
        w->start = now(); t = ordered_tsc();
        for (unsigned r = 0; r < batch; ++r) stream(w);
        w->ticks = ordered_tsc() - t; w->end = now();
        if (sched_getcpu() != w->cpu) fail(14, w->cpu);
        wait_all();
    }
    for (size_t i = 0; i < length; ++i)
        if (w->c[i] != (float)(i & 15) + 1.0f) ++w->bad;
    return NULL;
}
static uint64_t sample(void) {
    uint64_t first = UINT64_MAX, last = 0;
    wait_all(); wait_all();
    for (int i = 0; i < workers; ++i) {
        if (data[i].start < first) first = data[i].start;
        if (data[i].end > last) last = data[i].end;
    }
    return last - first;
}
static unsigned long argument(const char *s, unsigned long max) {
    char *end;
    unsigned long n;
    errno = 0; n = strtoul(s, &end, 10);
    if (errno || *end || !*s || !n || n > max || *s == '-') fail(15, 0);
    return n;
}
int main(int argc, char **argv) {
    pthread_t threads[THREADS];
    pthread_attr_t attr;
    struct timespec res;
    uint64_t times[REPS], medians[GROUPS], pilot;
    unsigned long bad = 0;
    int rc;
    if (argc != 1 && argc != 4) fail(16, argc);
    if (argc == 4) {
        cores = argument(argv[1], CORES); density = argument(argv[2], 4);
        length = argument(argv[3], 1048576);
    }
    workers = cores * density;
    if (sched_getaffinity(0, sizeof(allowed), &allowed)) fail(17, errno);
    topology_read(); pin(topology[0][0]);
#ifdef CLOCK_MONOTONIC_RAW
    if (!clock_getres(CLOCK_MONOTONIC_RAW, &res)) wall = CLOCK_MONOTONIC_RAW;
#endif
    clocks();
    policy(0); calibrate(0);
    if ((rc = pthread_barrier_init(&barrier, NULL, workers + 1))) fail(18, rc);
    if ((rc = pthread_attr_init(&attr))) fail(19, rc);
    if ((rc = pthread_attr_setstacksize(&attr, 128 * 1024))) fail(20, rc);
    for (int i = 0; i < workers; ++i) {
        struct worker *w = &data[i];
        w->id = i; w->cpu = topology[i/density][i%density];
        if ((rc = posix_memalign((void **)&w->a, 64, length * sizeof(float)))) fail(21, rc);
        if ((rc = posix_memalign((void **)&w->b, 64, length * sizeof(float)))) fail(22, rc);
        if ((rc = posix_memalign((void **)&w->c, 64, length * sizeof(float)))) fail(23, rc);
        if ((rc = pthread_create(&threads[i], &attr, work, w))) fail(24, rc);
    }
    pilot = sample();
    if (!pilot) fail(25, 0);
    batch = (unsigned)((100000000ULL + pilot - 1)/pilot);
    if (!batch) batch = 1;
    printf("0 2 %d %d %zu %u %d %d %d\n", cores, density, length, batch, GROUPS, REPS, 3);
    for (int i = 0; i < workers; ++i)
        printf("5 %d %d %d %d %d\n", i, i/density, i%density, data[i].cpu, data[i].observed);
    for (int g = 0; g < GROUPS; ++g) {
        for (int warm = 0; warm < 3; ++warm) (void)sample();
        for (int r = 0; r < REPS; ++r) {
            times[r] = sample();
            /* Print only with all workers blocked outside the measured region. */
            printf("6 %d %d %llu %llu\n", g, r, (unsigned long long)times[r],
                   (unsigned long long)data[0].ticks);
        }
        qsort(times, REPS, sizeof(*times), compare);
        medians[g] = times[REPS/2];
        printf("7 %d %llu %llu %llu %.6f\n", g, (unsigned long long)times[0],
               (unsigned long long)times[REPS/2], (unsigned long long)times[REPS-1],
               100.0 * (double)(times[REPS-1]-times[0])/times[REPS/2]);
    }
    qsort(medians, GROUPS, sizeof(*medians), compare);
    double spread = 100.0 * (double)(medians[GROUPS-1]-medians[0])/medians[GROUPS/2];
    printf("8 %llu %llu %llu %.6f %d\n", (unsigned long long)medians[0],
           (unsigned long long)medians[GROUPS/2], (unsigned long long)medians[GROUPS-1],
           spread, spread < 2.0);
    for (int i = 0; i < workers; ++i) {
        if ((rc = pthread_join(threads[i], NULL))) fail(26, rc);
        bad += data[i].bad;
        free(data[i].a); free(data[i].b); free(data[i].c);
    }
    printf("9 %lu\n", bad);
    pthread_attr_destroy(&attr); pthread_barrier_destroy(&barrier);
    calibrate(1); policy(1);
    return bad ? 1 : spread < 2.0 ? 0 : 2;
}
