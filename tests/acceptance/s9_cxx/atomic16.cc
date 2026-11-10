// S9-03/S9-05: a 16-byte std::atomic through libatomic (KNC has no cmpxchg16b), from 4 threads.
#include "check.h"
#include <atomic>
#include <thread>
#include <vector>

struct Pair {
  long a, b;
};

int main() {
  std::atomic<Pair> p(Pair{0, 0});
  const int nthreads = 4, iters = 20000;
  std::vector<std::thread> ts;
  for (int t = 0; t < nthreads; t++)
    ts.emplace_back([&] {
      for (int i = 0; i < iters; i++) {
        Pair old = p.load();
        Pair next;
        do
          next = Pair{old.a + 1, old.b + 2};
        while (!p.compare_exchange_weak(old, next));
      }
    });
  for (auto &th : ts)
    th.join();
  Pair end = p.load();
  CHECK(end.a == (long)nthreads * iters);
  CHECK(end.b == 2 * end.a);
  p.store(Pair{-1, 1});
  Pair back = p.exchange(Pair{3, 4});
  CHECK(back.a == -1 && back.b == 1 && p.load().b == 4);
  return report("atomic16");
}
