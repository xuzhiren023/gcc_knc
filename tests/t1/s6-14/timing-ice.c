/* ADR-0010: RAW wall makespan, pinned first touch, five (3+21) groups.
   Only the lead may launch this binary in a card_run --benchmark window.
   Builds are interleaved round by round inside every group (lead, 2026-11-06,
   docs/research/m2-noise-diagnosis.md): a regime change on the card then hits
   all three builds alike, and the gain fraction is taken from same-group medians. */
#define _GNU_SOURCE
#include "kernels.h"
#include <errno.h>
#include <limits.h>
#include <math.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <time.h>

static int cores, density, workers, selected, launch, current_build, stopping;
static unsigned long length, repetitions = 1, warmup_seconds = 10;
static int topology[61][4], counts[61];
static const char *working_set = "boundary";
static cpu_set_t allowed;
static pthread_barrier_t barrier;
static uint64_t program_start;
struct worker {
  struct buffers buffers;
  uint64_t start, end, ticks;
  struct rusage before, after;
  int cpu, id;
} __attribute__((aligned(64)));
static struct worker data[MAX_WORKERS];
/* Per-batch straggler diagnostics (lead, 2026-11-06): which worker ended last and
   how long it ran, the median worker time, the wake-up skew, and whether workers
   were preempted (involuntary context switches and system time, RUSAGE_THREAD). */
static struct {
  uint64_t max_ns, median_ns, skew_ns;
  unsigned long nivcsw, nivcsw_max, stime_us;
  int max_worker, nivcsw_worker;
} last;
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
    /* Resource reads sit outside the timed window. */
    if (getrusage(RUSAGE_THREAD,&w->before)) die("getrusage");
    w->start = now();
    uint64_t t0 = ordered_tsc();
    for (unsigned long r = 0; r < repetitions; ++r)
      invoke(selected,current_build,&w->buffers,length);
    w->ticks = ordered_tsc()-t0;
    w->end = now();
    if (getrusage(RUSAGE_THREAD,&w->after)) die("getrusage");
    verify_pin(w->cpu);
    sync_workers();
  }
  free_buffers(&w->buffers);
  return NULL;
}
static int compare(const void *aa, const void *bb) {
  uint64_t a = *(const uint64_t *)aa, b = *(const uint64_t *)bb;
  return (a>b)-(a<b);
}
static unsigned long micros(struct timeval a, struct timeval b) {
  return (unsigned long)((b.tv_sec-a.tv_sec)*1000000L+(b.tv_usec-a.tv_usec));
}
static uint64_t batch(void) {
  sync_workers(); sync_workers();
  uint64_t first = UINT64_MAX, last_end = 0, last_start = 0, durations[MAX_WORKERS];
  memset(&last,0,sizeof(last));
  for (int w = 0; w < workers; ++w) {
    if (data[w].start < first) first = data[w].start;
    if (data[w].start > last_start) last_start = data[w].start;
    if (data[w].end > last_end) last_end = data[w].end;
    durations[w] = data[w].end-data[w].start;
    if (durations[w] > last.max_ns) { last.max_ns = durations[w]; last.max_worker = w; }
    unsigned long n = (unsigned long)(data[w].after.ru_nivcsw-data[w].before.ru_nivcsw);
    last.nivcsw += n;
    if (n > last.nivcsw_max) { last.nivcsw_max = n; last.nivcsw_worker = w; }
    last.stime_us += micros(data[w].before.ru_stime,data[w].after.ru_stime);
  }
  qsort(durations,workers,sizeof(*durations),compare);
  last.median_ns = durations[workers/2];
  last.skew_ns = last_start-first;
  return last_end-first;
}
static void sample(const char *phase, int group, int index, uint64_t elapsed) {
  printf("sample kernel=%s build=%s length=%lu threads_per_core=%d cores=%d "
         "cycles_per_element=%.9f repetitions=%lu wall_ns=%llu ns_per_element=%.9f "
         "phase=%s group=%d sample=%d launch=%d working_set=%s short_length=%u "
         "t_ms=%llu max_worker=%d max_ns=%llu median_ns=%llu skew_ns=%llu "
         "nivcsw=%lu nivcsw_max=%lu nivcsw_worker=%d stime_us=%lu\n",
         kernels[selected].name,build_names[current_build],length,density,cores,
         (double)data[0].ticks/((double)length*repetitions),repetitions,
         (unsigned long long)elapsed,(double)elapsed/((double)length*workers*repetitions),
         phase,group,index,launch,working_set,short_length,
         (unsigned long long)((now()-program_start)/1000000ULL),last.max_worker,
         (unsigned long long)last.max_ns,(unsigned long long)last.median_ns,
         (unsigned long long)last.skew_ns,last.nivcsw,last.nivcsw_max,last.nivcsw_worker,
         last.stime_us);
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
/* Round r of a group runs every build once; the starting build rotates with the
   round, and even launches rotate the other way (the old per-launch alternation). */
static int build_in_round(int round, int k) {
  int b = launch%2 ? (round+k)%3 : (2-(round+k)%3);
  return b;
}
static double spread_of(double *v, int n) {
  double s[5]; int m = n;
  memcpy(s,v,n*sizeof(*v));
  for (int i = 1; i < m; ++i) for (int j = i; j > 0 && s[j-1] > s[j]; --j) {
    double t = s[j]; s[j] = s[j-1]; s[j-1] = t;
  }
  return (s[m-1]-s[0])/s[m/2];
}
int benchmark(int argc, char **argv) {
  selected = -1;
  program_start = now();
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
    else if (!strcmp(key,"--warmup-seconds")) warmup_seconds = number(value);
    else die("unknown option");
  }
  if (selected < 0 || (cores != 1 && cores != 60) || density < 1 || density > 4
      || launch < 1 || launch > 5 || short_length < 1 || short_length > 64
      || warmup_seconds > 60)
    die("require kernel, cores 1|60, density 1..4, launch 1..5, short-length 1..64, "
        "warmup-seconds 0..60");
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
  printf("phase name=correctness_done t_ms=%llu\n",
         (unsigned long long)((now()-program_start)/1000000ULL));
  workers = cores*density;
  policy("start"); read_topology();
  pin(topology[0][0]);
  printf("configuration kernel=%s length=%lu workers=%d bytes_per_worker=%zu "
         "bytes_per_core=%zu clock=CLOCK_MONOTONIC_RAW cycles=worker0_TSC_diagnostic "
         "density_comparable=%d warmup_seconds=%lu interleaved=1\n",kernels[selected].name,
         length,workers,footprint(length),footprint(length)*density,density != 3,
         warmup_seconds);
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
  unsigned long reps[3];
  uint64_t elapsed;
  /* Size every build first: grow a pilot to >=10 ms, then size a batch for 100 ms.
     Record even pilot samples, with their own repetition counts. */
  for (int b = 0; b < 3; ++b) {
    current_build = b;
    repetitions = 1;
    int pilot = 0;
    do {
      elapsed = batch(); sample("pilot",-1,pilot++,elapsed);
      if (elapsed >= 10000000ULL) break;
      if (repetitions > ULONG_MAX/10) die("pilot overflow");
      repetitions *= 10;
    } while (1);
    /* A stalled pilot batch (cold start, a page-fault burst) sizes batches far too short, and
       then the barrier dominates every sample (lead, 2026-11-06: 4-9 ms samples in the first
       M2 block). Re-size from a check batch until one lands within 50-200 ms. */
    for (int sizing = 0;; ++sizing) {
      double scaled = (double)repetitions*100000000.0/elapsed;
      if (scaled >= (double)ULONG_MAX) die("repetition overflow");
      repetitions = scaled < 1 ? 1 : (unsigned long)(scaled+0.5);
      elapsed = batch(); sample("pilot",-1,pilot++,elapsed);
      if (elapsed >= 50000000ULL && elapsed <= 200000000ULL) break;
      if (sizing == 9) die("batch sizing did not settle within 50-200 ms");
    }
    reps[b] = repetitions;
  }
  /* Global warm-up: the slow regime of the first seconds after the threads start ended
     6.2-6.9 s into the first build in every large step seen (lead, 2026-11-06). */
  uint64_t warm_start = now();
  for (int round = 0; now()-warm_start < warmup_seconds*1000000000ULL; ++round)
    for (int k = 0; k < 3; ++k) {
      current_build = build_in_round(round,k); repetitions = reps[current_build];
      elapsed = batch(); sample("warmup",-1,round,elapsed);
    }
  uint64_t medians[3][5];
  double gf[5], ratio[5], gcc_x87[5];
  int gf_defined = 1;
  for (int g = 0; g < 5; ++g) {
    uint64_t samples[3][21];
    for (int round = 0; round < 24; ++round)
      for (int k = 0; k < 3; ++k) {
        current_build = build_in_round(round,k); repetitions = reps[current_build];
        if (round < 3) { elapsed = batch(); sample("warmup",g,round,elapsed); }
        else { elapsed = batch(); sample("timed",g,round-3,elapsed); samples[current_build][round-3] = elapsed; }
      }
    double per_element[3];
    for (int b = 0; b < 3; ++b) {
      qsort(samples[b],21,sizeof(**samples),compare);
      medians[b][g] = samples[b][10];
      per_element[b] = (double)medians[b][g]/((double)workers*length*reps[b]);
      printf("group kernel=%s build=%s group=%d min_ns=%llu median_ns=%llu max_ns=%llu\n",
             kernels[selected].name,build_names[b],g,
             (unsigned long long)samples[b][0],(unsigned long long)samples[b][10],
             (unsigned long long)samples[b][20]);
    }
    /* Same-group pairing: builds 0 gcc, 1 x87, 2 imci (driver.c). */
    double s_gcc = per_element[1]/per_element[0], s_imci = per_element[1]/per_element[2];
    gcc_x87[g] = per_element[0]/per_element[1];
    ratio[g] = per_element[0]/per_element[2];
    if (s_imci-1 <= 0) gf_defined = 0;
    gf[g] = (s_gcc-1)/(s_imci-1);
    printf("pair kernel=%s group=%d gcc_over_x87=%.6f imci_over_x87=%.6f gcc_over_imci=%.6f "
           "gain_fraction=%.6f\n",kernels[selected].name,g,gcc_x87[g],per_element[2]/per_element[1],
           ratio[g],gf[g]);
  }
  int sized = 1;
  double figure[3];
  for (int b = 0; b < 3; ++b) {
    uint64_t sorted[5];
    memcpy(sorted,medians[b],sizeof(sorted));
    qsort(sorted,5,sizeof(*sorted),compare);
    double spread = (double)(sorted[4]-sorted[0])/sorted[2];
    /* A launch is valid only if its samples are the protocol's ~100 ms batches. */
    int build_sized = sorted[2] >= 50000000ULL && sorted[2] <= 200000000ULL;
    sized = sized && build_sized;
    figure[b] = (double)sorted[2]/((double)workers*length*reps[b]);
    printf("summary kernel=%s build=%s length=%lu threads_per_core=%d cores=%d "
           "repetitions=%lu median_ns=%llu ns_per_element=%.9f group_spread=%.9f "
           "within_launch_ok=%d launch=%d working_set=%s short_length=%u\n",
           kernels[selected].name,build_names[b],length,density,cores,
           reps[b],(unsigned long long)sorted[2],figure[b],spread,
           spread < 0.02 && build_sized && density != 3,launch,working_set,short_length);
  }
  /* The launch figure (ADR-0010 point 6) and the paired validity rule: the quantity M2 decides
     on, taken from same-group medians, must agree across the five groups within 2%. */
  double gf_launch = (figure[1]/figure[0]-1)/(figure[1]/figure[2]-1);
  double gf_spread = spread_of(gf,5), ratio_spread = spread_of(ratio,5), gcc_x87_max = 0;
  for (int g = 0; g < 5; ++g) if (gcc_x87[g] > gcc_x87_max) gcc_x87_max = gcc_x87[g];
  double gate = gf_defined ? gf_spread : ratio_spread;
  int paired_ok = sized && density != 3 && isfinite(gate) && gate < 0.02;
  if (!paired_ok) noisy = 1;
  printf("launch kernel=%s length=%lu threads_per_core=%d cores=%d launch=%d working_set=%s "
         "short_length=%u gain_fraction=%.6f gain_fraction_defined=%d gain_fraction_spread=%.9f "
         "gcc_over_imci_spread=%.9f gcc_over_x87_max=%.6f sized=%d paired_ok=%d\n",
         kernels[selected].name,length,density,cores,launch,working_set,short_length,
         gf_launch,gf_defined,gf_spread,ratio_spread,gcc_x87_max,sized,paired_ok);
  stopping = 1; sync_workers();
  for (int w = 0; w < workers; ++w) if (pthread_join(threads[w],NULL)) die("pthread_join");
  if (pthread_barrier_destroy(&barrier)) die("barrier destroy");
  policy("end");
  return noisy ? 3 : 0;
}
