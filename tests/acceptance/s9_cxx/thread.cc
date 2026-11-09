// S9-05: std::thread, mutex, condition_variable, atomics, thread_local, call_once, async.
#include "check.h"
#include <atomic>
#include <condition_variable>
#include <future>
#include <mutex>
#include <thread>
#include <vector>

static thread_local int tl_value = 0;

int main() {
  const int nthreads = 8, iters = 10000;
  std::mutex mu;
  long counter = 0;
  std::atomic<long> acount(0);
  std::vector<int> tl_seen(nthreads, -1);
  std::vector<std::thread> ts;
  for (int t = 0; t < nthreads; t++)
    ts.emplace_back([&, t] {
      tl_value = t * 10;
      for (int i = 0; i < iters; i++) {
        std::lock_guard<std::mutex> g(mu);
        counter++;
        acount.fetch_add(1, std::memory_order_relaxed);
      }
      tl_seen[t] = tl_value;
    });
  for (auto &th : ts)
    th.join();
  CHECK(counter == (long)nthreads * iters);
  CHECK(acount.load() == (long)nthreads * iters);
  bool tl_ok = tl_value == 0;
  for (int t = 0; t < nthreads; t++)
    tl_ok = tl_ok && tl_seen[t] == t * 10;
  CHECK(tl_ok);

  std::condition_variable cv;
  int turn = 0, rounds = 1000;
  std::thread pong([&] {
    for (int r = 0; r < rounds; r++) {
      std::unique_lock<std::mutex> lk(mu);
      cv.wait(lk, [&] { return turn == 1; });
      turn = 0;
      cv.notify_one();
    }
  });
  for (int r = 0; r < rounds; r++) {
    std::unique_lock<std::mutex> lk(mu);
    turn = 1;
    cv.notify_one();
    cv.wait(lk, [&] { return turn == 0; });
  }
  pong.join();
  CHECK(turn == 0);

  std::once_flag once;
  std::atomic<int> once_runs(0);
  std::vector<std::thread> os;
  for (int t = 0; t < 4; t++)
    os.emplace_back([&] { std::call_once(once, [&] { once_runs++; }); });
  for (auto &th : os)
    th.join();
  CHECK(once_runs.load() == 1);

  auto f1 = std::async(std::launch::async, [] { return 6 * 7; });
  auto f2 = std::async(std::launch::deferred, [] { return 5; });
  CHECK(f1.get() == 42 && f2.get() == 5);
  return report("thread");
}
