// options: -O2 -march=knc
// scan-asm-func batch: \bkxor\s+%k([0-7]),\s*%k\1,\s*%k\1\b
// S6-14: reload creates k1:QI=0 for a loop-store-motion flag.
// S6-10 already handles it; the reported ICE was an unmerged S6-05 WIP.
// Original reproducer: s6-14/timing-ice.c (retained, not a second test).
/* S6-14: loop-store-motion flags for conditional static struct updates. */
typedef unsigned long long u64;
struct worker { u64 start, end; unsigned long n; };
struct worker data[240];
int workers;
static struct {
  u64 max_ns, median_ns, skew_ns;
  unsigned long nivcsw, nivcsw_max, stime_us;
  int max_worker, nivcsw_worker;
} last;
extern void sort(u64 *, int);

__attribute__((noinline)) u64 batch(void)
{
  u64 first = -1ULL, last_end = 0, last_start = 0, durations[240];
  __builtin_memset(&last, 0, sizeof(last));
  for (int w = 0; w < workers; ++w) {
    if (data[w].start < first) first = data[w].start;
    if (data[w].start > last_start) last_start = data[w].start;
    if (data[w].end > last_end) last_end = data[w].end;
    durations[w] = data[w].end - data[w].start;
    if (durations[w] > last.max_ns) {
      last.max_ns = durations[w]; last.max_worker = w;
    }
    unsigned long n = data[w].n;
    last.nivcsw += n;
    if (n > last.nivcsw_max) {
      last.nivcsw_max = n; last.nivcsw_worker = w;
    }
  }
  sort(durations, workers);
  last.median_ns = durations[workers / 2];
  last.skew_ns = last_start - first;
  return last_end - first;
}

void sort(u64 *values, int count)
{
  for (int i = 1; i < count; ++i)
    for (int j = i; j > 0 && values[j] < values[j-1]; --j) {
      u64 t = values[j]; values[j] = values[j-1]; values[j-1] = t;
    }
}

int main(void)
{
  workers = 3;
  data[0] = (struct worker){10, 20, 4};
  data[1] = (struct worker){12, 42, 2};
  data[2] = (struct worker){11, 31, 7};
  if (batch() != 32 || last.max_ns != 30 || last.max_worker != 1
      || last.median_ns != 20 || last.skew_ns != 2
      || last.nivcsw != 13 || last.nivcsw_max != 7 || last.nivcsw_worker != 2)
    __builtin_abort();
  return 0;
}
