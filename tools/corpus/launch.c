/* Harness only: time the child from launch to exit and bind granted CPUs.
   Never starts a remote job; card_run supplies this process's affinity. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <sched.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#include <gnu/libc-version.h>
#include "timing.h"

static int topology(int cpu, const char *field)
{
  char path[160];
  int value;
  FILE *f;
  snprintf(path, sizeof path, "/sys/devices/system/cpu/cpu%d/topology/%s", cpu, field);
  f = fopen(path, "r");
  if (!f || fscanf(f, "%d", &value) != 1) {
    fprintf(stderr, "Cannot read topology for CPU %d\n", cpu);
    exit(2);
  }
  fclose(f);
  return value;
}

static void reports(void)
{
  DIR *d = opendir(".");
  struct dirent *entry;
  if (!d) return;
  while ((entry = readdir(d))) {
    size_t n = strlen(entry->d_name);
    if (n > 5 && (!strcmp(entry->d_name + n - 5, ".yaml") ||
                 !strcmp(entry->d_name + n - 4, ".txt"))) {
      FILE *f = fopen(entry->d_name, "r");
      char buffer[4096];
      size_t got;
      if (!f) continue;
      printf("\nCORPUS_REPORT %s\n", entry->d_name);
      while ((got = fread(buffer, 1, sizeof buffer, f)))
        fwrite(buffer, 1, got, stdout);
      fclose(f);
    }
  }
  closedir(d);
}

/* A separate copy leaves the normal cross-decoding input intact. */
static int corrupt_stream(void)
{
  FILE *input = fopen("packed.bin", "rb"), *output;
  unsigned char buffer[4096];
  size_t got;
  int first = 1, failed;
  if (!input) return 2;
  output = fopen("corrupt.bin", "wb");
  if (!output) { fclose(input); return 2; }
  while ((got = fread(buffer, 1, sizeof buffer, input))) {
    if (first) { buffer[0] ^= 1; first = 0; }
    if (fwrite(buffer, 1, got, output) != got) break;
  }
  failed = first || ferror(input) || ferror(output);
  if (fclose(input)) failed = 1;
  if (fclose(output)) failed = 1;
  return failed ? 2 : 0;
}

/* Convert materialized doubles only after launch-to-exit has been recorded. */
static int arrays(void)
{
  FILE *input = fopen("arrays.bin", "rb");
  char name[80];
  uint64_t count, i;
  size_t got;
  if (!input) return 2;
  while ((got = fread(name, 1, sizeof name, input))) {
    if (got != sizeof name || !memchr(name, 0, sizeof name) || !name[0] ||
        strspn(name, "_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") != strlen(name) ||
        fread(&count, sizeof count, 1, input) != 1 || !count) { fclose(input); return 2; }
    printf("CORPUS_ARRAY {\"array\":\"%s\",\"values\":[", name);
    for (i = 0; i < count; ++i) {
      double value;
      if (fread(&value, sizeof value, 1, input) != 1) { fclose(input); return 2; }
      printf("%s%.17g", i ? "," : "", value);
    }
    puts("]}");
  }
  i = ferror(input);
  fclose(input);
  return i || ferror(stdout) ? 2 : 0;
}

int main(int argc, char **argv)
{
  cpu_set_t granted, selected;
  int cores[CPU_SETSIZE], packages[CPU_SETSIZE], percore[CPU_SETSIZE] = {0}, ncores = 0, ncpus = 0;
  int cpu, i, count = 0, status;
  char affinity[CPU_SETSIZE * 6], threads[32];
  size_t used = 0;
  pid_t child;
  if (argc != 3 || sched_getaffinity(0, sizeof granted, &granted)) return 2;
  CPU_ZERO(&selected);
  for (cpu = 0; cpu < CPU_SETSIZE; ++cpu) {
    int core, package, first;
    if (!CPU_ISSET(cpu, &granted)) continue;
    ++ncpus;
    core = topology(cpu, "core_id");
    package = topology(cpu, "physical_package_id");
    for (i = 0; i < ncores; ++i)
      if (cores[i] == core && packages[i] == package) break;
    first = i == ncores;
    if (first) {
      cores[ncores] = core;
      packages[ncores++] = package;
    }
    if ((!strcmp(argv[1], "serial") && !count) ||
        (!strcmp(argv[1], "one") && first) ||
        (!strcmp(argv[1], "two") && percore[i] < 2) ||
        !strcmp(argv[1], "full") || !strcmp(argv[1], "probe")) {
      CPU_SET(cpu, &selected);
      used += snprintf(affinity + used, sizeof affinity - used, "%s%d", count ? " " : "", cpu);
      ++count;
    }
    ++percore[i];
  }
  if (!ncores || !count || ncpus != 4 * ncores ||
      (!strcmp(argv[1], "one") && count != ncores) ||
      (!strcmp(argv[1], "two") && count != 2 * ncores)) {
    fprintf(stderr, "Insufficient affinity: %d cores, %d CPUs\n", ncores, ncpus);
    return 2;
  }
  printf("CORPUS_META {\"cores\":%d,\"granted_cpus\":%d,\"threads\":%d,\"cpus\":\"%s\"}\n",
         ncores, ncpus, count, affinity);
  fflush(stdout);
  if (!strcmp(argv[1], "probe")) return 0;
  printf("CORPUS_RUNTIME glibc %s\n", gnu_get_libc_version());
  if (sched_setaffinity(0, sizeof selected, &selected)) return 2;
  snprintf(threads, sizeof threads, "%d", count);
  setenv("OMP_NUM_THREADS", threads, 1);
  setenv("OMP_DYNAMIC", "FALSE", 1);
  setenv("OMP_PROC_BIND", "TRUE", 1);
  setenv("OMP_NESTED", "FALSE", 1);
  unsetenv("OMP_PLACES");
  setenv("GOMP_CPU_AFFINITY", affinity, 1);
  setenv("LD_LIBRARY_PATH", ".", 1);
  if ((!strcmp(argv[2], "zlib") || !strcmp(argv[2], "bzip2")) &&
      system("mkdir -p peer && tar -xf peer.tar -C peer")) return 2;
  fflush(stdout);
  if (corpus_timed_workload(&status)) return 2;
  if (!strncmp(argv[2], "PB-", 3) && arrays()) return 2;
  if (!strcmp(argv[2], "HPCG")) reports();
  if ((!strcmp(argv[2], "zlib") || !strcmp(argv[2], "bzip2")) &&
      WIFEXITED(status) && WEXITSTATUS(status) == 0) {
    for (i = 0; i < 2; ++i) {
      if (i && corrupt_stream()) return 2;
      fflush(stdout);
      child = fork();
      if (child < 0) return 2;
      if (!child) {
        setenv("LD_LIBRARY_PATH", "peer", 1);
        execl("./peer/workload", "workload", i ? "control" : "decode", (char *)0);
        _exit(127);
      }
      while (waitpid(child, &status, 0) < 0) if (errno != EINTR) return 2;
      if (!WIFEXITED(status) || WEXITSTATUS(status)) break;
    }
  }
  return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}
