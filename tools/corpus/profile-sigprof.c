/* S11-15: bounded, serial-only diagnostic PC sampling. No corpus edits. */
#define _GNU_SOURCE
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <sys/time.h>
#include <time.h>
#include <ucontext.h>
#include <unistd.h>

#define CAPACITY 20000
static volatile uintptr_t pcs[CAPACITY];
static volatile sig_atomic_t used, overflow;
static struct timespec start_wall;
static struct rusage start_usage;

static void blocked(const char *reason)
{
  fprintf(stderr, "PROFILE_BLOCKED %s\n", reason);
  _exit(3);
}

static void sample(int signal_number, siginfo_t *info, void *context)
{
  sig_atomic_t n = used;
  (void)signal_number;
  (void)info;
  if (n == CAPACITY) { overflow = 1; return; }
  pcs[n] = (uintptr_t)((ucontext_t *)context)->uc_mcontext.gregs[REG_RIP];
  used = n + 1;
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
  int i;
  sigemptyset(&signals);
  sigaddset(&signals, SIGPROF);
  if (sigprocmask(SIG_BLOCK, &signals, NULL) ||
      setitimer(ITIMER_PROF, &timer, NULL) ||
      clock_gettime(CLOCK_MONOTONIC_RAW, &end_wall) ||
      getrusage(RUSAGE_SELF, &end_usage)) blocked("stop SIGPROF");
  fprintf(stderr, "PROFILE_ACCOUNT wall=%.9f user=%.9f system=%.9f interval_us=10000 samples=%d overflow=%d\n",
          end_wall.tv_sec - start_wall.tv_sec +
          (end_wall.tv_nsec - start_wall.tv_nsec) * 1e-9,
          seconds(end_usage.ru_utime) - seconds(start_usage.ru_utime),
          seconds(end_usage.ru_stime) - seconds(start_usage.ru_stime),
          (int)used, (int)overflow);
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
  for (i = 0; i < used; ++i)
    fprintf(stderr, "PROFILE_PC %lx\n", (unsigned long)pcs[i]);
  fputs("PROFILE_SAMPLES_END\n", stderr);
  if (overflow || !used) blocked("overflow or no samples");
  fputs("PROFILE_SAMPLER_COMPLETE\n", stderr);
  if (fflush(stderr)) _exit(3);
}
