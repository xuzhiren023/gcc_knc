// S9-05: documents std::thread::hardware_concurrency() on KNC (docs/research/knc-libstdcxx.md 3.3).
// libstdc++ returns get_nprocs(), the card's online CPUs, not the CPUs the job may run on.
// The first line records the values (card-dependent); the result line is compared on the host.
#include <cstdio>
#include <sched.h>
#include <thread>
#include <unistd.h>

int main() {
  unsigned reported = std::thread::hardware_concurrency();
  long online = sysconf(_SC_NPROCESSORS_ONLN);
  cpu_set_t set;
  int allowed = sched_getaffinity(0, sizeof set, &set) == 0 ? CPU_COUNT(&set) : -1;
  std::printf("hardware_concurrency=%u online=%ld affinity=%d\n", reported, online, allowed);
  bool ok = reported > 0 && (long)reported == online;
  std::printf("S9-CXX hwconc %s hardware_concurrency() is the online CPU count, not the affinity mask\n",
              ok ? "PASS" : "FAIL");
  return !ok;
}
