/* S8-17 C12: card power by rail for idle, x87, saturated IMCI FMA and a memory
   stream, interleaved idle x87 fma stream fma x87 idle, each for a fixed time.
   Included by driver.c to reuse its pinning, barrier and policy helpers.
   Sensor format: m2 power.c (S6-13) and its fixture; lines 8-10 are the core,
   uncore and memory rails as power uW, current, voltage uV. */
#include <ctype.h>

enum { C12_PHASES = 7, C12_ITERS = 4096 };
static const char *const c12_order[C12_PHASES] = {"idle", "x87", "fma", "stream", "fma", "x87", "idle"};
static const char *const c12_rails[4] = {"card", "core", "uncore", "memory"};
static const char *c12_power_path = "/sys/class/micras/power";
static unsigned long c12_seconds = 20;
static size_t c12_bytes;
static int c12_kind, c12_over;
static struct { uint64_t work; char pad[56]; } c12_count[240] __attribute__((aligned(64)));
struct c12_reading { double watts[4], volts[4]; };
static struct {
    unsigned long n;
    double sum[4], min[4], max[4], volts[4];
    int error;
} c12_stats[C12_PHASES];
static pthread_mutex_t c12_mutex = PTHREAD_MUTEX_INITIALIZER;
static int c12_active = -1, c12_done;
static unsigned long c12_generation;

#ifndef CHAR_HOST
/* Register-resident bodies, no memory traffic in the x87 and FMA loops.
   x87: st0 = 1, seven independent stack registers, 28 flops per iteration.
   FMA: eight independent zmm accumulators (4-cycle latency, 4 threads per core)
   alternating +b and -b products so the values stay bounded; 32 vfmadd231ps
   per iteration, 1024 flops. Stream: read-add-write of 512 bytes per
   iteration with L1/L2 prefetch 8 and 32 lines ahead (C5's l1_8.l2_32). */
__asm__(".pushsection .text\n"
        ".p2align 6\n.globl c12_x87\n.type c12_x87, @function\nc12_x87:\n"
        "fld1\nfld1\nfld1\nfld1\nfld1\nfld1\nfld1\nfld1\n"
        ".p2align 6\n1:\n.rept 2\n"
        "fmul %st, %st(1)\nfmul %st, %st(2)\nfmul %st, %st(3)\nfmul %st, %st(4)\n"
        "fmul %st, %st(5)\nfmul %st, %st(6)\nfmul %st, %st(7)\n"
        "fadd %st, %st(1)\nfadd %st, %st(2)\nfadd %st, %st(3)\nfadd %st, %st(4)\n"
        "fadd %st, %st(5)\nfadd %st, %st(6)\nfadd %st, %st(7)\n"
        ".endr\nsubq $1, %rdi\njnz 1b\n"
        "fstp %st(0)\nfstp %st(0)\nfstp %st(0)\nfstp %st(0)\n"
        "fstp %st(0)\nfstp %st(0)\nfstp %st(0)\nfstp %st(0)\nret\n"
        ".size c12_x87, .-c12_x87\n"
        ".p2align 6\n.globl c12_fma\n.type c12_fma, @function\nc12_fma:\n"
        "vmovaps (%rsi), %zmm28\nvmovaps 64(%rsi), %zmm29\nvmovaps 128(%rsi), %zmm30\n"
        "vmovaps 192(%rsi), %zmm0\nvmovaps %zmm0, %zmm1\nvmovaps %zmm0, %zmm2\n"
        "vmovaps %zmm0, %zmm3\nvmovaps %zmm0, %zmm4\nvmovaps %zmm0, %zmm5\n"
        "vmovaps %zmm0, %zmm6\nvmovaps %zmm0, %zmm7\n"
        ".p2align 6\n1:\n.rept 2\n"
        "vfmadd231ps %zmm29, %zmm28, %zmm0\nvfmadd231ps %zmm29, %zmm28, %zmm1\n"
        "vfmadd231ps %zmm29, %zmm28, %zmm2\nvfmadd231ps %zmm29, %zmm28, %zmm3\n"
        "vfmadd231ps %zmm29, %zmm28, %zmm4\nvfmadd231ps %zmm29, %zmm28, %zmm5\n"
        "vfmadd231ps %zmm29, %zmm28, %zmm6\nvfmadd231ps %zmm29, %zmm28, %zmm7\n"
        "vfmadd231ps %zmm30, %zmm28, %zmm0\nvfmadd231ps %zmm30, %zmm28, %zmm1\n"
        "vfmadd231ps %zmm30, %zmm28, %zmm2\nvfmadd231ps %zmm30, %zmm28, %zmm3\n"
        "vfmadd231ps %zmm30, %zmm28, %zmm4\nvfmadd231ps %zmm30, %zmm28, %zmm5\n"
        "vfmadd231ps %zmm30, %zmm28, %zmm6\nvfmadd231ps %zmm30, %zmm28, %zmm7\n"
        ".endr\nsubq $1, %rdi\njnz 1b\n"
        "vmovaps %zmm0, 256(%rsi)\nret\n"
        ".size c12_fma, .-c12_fma\n"
        ".p2align 6\n.globl c12_stream\n.type c12_stream, @function\nc12_stream:\n"
        "vmovaps 64(%rdx), %zmm31\n"
        ".p2align 6\n1:\n"
        "vprefetch1 2048(%rdi)\nvprefetch1 2112(%rdi)\nvprefetch1 2176(%rdi)\nvprefetch1 2240(%rdi)\n"
        "vprefetch1 2304(%rdi)\nvprefetch1 2368(%rdi)\nvprefetch1 2432(%rdi)\nvprefetch1 2496(%rdi)\n"
        "vprefetch0 512(%rdi)\nvprefetch0 576(%rdi)\nvprefetch0 640(%rdi)\nvprefetch0 704(%rdi)\n"
        "vprefetch0 768(%rdi)\nvprefetch0 832(%rdi)\nvprefetch0 896(%rdi)\nvprefetch0 960(%rdi)\n"
        "vmovaps (%rdi), %zmm0\nvmovaps 64(%rdi), %zmm1\nvmovaps 128(%rdi), %zmm2\n"
        "vmovaps 192(%rdi), %zmm3\nvmovaps 256(%rdi), %zmm4\nvmovaps 320(%rdi), %zmm5\n"
        "vmovaps 384(%rdi), %zmm6\nvmovaps 448(%rdi), %zmm7\n"
        "vaddps %zmm31, %zmm0, %zmm0\nvaddps %zmm31, %zmm1, %zmm1\nvaddps %zmm31, %zmm2, %zmm2\n"
        "vaddps %zmm31, %zmm3, %zmm3\nvaddps %zmm31, %zmm4, %zmm4\nvaddps %zmm31, %zmm5, %zmm5\n"
        "vaddps %zmm31, %zmm6, %zmm6\nvaddps %zmm31, %zmm7, %zmm7\n"
        "vmovaps %zmm0, (%rdi)\nvmovaps %zmm1, 64(%rdi)\nvmovaps %zmm2, 128(%rdi)\n"
        "vmovaps %zmm3, 192(%rdi)\nvmovaps %zmm4, 256(%rdi)\nvmovaps %zmm5, 320(%rdi)\n"
        "vmovaps %zmm6, 384(%rdi)\nvmovaps %zmm7, 448(%rdi)\n"
        "addq $512, %rdi\nsubq $512, %rsi\njnz 1b\nret\n"
        ".size c12_stream, .-c12_stream\n"
        ".popsection\n");
void c12_x87(unsigned long iterations);
void c12_fma(unsigned long iterations, float *constants);
void c12_stream(void *buffer, unsigned long bytes, const float *constants);
/* a, +b, -b, initial accumulator, result slot; 16 lanes each. */
static float c12_constants[5*16] __attribute__((aligned(64)));
#endif

/* Work done by one call: flops for x87 and FMA, bytes read plus written for stream. */
static uint64_t c12_run(int kind, unsigned char *memory) {
#ifdef CHAR_HOST
    (void)kind; (void)memory;
    return 0;
#else
    if (kind == 1) { c12_x87(C12_ITERS); return 28ULL*C12_ITERS; }
    if (kind == 2) { c12_fma(C12_ITERS, c12_constants); return 1024ULL*C12_ITERS; }
    c12_stream(memory, c12_bytes, c12_constants);
    return 2ULL*c12_bytes;
#endif
}
static int c12_kind_of(const char *name) {
    return !strcmp(name, "x87") ? 1 : !strcmp(name, "fma") ? 2 : !strcmp(name, "stream") ? 3 : 0;
}

/* Copy of m2 power_parse's strict field rule: digits, at most 1e9, then space or end. */
static int c12_field(const char **p, unsigned long long *value) {
    char *end;
    while (**p == ' ' || **p == '\t') ++*p;
    if (!isdigit((unsigned char)**p)) return 0;
    errno = 0;
    *value = strtoull(*p, &end, 10);
    if (errno || *value > 1000000000ULL) return 0;
    *p = end;
    return **p == ' ' || **p == '\t' || **p == '\n' || **p == '\r';
}
/* Line 1: whole card, window 0. Lines 2-7 must be present. Lines 8-10: rails. */
static int c12_parse(FILE *file, struct c12_reading *r) {
    char line[256];
    for (int n = 1; n <= 10; ++n) {
        unsigned long long v[3];
        const char *p = line;
        if (!fgets(line, sizeof(line), file) || !strchr(line, '\n')) return 0;
        if (n > 1 && n < 8) continue;
        for (int i = 0; i < (n == 1 ? 1 : 3); ++i)
            if (!c12_field(&p, &v[i])) return 0;
        while (isspace((unsigned char)*p)) ++p;
        if (*p) return 0;
        if (n == 1) r->watts[0] = v[0] / 1e6;
        else { r->watts[n-7] = v[0] / 1e6; r->volts[n-7] = v[2] / 1e6; }
    }
    return 1;
}
static int c12_read(struct c12_reading *r) {
    FILE *f = fopen(c12_power_path, "r");
    if (!f) return errno ? errno : EIO;
    int ok = c12_parse(f, r);
    fclose(f);
    return ok ? 0 : EPROTO;
}
static void c12_raw(const char *kind, const char *path) {
    char line[256];
    unsigned n = 0;
    FILE *f = fopen(path, "r");
    if (!f) { printf("%s_raw path=%s unavailable errno=%d\n", kind, path, errno); return; }
    while (fgets(line, sizeof(line), f)) {
        line[strcspn(line, "\r\n")] = 0;
        printf("%s_raw path=%s line=%u value=%s\n", kind, path, ++n, line);
    }
    fclose(f);
}
/* First line of a sysfs file as one token: spaces become commas. */
static void c12_first_line(const char *path, char *out, size_t size) {
    FILE *f = fopen(path, "r");
    if (!f) { snprintf(out, size, "unavailable"); return; }
    if (!fgets(out, size, f)) snprintf(out, size, "unreadable");
    fclose(f);
    out[strcspn(out, "\r\n")] = 0;
    for (char *p = out; *p; ++p) if (isspace((unsigned char)*p)) *p = ',';
    if (!*out) snprintf(out, size, "empty");
}

/* Unpinned, as S6-13 round 2. Reads every 50 ms; a read that crosses a phase
   change is discarded. Main activates a phase only after its first second. */
static void *c12_sampler(void *unused) {
    struct timespec next;
    (void)unused;
    if (clock_gettime(CLOCK_MONOTONIC, &next)) fail("sampler clock");
    for (;;) {
        struct timespec t;
        next.tv_nsec += 50000000;
        if (next.tv_nsec >= 1000000000) { ++next.tv_sec; next.tv_nsec -= 1000000000; }
        while (clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next, NULL) == EINTR) {}
        if (!clock_gettime(CLOCK_MONOTONIC, &t) &&
            (t.tv_sec > next.tv_sec + 1)) next = t;
        pthread_mutex_lock(&c12_mutex);
        int phase = c12_active, done = c12_done;
        unsigned long generation = c12_generation;
        pthread_mutex_unlock(&c12_mutex);
        if (done) break;
        if (phase < 0) continue;
        struct c12_reading r;
        int error = c12_read(&r);
        pthread_mutex_lock(&c12_mutex);
        if (c12_active == phase && c12_generation == generation) {
            if (error) c12_stats[phase].error = error;
            else {
                for (int k = 0; k < 4; ++k) {
                    if (!c12_stats[phase].n || r.watts[k] < c12_stats[phase].min[k]) c12_stats[phase].min[k] = r.watts[k];
                    if (!c12_stats[phase].n || r.watts[k] > c12_stats[phase].max[k]) c12_stats[phase].max[k] = r.watts[k];
                    c12_stats[phase].sum[k] += r.watts[k];
                    c12_stats[phase].volts[k] += r.volts[k];
                }
                ++c12_stats[phase].n;
            }
        }
        pthread_mutex_unlock(&c12_mutex);
    }
    return NULL;
}
static void c12_activate(int phase) {
    pthread_mutex_lock(&c12_mutex);
    c12_active = phase; ++c12_generation;
    pthread_mutex_unlock(&c12_mutex);
}
static void c12_sleep_until(uint64_t target) {
    for (uint64_t t = now(); t < target; t = now()) {
        uint64_t left = target - t;
        struct timespec d = {(time_t)(left / 1000000000ULL), (long)(left % 1000000000ULL)};
        nanosleep(&d, NULL);
    }
}
static uint64_t c12_total(void) {
    uint64_t total = 0;
    for (int i = 0; i < cores*density; ++i) total += __atomic_load_n(&c12_count[i].work, __ATOMIC_RELAXED);
    return total;
}
static void *c12_worker(void *arg) {
    struct worker *w = arg;
    if (w->cpu >= 0) pin(w->cpu);
    /* Pinned first touch of the stream buffer; main allocated it. */
    for (size_t i = 0; i < c12_bytes/sizeof(float); ++i) ((float *)w->memory)[i] = .25f;
    for (;;) {
        wait_all();
        if (stop) break;
        uint64_t work = 0;
        /* Idle phase: straight back to the barrier, asleep until the phase ends. */
        if (c12_kind)
            while (!__atomic_load_n(&c12_over, __ATOMIC_RELAXED)) {
                work += c12_run(c12_kind, w->memory);
                __atomic_store_n(&c12_count[w->id].work, work, __ATOMIC_RELAXED);
            }
        wait_all();
    }
    return NULL;
}
static void c12_report(int p, uint64_t window_ns, uint64_t ops, const char *freq, const char *temp) {
    static const char *const units[] = {"none", "gflop_per_s", "gflop_per_s", "gbyte_per_s"};
    static const char *const op[] = {"none", "flop", "flop", "byte"};
    int kind = c12_kind_of(c12_order[p]);
    unsigned long n = c12_stats[p].n;
    int error = c12_stats[p].error ? c12_stats[p].error : n ? 0 : ENODATA;
    printf("phase index=%d name=%s seconds=%lu samples=%lu", p, c12_order[p], c12_seconds, n);
    for (int k = 0; k < 4; ++k) {
        if (error) printf(" %s_mean_watts=unavailable %s_min_watts=unavailable %s_max_watts=unavailable",
                          c12_rails[k], c12_rails[k], c12_rails[k]);
        else printf(" %s_mean_watts=%.6f %s_min_watts=%.6f %s_max_watts=%.6f",
                    c12_rails[k], c12_stats[p].sum[k]/n, c12_rails[k], c12_stats[p].min[k],
                    c12_rails[k], c12_stats[p].max[k]);
        if (k && error) printf(" %s_mean_volts=unavailable", c12_rails[k]);
        else if (k) printf(" %s_mean_volts=%.6f", c12_rails[k], c12_stats[p].volts[k]/n);
    }
    char energy[64] = "na";
    if (!error && ops) snprintf(energy, sizeof(energy), "%.6e", c12_stats[p].sum[0]/n * window_ns*1e-9 / ops);
    printf(" work=%.6f work_unit=%s joules_per_op=%s op=%s window_ns=%llu ops=%llu freq_khz=%s temp=%s errno=%d\n",
           window_ns ? (double)ops/window_ns : 0.0, units[kind], energy, op[kind],
           (unsigned long long)window_ns, (unsigned long long)ops, freq, temp, error);
    fflush(stdout);
}

static int c12_main(int argc, char **argv) {
    static const char freq_path[] = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq";
    static const char temp_path[] = "/sys/class/micras/temp";
    int dry = 0, native = 0, failed = 0;
    pthread_t threads[240], sampler;
    for (int i = 1; i < argc; ++i) {
        if (!strcmp(argv[i], "--dry-run")) dry = 1;
        else if (!strcmp(argv[i], "--native")) native = 1;
        else if ((!strcmp(argv[i], "--threads") || !strcmp(argv[i], "--cores") ||
                  !strcmp(argv[i], "--check") || !strcmp(argv[i], "--phase-seconds") ||
                  !strcmp(argv[i], "--power-file")) && i+1 < argc) {
            const char *option = argv[i++], *value = argv[i];
            if (!strcmp(option, "--threads")) density = (int)number(value, 4);
            else if (!strcmp(option, "--cores")) cores = (int)number(value, 60);
            else if (!strcmp(option, "--phase-seconds")) c12_seconds = number(value, 3600);
            else if (!strcmp(option, "--power-file")) c12_power_path = value;
            else if (strcmp(value, "c12")) fail("--check c12 takes no other check");
        } else fail("usage: --dry-run|--native --check c12 [--threads 1,2,4] [--cores 1..60] [--phase-seconds 2..3600] [--power-file PATH]");
    }
    if (dry == native) fail("choose exactly one execution mode");
    if (density == 3) fail("S8 excludes density 3");
    if (c12_seconds < 2) fail("--phase-seconds must exceed the dropped first second");
#ifdef CHAR_HOST
    if (native) fail("host executable supports --dry-run only");
#else
    for (int i = 0; i < 16; ++i) {
        c12_constants[i] = 1.f + i/64.f;
        c12_constants[16+i] = 1.f/3;
        c12_constants[32+i] = -1.f/3;
        c12_constants[48+i] = 1.f;
    }
#endif
    if (native) { topology_read(); policy(0); }
    printf("power_source path=%s fields=total_window0,core,uncore,memory units=uW,uV interval_ms=50 cpu=unpinned drop_ms=1000\n",
           c12_power_path);
    c12_raw("power", c12_power_path);
    c12_raw("temp", temp_path);
    struct c12_reading first;
    int error = c12_read(&first);
    if (error == EPROTO) fail("malformed power sensor file");
    if (error) { errno = error; fail("power sensor unavailable"); }
    /* S8-01 C1 sizing: 16 MiB per core divided among siblings. */
    c12_bytes = 16*1024*1024 / density;
    if (pthread_barrier_init(&barrier, NULL, cores*density+1)) fail("barrier init");
    pthread_attr_t attr;
    if (pthread_attr_init(&attr) || pthread_attr_setstacksize(&attr, 256 * 1024)) fail("thread attributes");
    for (int i = 0; i < cores*density; ++i) {
        if (posix_memalign(&workers[i].allocation, 4096, c12_bytes)) fail("allocation");
        workers[i].memory = workers[i].allocation;
        workers[i].id = i;
        workers[i].cpu = native ? topology[i/density][i%density] : -1;
        if (native) printf("pin %d %d\n", i, workers[i].cpu);
    }
    if (pthread_create(&sampler, &attr, c12_sampler, NULL)) fail("sampler pthread_create");
    for (int i = 0; i < cores*density; ++i)
        if (pthread_create(&threads[i], &attr, c12_worker, &workers[i])) fail("pthread_create");
    for (int p = 0; p < C12_PHASES; ++p) {
        char freq[128], temp[256];
        for (int i = 0; i < cores*density; ++i) __atomic_store_n(&c12_count[i].work, 0, __ATOMIC_RELAXED);
        c12_kind = c12_kind_of(c12_order[p]);
        __atomic_store_n(&c12_over, 0, __ATOMIC_RELAXED);
        wait_all();
        uint64_t start = now();
        c12_sleep_until(start + 1000000000ULL);
        uint64_t t0 = now(), w0 = c12_total();
        c12_activate(p);
        c12_sleep_until(start + c12_seconds*1000000000ULL);
        uint64_t t1 = now(), w1 = c12_total();
        c12_activate(-1);
        c12_first_line(freq_path, freq, sizeof(freq));
        c12_first_line(temp_path, temp, sizeof(temp));
        __atomic_store_n(&c12_over, 1, __ATOMIC_RELAXED);
        wait_all();
        c12_report(p, t1 - t0, w1 - w0, freq, temp);
        failed |= c12_stats[p].error || !c12_stats[p].n;
    }
    stop = 1; wait_all();
    for (int i = 0; i < cores*density; ++i)
        if (pthread_join(threads[i], NULL)) fail("pthread_join");
    pthread_mutex_lock(&c12_mutex);
    c12_done = 1;
    pthread_mutex_unlock(&c12_mutex);
    if (pthread_join(sampler, NULL)) fail("sampler pthread_join");
    for (int i = 0; i < cores*density; ++i) free(workers[i].allocation);
    if (native) policy(1);
    return failed ? 3 : 0;
}
