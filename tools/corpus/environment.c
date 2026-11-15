/* Linux runtime observations, emitted inside each fresh process. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sched.h>

static void value(const char *label, const char *path) {
  FILE *f = fopen(path,"r");
  char line[256];
  printf("CORPUS_ENV %s ",label);
  if (!f || !fgets(line,sizeof line,f)) puts("unavailable");
  else { line[strcspn(line,"\r\n")]=0; puts(line); }
  if (f) fclose(f);
}
void corpus_environment(const char *phase) {
  const char *names[] = {"MALLOC_ARENA_MAX","MALLOC_MMAP_THRESHOLD_","MALLOC_TRIM_THRESHOLD_",
    "LD_LIBRARY_PATH","LD_PRELOAD","OMP_NUM_THREADS","OMP_DYNAMIC","OMP_PROC_BIND","GOMP_CPU_AFFINITY"};
  FILE *f;
  char line[1024];
  cpu_set_t affinity;
  int i;
  printf("CORPUS_ENV_BEGIN %s\n",phase);
  value("governor","/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor");
  value("minimum_frequency","/sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq");
  value("maximum_frequency","/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq");
  value("boost","/sys/devices/system/cpu/cpufreq/boost");
  value("clocksource","/sys/devices/system/clocksource/clocksource0/current_clocksource");
  value("transparent_hugepage","/sys/kernel/mm/transparent_hugepage/enabled");
  for (i=0; i<(int)(sizeof names/sizeof names[0]); ++i)
    printf("CORPUS_ENV %s %s\n",names[i],getenv(names[i]) ? getenv(names[i]) : "unset");
  if (sched_getaffinity(0,sizeof affinity,&affinity)) puts("CORPUS_ENV affinity unavailable");
  else {
    printf("CORPUS_ENV affinity");
    for (i=0; i<CPU_SETSIZE; ++i) if (CPU_ISSET(i,&affinity)) printf(" %d",i);
    puts("");
  }
  f=fopen("/proc/self/smaps","r");
  if (!f) puts("CORPUS_ENV pages unavailable");
  else {
    while (fgets(line,sizeof line,f))
      if (!strncmp(line,"KernelPageSize:",15) || !strncmp(line,"MMUPageSize:",12) ||
          !strncmp(line,"AnonHugePages:",14)) printf("CORPUS_ENV pages %s",line);
    fclose(f);
  }
  f=fopen("/proc/self/maps","r");
  if (!f) puts("CORPUS_ENV linked unavailable");
  else {
    while (fgets(line,sizeof line,f)) if (strchr(line,'/')) printf("CORPUS_ENV linked %s",line);
    fclose(f);
  }
  printf("CORPUS_ENV_END %s\n",phase);
}
static void __attribute__((constructor)) begin(void) { corpus_environment("start"); }
static void __attribute__((destructor)) end(void) { corpus_environment("end"); }
