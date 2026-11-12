/* Harness only: time the whole child process and bind the granted CPUs.
   Never starts a remote job; card_run supplies this process's affinity. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

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

int main(int argc, char **argv)
{
  cpu_set_t granted, selected;
  int cores[CPU_SETSIZE], packages[CPU_SETSIZE], ncores = 0, ncpus = 0;
  int cpu, i, count = 0, status;
  char affinity[CPU_SETSIZE * 6], threads[32];
  size_t used = 0;
  struct timespec start, end;
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
        ((!strcmp(argv[1], "full") || !strcmp(argv[1], "probe")) && count < 240)) {
      CPU_SET(cpu, &selected);
      used += snprintf(affinity + used, sizeof affinity - used, "%s%d", count ? " " : "", cpu);
      ++count;
    }
  }
  if (!ncores || !count || ((!strcmp(argv[1], "full") || !strcmp(argv[1], "probe")) && count != 240)) {
    fprintf(stderr, "Insufficient affinity: %d cores, %d CPUs\n", ncores, ncpus);
    return 2;
  }
  printf("CORPUS_META {\"cores\":%d,\"granted_cpus\":%d,\"threads\":%d,\"cpus\":\"%s\"}\n",
         ncores, ncpus, count, affinity);
  fflush(stdout);
  if (!strcmp(argv[1], "probe")) return 0;
  if (sched_setaffinity(0, sizeof selected, &selected)) return 2;
  snprintf(threads, sizeof threads, "%d", count);
  setenv("OMP_NUM_THREADS", threads, 1);
  setenv("OMP_DYNAMIC", "FALSE", 1);
  setenv("OMP_PROC_BIND", "TRUE", 1);
  setenv("OMP_NESTED", "FALSE", 1);
  unsetenv("OMP_PLACES");
  setenv("GOMP_CPU_AFFINITY", affinity, 1);
  setenv("LD_LIBRARY_PATH", ".", 1);
  if (clock_gettime(CLOCK_MONOTONIC, &start)) return 2;
  child = fork();
  if (child < 0) return 2;
  if (!child) {
    execl("./workload", "workload", (char *)0);
    perror("exec workload");
    _exit(127);
  }
  while (waitpid(child, &status, 0) < 0) if (errno != EINTR) return 2;
  if (clock_gettime(CLOCK_MONOTONIC, &end)) return 2;
  printf("\nCORPUS_TIME %.9f\n", end.tv_sec - start.tv_sec + (end.tv_nsec - start.tv_nsec) * 1e-9);
  if (!strcmp(argv[2], "HPCG")) reports();
  return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}
