// S9-05: documents condition_variable waits on KNC (docs/research/knc-libstdcxx.md 3.3).
// glibc 2.21 has no pthread_cond_clockwait, so a steady_clock wait_until is converted to a
// system_clock deadline (pthread_cond_timedwait); a wall-clock step on the card moves it.
// The program checks that the steady_clock deadline is still honoured and names the mechanism.
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <mutex>

int main() {
#ifdef _GLIBCXX_USE_PTHREAD_COND_CLOCKWAIT
  const char *mechanism = "steady_clock (pthread_cond_clockwait)";
#else
  const char *mechanism = "system_clock (pthread_cond_timedwait, no pthread_cond_clockwait)";
#endif
  using clock = std::chrono::steady_clock;
  std::mutex m;
  std::condition_variable cv;
  std::unique_lock<std::mutex> lock(m);
  const clock::time_point deadline = clock::now() + std::chrono::milliseconds(50);
  std::cv_status status;
  do  // nobody notifies: anything before the deadline is a spurious wakeup
    status = cv.wait_until(lock, deadline);
  while (status == std::cv_status::no_timeout && clock::now() < deadline);
  bool ok = status == std::cv_status::timeout && clock::now() >= deadline;
  std::printf("S9-CXX cvclock %s steady_clock wait_until times out at its deadline; waits on %s\n",
              ok ? "PASS" : "FAIL", mechanism);
  return !ok;
}
