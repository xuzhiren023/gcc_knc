/* S6-03: lead-only exclusive benchmark. CHAR_HOST permits argument dry runs. */
#define _GNU_SOURCE
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
#include "kernels.h"

enum { GROUPS = 5, REPS = 21, WARM = 3 };
static int density = 4, cores = 1, topology[61][4], counts[61], selected = -1;
static unsigned long rounds = 1024;
static int fixed_rounds;
static cpu_set_t allowed;
static pthread_barrier_t barrier;
struct worker {
    int id, cpu;
    unsigned char *memory;
    uint64_t begin, end, ticks;
};
static struct worker workers[240];
static const struct test *current;
static size_t footprint;
static int stop;

static void fail(const char *message) {
    fprintf(stderr, "%s (errno=%d)\n", message, errno);
    exit(2);
}
static uint64_t now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC_RAW, &t)) fail("CLOCK_MONOTONIC_RAW");
    return (uint64_t)t.tv_sec * 1000000000ULL + t.tv_nsec;
}
static uint64_t ticks(void) {
    unsigned a, b, c, d, lo, hi;
    __asm__ volatile("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d) : "a"(0) : "memory");
    __asm__ volatile("rdtsc" : "=a"(lo), "=d"(hi) : : "memory");
    __asm__ volatile("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d) : "a"(0) : "memory");
    return ((uint64_t)hi << 32) | lo;
}
static unsigned long number(const char *s, unsigned long max) {
    char *end;
    unsigned long n;
    if (!*s || *s == '-' || *s == '+') fail("invalid numeric argument");
    errno = 0;
    n = strtoul(s, &end, 10);
    if (errno || *end || !n || n > max) fail("numeric argument out of range");
    return n;
}
static void topology_read(void) {
    FILE *f = fopen("/proc/cpuinfo", "r");
    char line[2048];
    int cpu = -1, core = -1;
    if (!f) fail("cpuinfo");
    for (;;) {
        int end = !fgets(line, sizeof(line), f);
        if (end || line[0] == '\n') {
            if (cpu >= 0) {
                if (core < 0 || core > 60 || cpu >= CPU_SETSIZE || counts[core] >= 4)
                    fail("unexpected KNC topology");
                topology[core][counts[core]++] = cpu;
            }
            cpu = core = -1;
            if (end) break;
        } else if (sscanf(line, "processor : %d", &cpu) == 1) {
        } else if (sscanf(line, "core id : %d", &core) == 1) {
        }
    }
    if (ferror(f)) fail("cpuinfo read");
    fclose(f);
    if (sched_getaffinity(0, sizeof(allowed), &allowed)) fail("allowed affinity");
    for (int c = 0; c < cores; ++c) {
        if (counts[c] != 4) fail("missing KNC siblings");
        for (int i = 0; i < 4; ++i)
            for (int j = i+1; j < 4; ++j)
                if (topology[c][j] < topology[c][i]) {
                    int t = topology[c][i];
                    topology[c][i] = topology[c][j]; topology[c][j] = t;
                }
    }
}
static void pin(int cpu) {
    cpu_set_t mask, actual;
    CPU_ZERO(&mask); CPU_SET(cpu, &mask);
    if (!CPU_ISSET(cpu, &allowed)) fail("CPU outside launch affinity");
    if (sched_setaffinity(0, sizeof(mask), &mask) ||
        sched_getaffinity(0, sizeof(actual), &actual) ||
        CPU_COUNT(&actual) != 1 || !CPU_ISSET(cpu, &actual)) fail("worker affinity");
}
static void wait_all(void) {
    int e = pthread_barrier_wait(&barrier);
    if (e && e != PTHREAD_BARRIER_SERIAL_THREAD) fail("barrier");
}
static uint64_t random_next(uint64_t *state) {
    *state ^= *state << 13; *state ^= *state >> 7; *state ^= *state << 17;
    return *state;
}
static void prepare(struct worker *w) {
    memset(w->memory, 0, footprint);
    if (current->kind == 1) {
        size_t n = footprint / 64;
        size_t *order = malloc(n * sizeof(*order));
        uint64_t state = 1234567 + w->id;
        if (!order) fail("pointer permutation allocation");
        for (size_t i = 0; i < n; ++i) order[i] = i;
        for (size_t i = n-1; i > 0; --i) {
            size_t j = random_next(&state) % (i+1), t = order[i];
            order[i] = order[j]; order[j] = t;
        }
        for (size_t i = 0; i < n; ++i)
            *(void **)(w->memory + 64*order[i]) = w->memory + 64*order[(i+1) % n];
        free(order);
    }
}
static void *worker_main(void *arg) {
    struct worker *w = arg;
    const struct test *last = NULL;
    pin(w->cpu);
    size_t allocation = 16*1024*1024;
    if (posix_memalign((void **)&w->memory, 64, allocation)) fail("allocation");
    for (;;) {
        wait_all();
        if (stop) break;
        if (last != current) { prepare(w); last = current; }
        wait_all();
        w->begin = now();
        uint64_t start = ticks();
        current->fn(rounds, w->memory, footprint);
        w->ticks = ticks() - start;
        w->end = now();
        wait_all();
    }
    free(w->memory);
    return NULL;
}
static uint64_t sample(void) {
    uint64_t first = UINT64_MAX, last = 0;
    wait_all(); wait_all(); wait_all();
    for (int i = 0; i < cores*density; ++i) {
        if (workers[i].begin < first) first = workers[i].begin;
        if (workers[i].end > last) last = workers[i].end;
    }
    return last - first;
}
static int compare(const void *p, const void *q) {
    uint64_t a = *(const uint64_t *)p, b = *(const uint64_t *)q;
    return (a > b) - (a < b);
}
static void policy(int phase) {
    static const char *paths[] = {
        "/sys/devices/system/clocksource/clocksource0/current_clocksource",
        "/sys/devices/system/clocksource/clocksource0/available_clocksource",
        "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor",
        "/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver",
        "/sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq",
        "/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq",
        "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"
    };
    for (size_t i = 0; i < sizeof(paths)/sizeof(paths[0]); ++i) {
        char line[1024];
        FILE *f = fopen(paths[i], "r");
        if (!f) { printf("policy %d %s unavailable %d\n", phase, paths[i], errno); continue; }
        if (!fgets(line, sizeof(line), f)) strcpy(line, "unreadable\n");
        line[strcspn(line, "\r\n")] = 0;
        printf("policy %d %s %s\n", phase, paths[i], line);
        fclose(f);
    }
}
static size_t budget(const char *name) {
    size_t size = !strncmp(name, "memory.", 7) ? 16*1024*1024 :
                  !strncmp(name, "l2.", 3) ? 256*1024 : 16*1024;
    size_t per = size / density, result = 2048;
    while (result*2 <= per) result *= 2;
    return result;
}
int main(int argc, char **argv) {
    int dry = 0, native = 0, unstable = 0;
    pthread_t threads[240];
    for (int i = 1; i < argc; ++i) {
        if (!strcmp(argv[i], "--dry-run")) dry = 1;
        else if (!strcmp(argv[i], "--native")) native = 1;
        else if ((!strcmp(argv[i], "--threads") || !strcmp(argv[i], "--cores") ||
                  !strcmp(argv[i], "--rounds") || !strcmp(argv[i], "--case")) && i+1 < argc) {
            const char *option = argv[i++], *value = argv[i];
            if (!strcmp(option, "--threads")) density = (int)number(value, 4);
            else if (!strcmp(option, "--cores")) cores = (int)number(value, 60);
            else if (!strcmp(option, "--rounds")) { rounds = number(value, 100000000); fixed_rounds = 1; }
            else {
                for (size_t k = 0; k < NTESTS; ++k)
                    if (!strcmp(value, tests[k].name)) selected = (int)k;
                if (selected < 0) fail("unknown measurement name");
            }
        } else fail("usage: --dry-run|--native [--threads 1..4] [--cores 1..60] [--case NAME] [--rounds N]");
    }
    if (dry == native) fail("choose exactly one execution mode");
    if (dry) {
        for (size_t k = 0; k < NTESTS; ++k)
            if (selected < 0 || (size_t)selected == k)
                printf("DRY %s %d cycles=unmeasured cores=%d bytes=%zu\n", tests[k].name,
                       density, cores, budget(tests[k].name));
        return 0;
    }
#ifdef CHAR_HOST
    fail("host executable supports --dry-run only");
#endif
    topology_read();
    policy(0);
    if (pthread_barrier_init(&barrier, NULL, cores*density+1)) fail("barrier init");
    for (int i = 0; i < cores*density; ++i) {
        workers[i].id = i; workers[i].cpu = topology[i/density][i%density];
        printf("pin %d %d\n", i, workers[i].cpu);
        if (pthread_create(&threads[i], NULL, worker_main, &workers[i])) fail("pthread_create");
    }
    for (size_t k = 0; k < NTESTS; ++k) {
        uint64_t medians[GROUPS];
        uint64_t tick_groups[240][GROUPS], tick_samples[240][REPS];
        if (selected >= 0 && (size_t)selected != k) continue;
        current = &tests[k]; footprint = budget(current->name);
        if (!fixed_rounds) {
            rounds = 1024;
            uint64_t elapsed = sample();
            double target = (double)rounds * 100000000.0 / (double)(elapsed ? elapsed : 1);
            rounds = target > 100000000 ? 100000000 : target < 1 ? 1 : (unsigned long)target;
        }
        for (int g = 0; g < GROUPS; ++g) {
            uint64_t times[REPS];
            for (int w = 0; w < WARM; ++w) (void)sample();
            for (int r = 0; r < REPS; ++r) {
                times[r] = sample();
                for (int i = 0; i < cores*density; ++i) {
                    tick_samples[i][r] = workers[i].ticks;
                    printf("sample %s %d %d %d %d %lu %llu %llu\n", current->name, density,
                           g, r, i, rounds, (unsigned long long)times[r],
                           (unsigned long long)workers[i].ticks);
                }
            }
            qsort(times, REPS, sizeof(*times), compare);
            medians[g] = times[REPS/2];
            for (int i = 0; i < cores*density; ++i) {
                qsort(tick_samples[i], REPS, sizeof(uint64_t), compare);
                tick_groups[i][g] = tick_samples[i][REPS/2];
            }
            printf("group %s %d %d %llu %llu %llu\n", current->name, density, g,
                   (unsigned long long)medians[g], (unsigned long long)times[0],
                   (unsigned long long)times[REPS-1]);
        }
        qsort(medians, GROUPS, sizeof(*medians), compare);
        double spread = (double)(medians[GROUPS-1]-medians[0]) / medians[GROUPS/2];
        for (int i = 0; i < cores*density; ++i) {
            qsort(tick_groups[i], GROUPS, sizeof(uint64_t), compare);
            printf("result %s %d cycles=%.6f cycle_unit=tsc_ticks worker=%d ns_per_unit=%.6f spread=%.6f accepted=%d cores=%d bytes=%zu units=%lu instructions=%d\n",
                   current->name, density, (double)tick_groups[i][GROUPS/2]/(32.0*rounds), i,
                   (double)medians[GROUPS/2]/(32.0*rounds), spread,
                   density != 3 && spread < .02, cores, footprint, 32*rounds, current->instructions);
        }
        if (spread >= .02 || density == 3) unstable = 1;
        fflush(stdout);
    }
    stop = 1; wait_all();
    for (int i = 0; i < cores*density; ++i)
        if (pthread_join(threads[i], NULL)) fail("pthread_join");
    if (pthread_barrier_destroy(&barrier)) fail("barrier destroy");
    policy(1);
    return unstable ? 3 : 0;
}
