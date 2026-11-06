/* ADR-0010: RAW wall makespan, pinned first touch, five (3+21) groups.
   Only the lead may launch this binary in a card_run --benchmark window. */
#define _GNU_SOURCE
#include "kernels.h"
#include <errno.h>
#include <limits.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static int cores, density, workers, selected, launch, current_build, stopping;
static unsigned long length, repetitions = 1;
static int topology[61][4], counts[61];
static const char *working_set = "boundary";
static cpu_set_t allowed;
static pthread_barrier_t barrier;
struct worker {
  struct buffers buffers;
  uint64_t start, end, ticks;
  int cpu, id;
} __attribute__((aligned(64)));
static struct worker data[MAX_WORKERS];
static uint64_t now(void) {
  struct timespec ts;
  if (clock_gettime(CLOCK_MONOTONIC_RAW,&ts)) die("CLOCK_MONOTONIC_RAW unavailable");
  return (uint64_t)ts.tv_sec*1000000000ULL+ts.tv_nsec;
}
static uint64_t ordered_tsc(void) {
  unsigned a,b,c,d,lo,hi;
  __asm__ volatile("cpuid" : "=a"(a),"=b"(b),"=c"(c),"=d"(d) : "a"(0),"c"(0) : "memory");
  __asm__ volatile("rdtsc" : "=a"(lo),"=d"(hi) : : "memory");
  __asm__ volatile("cpuid" : "=a"(a),"=b"(b),"=c"(c),"=d"(d) : "a"(0),"c"(0) : "memory");
  return ((uint64_t)hi<<32)|lo;
}
static void sync_workers(void) {
  int rc = pthread_barrier_wait(&barrier);
  if (rc && rc != PTHREAD_BARRIER_SERIAL_THREAD) die("pthread_barrier_wait");
}
static void verify_pin(int cpu) {
  cpu_set_t actual;
  if (sched_getaffinity(0,sizeof(actual),&actual)
      || CPU_COUNT(&actual) != 1 || !CPU_ISSET(cpu,&actual)
      || sched_getcpu() != cpu) die("affinity verification");
}
static void pin(int cpu) {
  cpu_set_t mask;
  CPU_ZERO(&mask); CPU_SET(cpu,&mask);
  if (!CPU_ISSET(cpu,&allowed) || sched_setaffinity(0,sizeof(mask),&mask)) die("affinity setting");
  verify_pin(cpu);
}
static void read_topology(void) {
  FILE *f = fopen("/proc/cpuinfo","r");
  if (!f || sched_getaffinity(0,sizeof(allowed),&allowed)) die("topology/allowed mask");
  char line[2048]; int cpu = -1, core = -1;
  for (;;) {
    int end = !fgets(line,sizeof(line),f);
    if (end || line[0] == '\n') {
      if (cpu >= 0) {
        if (cpu >= CPU_SETSIZE || core < 0 || core > 60 || counts[core] == 4)
          die("unexpected topology");
        topology[core][counts[core]++] = cpu;
      }
      cpu = core = -1;
      if (end) break;
    } else if (sscanf(line,"processor : %d",&cpu) == 1) {
    } else if (sscanf(line,"core id : %d",&core) == 1) {
    }
  }
  if (ferror(f)) die("cpuinfo read");
  fclose(f);
  for (int c = 0; c < cores; ++c) {
    if (counts[c] != 4) die("expected four siblings/core");
    for (int i = 0; i < 4; ++i) for (int j = i+1; j < 4; ++j)
      if (topology[c][i] > topology[c][j]) {
        int tmp = topology[c][i]; topology[c][i] = topology[c][j]; topology[c][j] = tmp;
      }
    for (int t = 0; t < density; ++t) {
      int cpu_id = topology[c][t];
      if (cpu_id == 0 || cpu_id >= 241) die("OS core selected");
      data[c*density+t].cpu = cpu_id;
      data[c*density+t].id = c*density+t;
      printf("placement worker=%d core=%d sibling=%d cpu=%d\n",c*density+t,c,t,cpu_id);
    }
  }
}
static void policy(const char *phase) {
  static const char *paths[] = {
    "/sys/devices/system/clocksource/clocksource0/current_clocksource",
    "/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver",
    "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor",
    "/sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq",
    "/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq",
    "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"
  };
  for (unsigned i = 0; i < sizeof(paths)/sizeof(*paths); ++i) {
    FILE *f = fopen(paths[i],"r"); char value[256];
    if (!f) { printf("policy phase=%s path=%s errno=%d\n",phase,paths[i],errno); continue; }
    if (!fgets(value,sizeof(value),f)) strcpy(value,"unreadable");
    value[strcspn(value,"\r\n")] = 0;
    printf("policy phase=%s path=%s value=%s\n",phase,paths[i],value);
    fclose(f);
  }
}
static void *worker_main(void *arg) {
  struct worker *w = arg;
  pin(w->cpu);
  allocate_buffers(&w->buffers,selected,length,(unsigned)w->id);
  sync_workers();
  for (;;) {
    sync_workers();
    if (stopping) break;
    verify_pin(w->cpu);
    w->start = now();
    uint64_t t0 = ordered_tsc();
    for (unsigned long r = 0; r < repetitions; ++r)
      invoke(selected,current_build,&w->buffers,length);
    w->ticks = ordered_tsc()-t0;
    w->end = now();
    verify_pin(w->cpu);
    sync_workers();
  }
  free_buffers(&w->buffers);
  return NULL;
}
static uint64_t batch(void) {
  sync_workers(); sync_workers();
  uint64_t first = UINT64_MAX, last = 0;
  for (int w = 0; w < workers; ++w) {
    if (data[w].start < first) first = data[w].start;
    if (data[w].end > last) last = data[w].end;
  }
  return last-first;
}
static int compare(const void *aa, const void *bb) {
  uint64_t a = *(const uint64_t *)aa, b = *(const uint64_t *)bb;
  return (a>b)-(a<b);
}
static void sample(const char *phase, int group, int index, uint64_t elapsed) {
  printf("sample kernel=%s build=%s length=%lu threads_per_core=%d cores=%d "
         "cycles_per_element=%.9f repetitions=%lu wall_ns=%llu ns_per_element=%.9f "
         "phase=%s group=%d sample=%d launch=%d working_set=%s short_length=%u\n",
         kernels[selected].name,build_names[current_build],length,density,cores,
         (double)data[0].ticks/((double)length*repetitions),repetitions,
         (unsigned long long)elapsed,(double)elapsed/((double)length*workers*repetitions),
         phase,group,index,launch,working_set,short_length);
}
static unsigned long number(const char *s) {
  char *end; errno = 0;
  unsigned long value = strtoul(s,&end,10);
  if (errno || !*s || *end || *s == '-' || value > 262144) die("invalid numeric option");
  return value;
}
static size_t footprint(unsigned long n) {
  size_t nx = n+48;
  if (selected == 3) nx = ((n+WIDTH-1)/WIDTH+2)*PITCH;
  if (selected >= 5) { unsigned d = selected == 5 ? 8 : 16; nx = ((n+d-1)/d)*16+32; }
  size_t np = selected == 6 ? 256 : selected == 5 ? 128 : 16;
  return (nx+n+32+np)*kernels[selected].bytes;
}
int benchmark(int argc, char **argv) {
  selected = -1;
  for (int i = 2; i < argc; i += 2) {
    if (i+1 == argc) die("missing option value");
    const char *key = argv[i], *value = argv[i+1];
    if (!strcmp(key,"--kernel")) {
      selected = -1;
      for (int k = 0; k < 7; ++k) if (!strcmp(value,kernels[k].name)) selected = k;
    } else if (!strcmp(key,"--length")) length = number(value);
    else if (!strcmp(key,"--density")) density = number(value);
    else if (!strcmp(key,"--cores")) cores = number(value);
    else if (!strcmp(key,"--launch")) launch = number(value);
    else if (!strcmp(key,"--short-length")) short_length = number(value);
    else if (!strcmp(key,"--working-set")) working_set = value;
    else die("unknown option");
  }
  if (selected < 0 || (cores != 1 && cores != 60) || density < 1 || density > 4
      || launch < 1 || launch > 3 || short_length < 1 || short_length > 64)
    die("require kernel, cores 1|60, density 1..4, launch 1..3, short-length 1..64");
  if (strcmp(working_set,"boundary")) {
    static const unsigned l1[] = {0,1024,512,336,256}, l2[] = {0,16384,8192,5456,4096};
    size_t budget = 0;
    if (length) die("choose --length OR --working-set");
    if (!strcmp(working_set,"L1")) { length = l1[density]; budget = 12288; }
    else if (!strcmp(working_set,"L2")) { length = l2[density]; budget = 196608; }
    else if (!strcmp(working_set,"memory")) length = 262144;
    else die("working-set must be L1, L2 or memory");
    while (budget && length > 16 && footprint(length)*density > budget) length -= 16;
    if (budget && footprint(length)*density > budget) die("working set exceeds budget");
  }
  if (!length || length > 262144) die("length must be 1..262144");
  /* Every launch must pass the same full correctness gate before timing. */
  int rc = correctness();
  if (rc) return rc;
  workers = cores*density;
  policy("start"); read_topology();
  pin(topology[0][0]);
  printf("configuration kernel=%s length=%lu workers=%d bytes_per_worker=%zu "
         "bytes_per_core=%zu clock=CLOCK_MONOTONIC_RAW cycles=worker0_TSC_diagnostic "
         "density_comparable=%d\n",kernels[selected].name,length,workers,
         footprint(length),footprint(length)*density,density != 3);
  if (pthread_barrier_init(&barrier,NULL,workers+1)) die("barrier init");
  pthread_t threads[MAX_WORKERS];
  /* The card's stack limit is unlimited, so glibc's default thread stack is huge; 240 of them
     exhaust card_run's address-space limit (lead, 2026-11-06). Workers need little stack. */
  pthread_attr_t attr;
  if (pthread_attr_init(&attr) || pthread_attr_setstacksize(&attr, 256 * 1024)) die("thread attributes");
  for (int w = 0; w < workers; ++w)
    if (pthread_create(&threads[w],&attr,worker_main,&data[w])) die("pthread_create");
  pthread_attr_destroy(&attr);
  sync_workers();
  int noisy = density == 3;
  for (int order = 0; order < 3; ++order) {
    current_build = launch%2 ? order : 2-order;
    /* Grow an initial pilot to >=10 ms, then size a batch for 100 ms.
       Record even pilot/warmup samples, with their own repetition counts. */
    repetitions = 1;
    uint64_t elapsed;
    int pilot = 0;
    do {
      elapsed = batch(); sample("pilot",-1,pilot++,elapsed);
      if (elapsed >= 10000000ULL) break;
      if (repetitions > ULONG_MAX/10) die("pilot overflow");
      repetitions *= 10;
    } while (1);
    double scaled = (double)repetitions*100000000.0/elapsed;
    if (scaled >= (double)ULONG_MAX) die("repetition overflow");
    repetitions = scaled < 1 ? 1 : (unsigned long)(scaled+0.5);
    uint64_t medians[5];
    for (int g = 0; g < 5; ++g) {
      for (int r = 0; r < 3; ++r) { elapsed = batch(); sample("warmup",g,r,elapsed); }
      uint64_t samples[21];
      for (int r = 0; r < 21; ++r) { samples[r] = batch(); sample("timed",g,r,samples[r]); }
      qsort(samples,21,sizeof(*samples),compare);
      medians[g] = samples[10];
      printf("group kernel=%s build=%s group=%d min_ns=%llu median_ns=%llu max_ns=%llu\n",
             kernels[selected].name,build_names[current_build],g,
             (unsigned long long)samples[0],(unsigned long long)samples[10],
             (unsigned long long)samples[20]);
    }
    qsort(medians,5,sizeof(*medians),compare);
    double spread = (double)(medians[4]-medians[0])/medians[2];
    if (spread >= 0.02) noisy = 1;
    printf("summary kernel=%s build=%s length=%lu threads_per_core=%d cores=%d "
           "repetitions=%lu median_ns=%llu ns_per_element=%.9f group_spread=%.9f "
           "within_launch_ok=%d launch=%d working_set=%s short_length=%u\n",
           kernels[selected].name,build_names[current_build],length,density,cores,
           repetitions,(unsigned long long)medians[2],
           (double)medians[2]/((double)workers*length*repetitions),spread,
           spread < 0.02 && density != 3,launch,working_set,short_length);
  }
  stopping = 1; sync_workers();
  for (int w = 0; w < workers; ++w) if (pthread_join(threads[w],NULL)) die("pthread_join");
  if (pthread_barrier_destroy(&barrier)) die("barrier destroy");
  policy("end");
  return noisy ? 3 : 0;
}
