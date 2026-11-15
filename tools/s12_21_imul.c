/* S12-21: serial IMUL screening, not a claim about production latency.
   Original diagnostic; R02 p.56 motivates measuring each width/form. */
#define _GNU_SOURCE
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>

#define DECL(bits, form, dep) extern uint64_t imul_##bits##_##form##_##dep(uint64_t, const uint64_t *);
#define FORMS(bits) DECL(bits, register, dependent) DECL(bits, register, independent) \
                    DECL(bits, memory, dependent) DECL(bits, memory, independent)
FORMS(32)
FORMS(64)
struct sample { const char *name; int bits, streams; uint64_t (*fn)(uint64_t, const uint64_t *); };
#define ROW(bits, form, dep, streams) {#bits " " #form " " #dep, bits, streams, imul_##bits##_##form##_##dep}
static const struct sample cases[] = {
  ROW(32, register, dependent, 1), ROW(32, register, independent, 8),
  ROW(32, memory, dependent, 1), ROW(32, memory, independent, 8),
  ROW(64, register, dependent, 1), ROW(64, register, independent, 8),
  ROW(64, memory, dependent, 1), ROW(64, memory, independent, 8)
};

static uint64_t ticks(void)
{
  unsigned a, d;
  __asm__ volatile("cpuid\n\trdtsc" : "=a"(a), "=d"(d) : "a"(0) : "rbx", "rcx", "memory");
  return ((uint64_t)d << 32) | a;
}
static double seconds(void)
{
  struct timespec t;
  if (clock_gettime(CLOCK_MONOTONIC_RAW, &t)) return -1;
  return t.tv_sec + t.tv_nsec * 1e-9;
}
static uint64_t power3(uint64_t n)
{
  uint64_t x = 1, base = 3;
  while (n) { if (n & 1) x *= base; base *= base; n >>= 1; }
  return x;
}
static void topology(int cpu, const char *field)
{
  char path[160], value[160];
  snprintf(path, sizeof path, "/sys/devices/system/cpu/cpu%d/%s", cpu, field);
  FILE *f = fopen(path, "r");
  if (f && fgets(value, sizeof value, f)) printf("IMUL_ENV %s %s", field, value);
  else printf("IMUL_ENV %s unavailable\n", field);
  if (f) fclose(f);
}
int main(void)
{
  cpu_set_t granted, one, actual;
  int cpu, count = 0, chosen = -1;
  const uint64_t factor = 3, iterations = 200000, operations = iterations * 64;
  if (sched_getaffinity(0, sizeof granted, &granted)) return 2;
  for (cpu = 0; cpu < CPU_SETSIZE; ++cpu) if (CPU_ISSET(cpu, &granted)) {
    ++count; if (chosen < 0) chosen = cpu;
  }
  if (chosen < 0) return 2;
  CPU_ZERO(&one); CPU_SET(chosen, &one);
  if (sched_setaffinity(0, sizeof one, &one) ||
      sched_getaffinity(0, sizeof actual, &actual) || CPU_COUNT(&actual) != 1 ||
      !CPU_ISSET(chosen, &actual)) return 2;
  printf("IMUL_AFFINITY granted=%d selected=%d actual=%d\n", count, chosen, sched_getcpu());
  topology(chosen, "topology/core_id");
  topology(chosen, "topology/thread_siblings_list");
  topology(chosen, "cpufreq/scaling_cur_freq");
  uint64_t overhead_start = ticks(), overhead_end = ticks();
  printf("IMUL_OVERHEAD ticks=%llu (reported, not subtracted)\n",
         (unsigned long long)(overhead_end - overhead_start));
  for (unsigned i = 0; i < sizeof cases / sizeof cases[0]; ++i) {
    const struct sample *c = &cases[i];
    uint64_t expected = power3(operations / c->streams);
    if (c->bits == 32) expected = (uint32_t)expected;
    expected *= c->streams;
    (void)c->fn(100, &factor); /* Identical warm-up, outside timed region. */
    for (int repeat = 0; repeat < 3; ++repeat) {
      double begin = seconds();
      uint64_t start = ticks(), value = c->fn(iterations, &factor), end = ticks();
      double elapsed = seconds() - begin;
      if (begin < 0 || elapsed <= 0 || end <= start || value != expected || sched_getcpu() != chosen) {
        fprintf(stderr, "IMUL_FAIL %s expected=%llu actual=%llu\n", c->name,
                (unsigned long long)expected, (unsigned long long)value);
        return 1;
      }
      printf("IMUL_SAMPLE %s repeat=%d streams=%d operations=%llu ticks=%llu seconds=%.9f ticks_per_op=%.6f tsc_hz=%.0f\n",
             c->name, repeat, c->streams, (unsigned long long)operations,
             (unsigned long long)(end-start), elapsed, (double)(end-start)/operations, (end-start)/elapsed);
    }
  }
  topology(chosen, "cpufreq/scaling_cur_freq");
  puts("RESULT IMUL PASS");
  return 0;
}
