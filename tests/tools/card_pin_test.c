/* Host-only syscall seams: no KNC executable is ever run on the host. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <sched.h>
#include <sys/resource.h>
#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <sys/stat.h>

static int affinity_calls, limit_calls, exec_calls, mode;
static unsigned long expected_mib = 128;
static int fake_affinity(pid_t pid, size_t size, const cpu_set_t *mask) {
    /* Cygwin's inspection macros take a mutable pointer, unlike glibc's. */
    cpu_set_t observed = *mask;
    assert(pid == 0 && size == sizeof(*mask));
    assert(CPU_COUNT(&observed) == 3);
    assert(CPU_ISSET(4, &observed) && CPU_ISSET(13, &observed) && CPU_ISSET(91, &observed));
    assert(!CPU_ISSET(7, &observed)); /* sample core 60's logical CPU */
    ++affinity_calls;
    if (mode == 1) { errno = EPERM; return -1; }
    return 0;
}
static int fake_limit(int resource, const struct rlimit *limit) {
    assert(affinity_calls == 1 && exec_calls == 0);
    assert(resource == RLIMIT_AS);
    assert(limit->rlim_cur == (rlim_t)expected_mib * 1024 * 1024 && limit->rlim_max == limit->rlim_cur);
    ++limit_calls;
    if (mode == 2) { errno = EPERM; return -1; }
    return 0;
}
static int fake_exec(const char *path, char *const argv[]) {
    assert(affinity_calls == 1 && limit_calls <= 1); /* S9-23: 0 MiB means no setrlimit */
    assert(access("claude-pinned", F_OK) == 0);
    assert(strcmp(path, "./claude-program") == 0);
    assert(strcmp(argv[1], "argument with spaces") == 0 && argv[2] == NULL);
    ++exec_calls;
    errno = ENOENT;
    return -1;
}
#define sched_setaffinity fake_affinity
#define setrlimit fake_limit
#define execv fake_exec
#define main pin_main
#include "../../tools/claude-pin.c"
#undef main

int main(void) {
    char *args[] = {"claude-pin", "4,13,91", "128", "./claude-program", "argument with spaces", NULL};
    for (mode = 0; mode < 3; ++mode) {
        affinity_calls = limit_calls = exec_calls = 0;
        assert(pin_main(5, args) == (mode ? 126 : 127));
        assert(affinity_calls == 1);
        assert(limit_calls == (mode != 1));
        assert(exec_calls == (mode == 0));
        /* Failed affinity, limit or exec must never claim a program ran. */
        assert(access("claude-pinned", F_OK) != 0);
    }
    mode = 3;
    affinity_calls = limit_calls = exec_calls = 0;
    assert(mkdir("claude-pinned", 0700) == 0);
    assert(pin_main(5, args) == 126);
    assert(affinity_calls == 1 && limit_calls == 1 && exec_calls == 0);
    assert(rmdir("claude-pinned") == 0);
    /* Owner, 2026-11-10 (S9-14): exclusive turns may use the 7120P's 16 GB,
       so one job may declare up to 16384 MiB and no more. */
    mode = 0;
    expected_mib = 7680;
    args[2] = "7680";
    affinity_calls = limit_calls = exec_calls = 0;
    assert(pin_main(5, args) == 127 && limit_calls == 1 && exec_calls == 1);
    expected_mib = 16384;
    args[2] = "16384";
    affinity_calls = limit_calls = exec_calls = 0;
    assert(pin_main(5, args) == 127 && limit_calls == 1 && exec_calls == 1);
    args[2] = "16385";
    affinity_calls = limit_calls = exec_calls = 0;
    assert(pin_main(5, args) == 125 && affinity_calls == 0);
    /* S9-23: 0 means no limit; setrlimit is skipped but affinity and exec still run. */
    args[2] = "0";
    affinity_calls = limit_calls = exec_calls = 0;
    assert(pin_main(5, args) == 127 && affinity_calls == 1 && limit_calls == 0 && exec_calls == 1);
    args[2] = "128";
    char *bad[] = {"", "4,,13", "-1", "9999999", "4x", "4,"};
    for (unsigned i = 0; i < sizeof(bad) / sizeof(*bad); ++i) {
        args[1] = bad[i];
        affinity_calls = 0;
        assert(pin_main(5, args) == 125 && affinity_calls == 0);
    }
    return 0;
}
