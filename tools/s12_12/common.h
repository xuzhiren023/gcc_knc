/* S12-12: original bounded diagnostics; Linux public interfaces only. */
#define _GNU_SOURCE
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sched.h>
#include <time.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <pthread.h>
#include <glob.h>

static volatile uint64_t sink;
static void require(int ok, const char *what) {
    if (!ok) { fprintf(stderr, "FAIL %s errno=%d %s\n", what, errno, strerror(errno)); exit(1); }
}
static double now(void) {
    struct timespec t;
    require(clock_gettime(CLOCK_MONOTONIC_RAW, &t) == 0, "clock monotonic raw");
    return t.tv_sec + t.tv_nsec * 1e-9;
}
static void dump(const char *path) {
    char buf[1024]; FILE *f = fopen(path, "r");
    printf("BEGIN %s\n", path);
    if (!f) printf("UNAVAILABLE errno=%d %s\n", errno, strerror(errno));
    else { while (fgets(buf, sizeof buf, f)) fputs(buf, stdout); fclose(f); }
    printf("END %s\n", path);
}
static void globdump(const char *pattern) {
    glob_t g;
    if (glob(pattern, 0, NULL, &g)) printf("UNAVAILABLE path=%s\n", pattern);
    else { for (size_t i=0;i<g.gl_pathc;i++) dump(g.gl_pathv[i]); globfree(&g); }
}
static int cpus[CPU_SETSIZE], ncpu;
static void affinity(void) {
    cpu_set_t s; require(!sched_getaffinity(0, sizeof s, &s), "getaffinity");
    ncpu=0; printf("AFFINITY");
    for (int i=0;i<CPU_SETSIZE;i++) if (CPU_ISSET(i,&s)) { cpus[ncpu++]=i; printf(" %d",i); }
    puts(""); require(ncpu>0,"empty affinity");
}
static void pin(int cpu) {
    cpu_set_t s; CPU_ZERO(&s); CPU_SET(cpu,&s);
    require(!sched_setaffinity(0,sizeof s,&s),"pin");
}
static void snapshot(const char *phase) {
    struct rusage r; require(!getrusage(RUSAGE_SELF,&r),"rusage");
    printf("SNAPSHOT %s cpu=%d clock=CLOCK_MONOTONIC_RAW minflt=%ld majflt=%ld maxrss_kib=%ld\n",
           phase,sched_getcpu(),r.ru_minflt,r.ru_majflt,r.ru_maxrss);
    dump("/proc/self/status"); dump("/proc/self/smaps"); dump("/proc/stat");
    globdump("/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq");
    globdump("/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor");
    globdump("/sys/devices/system/cpu/cpu*/cpuidle/state*/time");
    globdump("/sys/class/micras/power");
}
static void start(const char *id, int serial) {
    setvbuf(stdout,NULL,_IOLBF,0); printf("JOB %s\n",id); affinity();
    /* card_run reserves whole cores (all cores for benchmarks); narrow locally. */
    if (serial) { pin(cpus[0]); affinity(); }
    dump("/proc/version"); dump("/proc/self/limits"); dump("/proc/meminfo");
    globdump("/sys/devices/system/cpu/cpu*/topology/thread_siblings_list");
    dump("/sys/devices/system/clocksource/clocksource0/current_clocksource");
    snapshot("before");
}
static void result(const char *id, const char *status) {
    snapshot("after"); printf("RESULT %s %s\n",id,status);
}
static void *alloc(size_t bytes) {
    void *p=mmap(NULL,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    require(p!=MAP_FAILED,"mmap"); return p;
}
