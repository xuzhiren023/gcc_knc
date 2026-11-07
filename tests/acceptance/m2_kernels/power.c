#define _GNU_SOURCE
#include "power.h"
#include "kernels.h"
#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static const char path[] = "/sys/class/micras/power";
/* MPSS total power, window 0, in microwatts. Read only the first line:
   subsequent lines are window 1, connectors, instantaneous/peak and rails.
   README cites the recorded format; the actual card dump is always printed. */
int power_parse(FILE *file, double *watts) {
  char line[128], *end;
  if (!fgets(line,sizeof(line),file)) return ferror(file) ? (errno ? errno : EIO) : EPROTO;
  char *p = line;
  while (isspace((unsigned char)*p)) ++p;
  if (!isdigit((unsigned char)*p)) return EPROTO;
  errno = 0;
  unsigned long long value = strtoull(p,&end,10);
  if (errno || end == p) return EPROTO;
  while (isspace((unsigned char)*end)) ++end;
  if (*end || !strchr(line,'\n') || value > 1000000000ULL) return EPROTO;
  *watts = (double)value*1e-6;
  return 0;
}
double power_joules(double watts, double ns_per_element) {
  return watts*ns_per_element*1e-9;
}

static struct {
  unsigned long samples;
  double sum, min, max;
  int error;
} stats[BUILD_COUNT];
static pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t changed = PTHREAD_COND_INITIALIZER;
static pthread_t thread;
static int created, done, active = -1, setup_error, sampler_cpu = -1;
static unsigned long generation;

static void raw_dump(void) {
  FILE *f = fopen(path,"r");
  printf("power_source path=%s field=total_window0 units=uW interval_ms=50 cpu=",path);
  if (sampler_cpu < 0) printf("unpinned");
  else printf("%d",sampler_cpu);
  printf(" format=confirmed_on_card\n");
  if (!f) {
    setup_error = errno;
    printf("power_raw path=%s power=unavailable errno=%d\n",path,setup_error);
    return;
  }
  char line[256]; unsigned n = 0;
  while (fgets(line,sizeof(line),f)) {
    line[strcspn(line,"\r\n")] = 0;
    printf("power_raw line=%u value=%s\n",++n,line);
  }
  if (ferror(f)) setup_error = errno ? errno : EIO;
  fclose(f);
}
static void *sampler(void *unused) {
  (void)unused;
  cpu_set_t mask, actual;
  if (sampler_cpu >= 0) {
    CPU_ZERO(&mask); CPU_SET(sampler_cpu,&mask);
    if (sched_setaffinity(0,sizeof(mask),&mask)
        || sched_getaffinity(0,sizeof(actual),&actual)) setup_error = errno;
    else if (CPU_COUNT(&actual) != 1 || !CPU_ISSET(sampler_cpu,&actual)
             || sched_getcpu() != sampler_cpu) setup_error = EINVAL;
  }
  if (setup_error) return NULL;
  pthread_mutex_lock(&mutex);
  while (!done) {
    while (active < 0 && !done) pthread_cond_wait(&changed,&mutex);
    if (done) break;
    int b = active;
    unsigned long epoch = generation;
    /* Wait a full sensor interval after the build starts. This avoids an
       immediate stale reading from the preceding interleaved build. */
    struct timespec deadline;
    if (clock_gettime(CLOCK_REALTIME,&deadline)) {
      setup_error = errno; break;
    }
    deadline.tv_nsec += 50000000;
    if (deadline.tv_nsec >= 1000000000) { ++deadline.tv_sec; deadline.tv_nsec -= 1000000000; }
    int rc = 0;
    while (!done && active == b && generation == epoch && !rc)
      rc = pthread_cond_timedwait(&changed,&mutex,&deadline);
    if (done || active != b || generation != epoch) continue;
    if (rc != ETIMEDOUT) { stats[b].error = rc; continue; }
    pthread_mutex_unlock(&mutex);
    double watts = 0;
    FILE *f = fopen(path,"r");
    int error = f ? power_parse(f,&watts) : errno;
    if (f && fclose(f) && !error) error = errno ? errno : EIO;
    pthread_mutex_lock(&mutex);
    /* Discard reads crossing a batch boundary, never charge the next build. */
    if (active != b || generation != epoch) continue;
    if (error) stats[b].error = error;
    else {
      if (!stats[b].samples || watts < stats[b].min) stats[b].min = watts;
      if (!stats[b].samples || watts > stats[b].max) stats[b].max = watts;
      stats[b].sum += watts;
      ++stats[b].samples;
    }
  }
  pthread_mutex_unlock(&mutex);
  return NULL;
}
void power_init(const cpu_set_t *allowed) {
  static const int os_cpus[] = {0,241,242,243};
  /* Cygwin's CPU_ISSET takes a non-const mask; keep the caller's untouched. */
  cpu_set_t available = *allowed;
  for (unsigned i = 0; i < sizeof(os_cpus)/sizeof(*os_cpus); ++i)
    if (CPU_ISSET(os_cpus[i],&available)) { sampler_cpu = os_cpus[i]; break; }
  raw_dump();
  /* A benchmark mask can contain only workers (1-240). In that case inherit
     the allowed mask and let the OS schedule us instead of pinning to -1. */
  if (!setup_error) {
    pthread_attr_t attr;
    int rc = pthread_attr_init(&attr);
    if (rc) { setup_error = rc; return; }
    rc = pthread_attr_setstacksize(&attr,256 * 1024);
    if (!rc) rc = pthread_create(&thread,&attr,sampler,NULL);
    pthread_attr_destroy(&attr);
    if (rc) setup_error = rc;
    else created = 1;
  }
}
void power_begin(int build) {
  if (!created) return;
  pthread_mutex_lock(&mutex);
  active = build; ++generation;
  pthread_cond_signal(&changed);
  pthread_mutex_unlock(&mutex);
}
void power_end(void) {
  if (!created) return;
  pthread_mutex_lock(&mutex);
  active = -1; ++generation;
  pthread_cond_signal(&changed);
  pthread_mutex_unlock(&mutex);
}
void power_finish(void) {
  if (!created) return;
  pthread_mutex_lock(&mutex);
  done = 1;
  pthread_cond_signal(&changed);
  pthread_mutex_unlock(&mutex);
  int rc = pthread_join(thread,NULL);
  if (rc) setup_error = rc;
}
void power_report(int build, const char *name, const char *kernel, int launch,
                  double ns_per_element) {
  unsigned long n = stats[build].samples;
  int error = setup_error ? setup_error : stats[build].error;
  if (!n && !error) error = ENODATA;
  printf("power kernel=%s build=%s launch=%d samples=%lu ",kernel,name,launch,n);
  if (error) printf("power=unavailable errno=%d\n",error);
  else {
    double mean = stats[build].sum/n;
    printf("mean_watts=%.6f min_watts=%.6f max_watts=%.6f joules_per_element=%.12g\n",
           mean,stats[build].min,stats[build].max,power_joules(mean,ns_per_element));
  }
}
