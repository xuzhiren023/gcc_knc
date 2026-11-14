/* ADR-0015: resident supervisor; transfer only after the child is reaped. */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static int corpus_transfer(const char *path, FILE *destination)
{
  FILE *input = fopen(path, "rb");
  char buffer[8192];
  size_t got;
  int failed;
  if (!input) return 2;
  while ((got = fread(buffer, 1, sizeof buffer, input)))
    if (fwrite(buffer, 1, got, destination) != got) break;
  failed = ferror(input) || ferror(destination);
  if (fclose(input)) failed = 1;
  return failed ? 2 : 0;
}

static long long corpus_ns(struct timespec t)
{
  return (long long)t.tv_sec * 1000000000LL + t.tv_nsec;
}

static int corpus_timed_workload(int *status)
{
  struct timespec start, end, utc;
  pid_t child;
  char clocksource[80] = "unavailable";
  FILE *source = fopen("/sys/devices/system/clocksource/clocksource0/current_clocksource", "r");
  FILE *out = fopen("workload.stdout", "wb"), *err = fopen("workload.stderr", "wb");
  if (source) { if (fscanf(source, "%79s", clocksource) != 1) return 2; fclose(source); }
  if (!out || !err) return 2;
  fflush(NULL);
  if (clock_gettime(CLOCK_REALTIME, &utc) ||
      clock_gettime(CLOCK_MONOTONIC_RAW, &start)) return 2;
  child = fork();
  if (child < 0) return 2;
  if (!child) {
    if (dup2(fileno(out), STDOUT_FILENO) < 0 ||
        dup2(fileno(err), STDERR_FILENO) < 0) _exit(126);
    fclose(out); fclose(err);
    execl("./workload", "workload", (char *)0);
    perror("exec workload");
    _exit(127);
  }
  while (waitpid(child, status, 0) < 0) if (errno != EINTR) return 2;
  if (clock_gettime(CLOCK_MONOTONIC_RAW, &end)) return 2;
  fclose(out); fclose(err);
  printf("\nCORPUS_TIME %.9f\n", (corpus_ns(end) - corpus_ns(start)) * 1e-9);
  printf("CORPUS_CLOCK {\"clock\":\"CLOCK_MONOTONIC_RAW\",\"boundary\":\"launch-to-exit\","
         "\"start_ns\":%lld,\"end_ns\":%lld,\"utc_start_ns\":%lld,\"clocksource\":\"%s\"}\n",
         corpus_ns(start), corpus_ns(end), corpus_ns(utc), clocksource);
  fflush(stdout);
  return corpus_transfer("workload.stdout", stdout) ||
         corpus_transfer("workload.stderr", stderr);
}
