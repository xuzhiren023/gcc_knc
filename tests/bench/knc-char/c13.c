/* S9-16 C13: do unaligned scalar accesses fault on KNC, and what do they cost.
   GCC emits unaligned scalar moves (store merging, inline memcpy), while the
   ICC 16.0 guide asks for naturally aligned data on MIC
   (GUID-7E3E5C78-3F3B-4746-8C2D-A912EE1D6B38).  For 2-, 4- and 8-byte general
   register loads and stores and x87 fld/fst of float and double, try every
   byte offset 0-63 from a 64-byte line start, and every offset that crosses a
   4 KiB page boundary.  Each row says whether the access faulted (SIGBUS or
   SIGSEGV), whether it read or wrote the right bytes, and ticks per access
   (median of 9 runs of 8 x 4096 accesses) against offset 0.  Standalone; one
   thread, pinned to the first allowed CPU. */
#define _GNU_SOURCE
#include <sched.h>
#include <setjmp.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>

enum { RUNS = 9, ITERS = 4096, PAGE = 4096 };

static sigjmp_buf c13_env;
static volatile sig_atomic_t c13_signal;

static void c13_handler(int sig) {
    c13_signal = sig;
    siglongjmp(c13_env, 1);
}

static uint64_t ticks(void) {
    unsigned a, b, c, d, lo, hi;
    __asm__ volatile("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d) : "a"(0) : "memory");
    __asm__ volatile("rdtsc" : "=a"(lo), "=d"(hi) : : "memory");
    __asm__ volatile("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d) : "a"(0) : "memory");
    return ((uint64_t)hi << 32) | lo;
}

#define X8(s) s s s s s s s s
/* Run ITERS rounds of eight accesses at P; the asm fixes the instruction. */
static void c13_run(int op, unsigned char *p) {
    long n = ITERS;
    unsigned long v = 0x1122334455667788UL;
    switch (op) {
    case 0: __asm__ volatile("1:" X8("movw (%1), %w2\n\t") "dec %0\n\tjnz 1b"
                             : "+r"(n), "+r"(p), "+r"(v) : : "memory", "cc"); break;
    case 1: __asm__ volatile("1:" X8("movl (%1), %k2\n\t") "dec %0\n\tjnz 1b"
                             : "+r"(n), "+r"(p), "+r"(v) : : "memory", "cc"); break;
    case 2: __asm__ volatile("1:" X8("movq (%1), %2\n\t") "dec %0\n\tjnz 1b"
                             : "+r"(n), "+r"(p), "+r"(v) : : "memory", "cc"); break;
    case 3: __asm__ volatile("1:" X8("movw %w2, (%1)\n\t") "dec %0\n\tjnz 1b"
                             : "+r"(n), "+r"(p) : "r"(v) : "memory", "cc"); break;
    case 4: __asm__ volatile("1:" X8("movl %k2, (%1)\n\t") "dec %0\n\tjnz 1b"
                             : "+r"(n), "+r"(p) : "r"(v) : "memory", "cc"); break;
    case 5: __asm__ volatile("1:" X8("movq %2, (%1)\n\t") "dec %0\n\tjnz 1b"
                             : "+r"(n), "+r"(p) : "r"(v) : "memory", "cc"); break;
    case 6: __asm__ volatile("1:" X8("flds (%1)\n\tfstp %%st(0)\n\t") "dec %0\n\tjnz 1b"
                             : "+r"(n), "+r"(p) : : "memory", "cc", "st"); break;
    case 7: __asm__ volatile("1:" X8("fldl (%1)\n\tfstp %%st(0)\n\t") "dec %0\n\tjnz 1b"
                             : "+r"(n), "+r"(p) : : "memory", "cc", "st"); break;
    /* The stores write the value already there (1.5), so the check holds. */
    case 8: __asm__ volatile("flds (%1)\n\t1:" X8("fsts (%1)\n\t") "dec %0\n\tjnz 1b\n\tfstp %%st(0)"
                             : "+r"(n), "+r"(p) : : "memory", "cc", "st"); break;
    case 9: __asm__ volatile("fldl (%1)\n\t1:" X8("fstl (%1)\n\t") "dec %0\n\tjnz 1b\n\tfstp %%st(0)"
                             : "+r"(n), "+r"(p) : : "memory", "cc", "st"); break;
    }
}

/* One access at P, checked: a load must return the bytes at P, a store must
   write exactly WIDTH bytes. */
static int c13_check(int op, int width, unsigned char *p) {
    unsigned char before[24], after[24];
    memcpy(before, p - 8, sizeof(before));
    if (op < 3) {
        unsigned long v = 0, want = 0;
        if (op == 0) __asm__ volatile("movzwl (%1), %k0" : "=r"(v) : "r"(p) : "memory");
        if (op == 1) __asm__ volatile("movl (%1), %k0" : "=r"(v) : "r"(p) : "memory");
        if (op == 2) __asm__ volatile("movq (%1), %0" : "=r"(v) : "r"(p) : "memory");
        memcpy(&want, p, width);
        return v == want;
    }
    if (op < 6) {
        unsigned long v = 0xa5c3e1f00f1e3c5aUL;
        if (op == 3) __asm__ volatile("movw %w1, (%0)" : : "r"(p), "r"(v) : "memory");
        if (op == 4) __asm__ volatile("movl %k1, (%0)" : : "r"(p), "r"(v) : "memory");
        if (op == 5) __asm__ volatile("movq %1, (%0)" : : "r"(p), "r"(v) : "memory");
        memcpy(after, p - 8, sizeof(after));
        memcpy(before + 8, &v, width);
        return !memcmp(before, after, sizeof(after));
    }
    if (op < 8) {
        double d = 0;
        if (op == 6) __asm__ volatile("flds (%1)\n\tfstpl %0" : "=m"(d) : "r"(p) : "memory");
        if (op == 7) __asm__ volatile("fldl (%1)\n\tfstpl %0" : "=m"(d) : "r"(p) : "memory");
        return d == 1.5;
    }
    double d = -2.25;
    float f = -2.25f;
    if (op == 8) __asm__ volatile("flds %1\n\tfstps (%0)" : : "r"(p), "m"(f) : "memory", "st");
    if (op == 9) __asm__ volatile("fldl %1\n\tfstpl (%0)" : : "r"(p), "m"(d) : "memory", "st");
    memcpy(after, p - 8, sizeof(after));
    if (op == 8) memcpy(before + 8, &f, 4); else memcpy(before + 8, &d, 8);
    return !memcmp(before, after, sizeof(after));
}

static int c13_cmp(const void *a, const void *b) {
    uint64_t x = *(const uint64_t *)a, y = *(const uint64_t *)b;
    return x < y ? -1 : x > y;
}

static void c13_fill(int op, unsigned char *p) {
    float f = 1.5f;
    double d = 1.5;
    if (op == 6 || op == 8) memcpy(p, &f, 4);
    if (op == 7 || op == 9) memcpy(p, &d, 8);
}

/* Check and time OP at P; a fault returns through the handler with
   c13_signal set.  Kept apart from main so no local lives across sigsetjmp. */
static __attribute__((noinline)) int c13_measure(int op, int w, unsigned char *p, uint64_t *t) {
    c13_signal = 0;
    if (sigsetjmp(c13_env, 1)) return 0;
    c13_fill(op, p);
    int ok = c13_check(op, w, p);
    c13_fill(op, p);
    c13_run(op, p);
    for (int r = 0; r < RUNS; ++r) {
        uint64_t t0 = ticks();
        c13_run(op, p);
        t[r] = ticks() - t0;
    }
    return ok;
}

int main(void) {
    static const char *const names[10] = {
        "ld16", "ld32", "ld64", "st16", "st32", "st64",
        "fld32", "fld64", "fst32", "fst64"};
    static const int widths[10] = {2, 4, 8, 2, 4, 8, 4, 8, 4, 8};
    cpu_set_t allowed;
    if (!sched_getaffinity(0, sizeof(allowed), &allowed))
        for (int c = 0; c < CPU_SETSIZE; ++c)
            if (CPU_ISSET(c, &allowed)) {
                CPU_ZERO(&allowed); CPU_SET(c, &allowed);
                if (sched_setaffinity(0, sizeof(allowed), &allowed)) return 2;
                printf("pin 0 %d\n", c);
                break;
            }
    unsigned char *buf = mmap(NULL, 2*PAGE, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (buf == MAP_FAILED) return 2;
    for (int i = 0; i < 2*PAGE; ++i) buf[i] = (unsigned char)(i*7 + 3);
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = c13_handler;
    sigemptyset(&sa.sa_mask);
    if (sigaction(SIGBUS, &sa, NULL) || sigaction(SIGSEGV, &sa, NULL)) return 2;
    unsigned long eflags;
    __asm__ volatile("pushfq\n\tpopq %0" : "=r"(eflags));
    printf("c13 eflags.ac=%lu\n", (eflags >> 18) & 1);
    printf("c13 op offset fault ok ticks_per_access ratio_to_offset0\n");
    int faults = 0, wrong = 0;
    for (int op = 0; op < 10; ++op) {
        int w = widths[op];
        double base = 0;
        /* Offsets 0-63 from a line at 1 KiB, then the page crossings. */
        for (int k = 0; k < 64 + w - 1; ++k) {
            int page = k >= 64;
            unsigned char *p = page ? buf + PAGE - (w - 1) + (k - 64) : buf + 1024 + k;
            uint64_t t[RUNS];
            int ok = c13_measure(op, w, p, t);
            if (c13_signal) {
                ++faults;
                printf("c13 %s %s%d fault sig%d - - -\n", names[op], page ? "page-" : "",
                       page ? (int)(buf + PAGE - p) : k, (int)c13_signal);
                continue;
            }
            wrong += !ok;
            qsort(t, RUNS, sizeof(t[0]), c13_cmp);
            double per = (double)t[RUNS/2] / (8.0 * ITERS);
            if (k == 0) base = per;
            printf("c13 %s %s%d none %s %.3f %.3f\n", names[op], page ? "page-" : "",
                   page ? (int)(buf + PAGE - p) : k, ok ? "ok" : "WRONG", per, per / base);
        }
    }
    printf("c13 summary faults=%d wrong=%d\n", faults, wrong);
    return faults || wrong ? 1 : 0;
}
