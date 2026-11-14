/* S11-15: bounded process CPU sampling. No corpus edits. */
#define _GNU_SOURCE
#include <signal.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <sys/time.h>
#include <sys/syscall.h>
#include <time.h>
#include <ucontext.h>
#include <unistd.h>

#define CAPACITY 4000000u
#define STOPPED (1u << 31)
/* 600 seconds * 60 workers / 10 ms, with headroom. BSS, not a stack buffer. */
static uintptr_t pcs[CAPACITY];
static int tids[CAPACITY];
static unsigned used, active;
_Static_assert(__atomic_always_lock_free(sizeof(unsigned), 0),
               "signal handler needs lock-free counters");
static struct timespec start_wall;
static struct rusage start_usage;

static void blocked(const char *reason)
{
  fprintf(stderr, "PROFILE_BLOCKED %s\n", reason);
  _exit(3);
}

static void sample(int signal_number, siginfo_t *info, void *context)
{
  unsigned n, state;
  (void)signal_number;
  (void)info;
  /* SIGPROF masks only the receiving thread; workers can enter concurrently. */
  state = __atomic_fetch_add(&active, 1, __ATOMIC_ACQUIRE);
  if (!(state & STOPPED)) {
    n = __atomic_fetch_add(&used, 1, __ATOMIC_RELAXED);
    if (n < CAPACITY) {
      pcs[n] = (uintptr_t)((ucontext_t *)context)->uc_mcontext.gregs[REG_RIP];
      tids[n] = (int)syscall(SYS_gettid);
    }
  }
  __atomic_fetch_sub(&active, 1, __ATOMIC_RELEASE);
}

__attribute__((constructor)) static void begin(void)
{
  struct sigaction action = {0}, previous;
  struct itimerval timer = {{0, 10000}, {0, 10000}}, previous_timer;
  if (sigaction(SIGPROF, NULL, &previous) ||
      getitimer(ITIMER_PROF, &previous_timer)) blocked("inspect signal/timer");
  if (previous.sa_handler != SIG_DFL || previous_timer.it_value.tv_sec ||
      previous_timer.it_value.tv_usec) blocked("SIGPROF already in use");
  action.sa_sigaction = sample;
  action.sa_flags = SA_SIGINFO | SA_RESTART;
  sigemptyset(&action.sa_mask);
  if (sigaction(SIGPROF, &action, NULL) ||
      clock_gettime(CLOCK_MONOTONIC_RAW, &start_wall) ||
      getrusage(RUSAGE_SELF, &start_usage) ||
      setitimer(ITIMER_PROF, &timer, NULL)) blocked("start SIGPROF");
}

static double seconds(struct timeval value)
{
  return value.tv_sec + value.tv_usec * 1e-6;
}

__attribute__((destructor)) static void finish(void)
{
  struct itimerval timer = {{0, 0}, {0, 0}};
  struct timespec end_wall;
  struct rusage end_usage;
  sigset_t signals;
  FILE *maps;
  char line[1024];
  unsigned bytes = 0;
  unsigned i, count;
  sigemptyset(&signals);
  sigaddset(&signals, SIGPROF);
  if (sigprocmask(SIG_BLOCK, &signals, NULL) ||
      setitimer(ITIMER_PROF, &timer, NULL)) blocked("stop SIGPROF");
  __atomic_fetch_or(&active, STOPPED, __ATOMIC_ACQ_REL);
  while (__atomic_load_n(&active, __ATOMIC_ACQUIRE) != STOPPED) sched_yield();
  count = __atomic_load_n(&used, __ATOMIC_RELAXED);
  if (
      clock_gettime(CLOCK_MONOTONIC_RAW, &end_wall) ||
      getrusage(RUSAGE_SELF, &end_usage)) blocked("stop SIGPROF");
  fprintf(stderr, "PROFILE_ACCOUNT wall=%.9f user=%.9f system=%.9f interval_us=10000 samples=%d overflow=%d\n",
          end_wall.tv_sec - start_wall.tv_sec +
          (end_wall.tv_nsec - start_wall.tv_nsec) * 1e-9,
          seconds(end_usage.ru_utime) - seconds(start_usage.ru_utime),
          seconds(end_usage.ru_stime) - seconds(start_usage.ru_stime),
          (int)count, count > CAPACITY);
  maps = fopen("/proc/self/maps", "r");
  if (!maps) blocked("no process maps");
  fputs("PROFILE_MAPS_BEGIN\n", stderr);
  while (fgets(line, sizeof line, maps)) {
    unsigned n = 0;
    while (line[n]) ++n;
    bytes += n;
    if (bytes > 65536 || !n || line[n - 1] != '\n') blocked("oversized maps");
    fputs(line, stderr);
  }
  if (ferror(maps)) blocked("read maps");
  fclose(maps);
  fputs("PROFILE_MAPS_END\nPROFILE_SAMPLES_BEGIN\n", stderr);
  for (i = 0; i < count && i < CAPACITY; ++i)
    fprintf(stderr, "PROFILE_PC %lx tid=%d\n", (unsigned long)pcs[i], tids[i]);
  fputs("PROFILE_SAMPLES_END\n", stderr);
  if (count > CAPACITY || !count) blocked("overflow or no samples");
  fputs("PROFILE_SAMPLER_COMPLETE\n", stderr);
  if (fflush(stderr)) _exit(3);
}
