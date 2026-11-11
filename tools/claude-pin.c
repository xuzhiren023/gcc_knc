/* S2-11: Linux sched_setaffinity(2), setrlimit(2), execve(2).
   Build statically with the donor; no card-installed runtime is required. */
#define _GNU_SOURCE
#include <errno.h>
#include <limits.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <unistd.h>

static int parse_number(const char *text, char **end, unsigned long *value) {
    if (*text < '0' || *text > '9') return 0;
    errno = 0;
    *value = strtoul(text, end, 10);
    return errno == 0;
}

int main(int argc, char **argv) {
    cpu_set_t mask;
    struct rlimit limit;
    FILE *marker;
    const char *part;
    char *end;
    unsigned long cpu, mib;
    if (argc < 4) {
        fputs("claude-pin: expected CPUs MiB program [args]\n", stderr);
        return 125;
    }
    CPU_ZERO(&mask);
    part = argv[1];
    for (;;) {
        if (!parse_number(part, &end, &cpu) || cpu >= CPU_SETSIZE ||
            (*end != ',' && *end != '\0')) {
            fputs("claude-pin: invalid logical CPU list\n", stderr);
            return 125;
        }
        CPU_SET(cpu, &mask);
        if (!*end) break;
        part = end + 1;
    }
    if (!parse_number(argv[2], &end, &mib) || *end || mib > 16384) {
        /* S9-14 (owner 2026-11-10): exclusive turns may use the 7120P's 16 GB. */
        fputs("claude-pin: memory must be 0 (no limit) or 1..16384 MiB\n", stderr);
        return 125;
    }
    if (sched_setaffinity(0, sizeof(mask), &mask) != 0) {
        perror("claude-pin: sched_setaffinity");
        return 126;
    }
    /* RLIMIT_AS bounds virtual address space, stricter than resident memory
       for a single process. The hard limit and affinity survive exec/fork. */
    limit.rlim_cur = limit.rlim_max = (rlim_t)mib * 1024 * 1024;
    /* S9-23: 0 means no limit (an exclusive turn); skip setrlimit. */
    if (mib && setrlimit(RLIMIT_AS, &limit) != 0) {
        perror("claude-pin: setrlimit RLIMIT_AS");
        return 126;
    }
    /* Only a successful exec may leave evidence that enforcement succeeded. */
    marker = fopen("claude-pinned", "w");
    if (marker == NULL) {
        perror("claude-pin: claude-pinned");
        return 126;
    }
    if (fclose(marker) != 0) {
        perror("claude-pin: claude-pinned");
        unlink("claude-pinned");
        return 126;
    }
    execv(argv[3], argv + 3);
    perror("claude-pin: execv");
    unlink("claude-pinned");
    return 127;
}
