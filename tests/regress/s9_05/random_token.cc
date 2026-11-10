// S9-05: documents which std::random_device tokens block on KNC. The testsuite's
// 26_numerics/random/random_device/cons/token.cc never finished on the card (2026-11-10).
// Its test02 reads std::random_device("/dev/random"); before Linux 5.6, read(2) of /dev/random
// waits until the kernel's entropy estimate covers the request, and the card's kernel has no
// hardware RNG or input devices to fill it. Each token here runs in its own child process
// under a time limit, so one blocking token cannot hide the others.
#include <cstdio>
#include <random>
#include <signal.h>
#include <string>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

enum { returns = 0, unavailable = 1, blocks = 2, crashed = 3 };

static int try_token(const char *token, int limit_ms) {
  pid_t child = fork();
  if (child == 0) {
    try {
      std::random_device device(token);
      device();
      device();  // token.cc test02 calls each device twice
      _exit(returns);
    } catch (...) {
      _exit(unavailable);
    }
  }
  if (child < 0)
    return crashed;
  const timespec tick = {0, 10 * 1000 * 1000};
  for (int waited = 0; waited < limit_ms; waited += 10) {
    int status;
    if (waitpid(child, &status, WNOHANG) == child)
      return WIFEXITED(status) ? WEXITSTATUS(status) : crashed;
    nanosleep(&tick, nullptr);
  }
  kill(child, SIGKILL);
  waitpid(child, nullptr, 0);
  return blocks;
}

int main() {
  // token.cc's tokens, plus "default" (test01) and a numeric seed (test04).
  const char *tokens[] = {"default", "rdseed", "rdrand", "darn", "rand_s", "/dev/urandom",
                          "/dev/random", "getentropy", "arc4random", "mt19937", "prng", "1234"};
  const char *names[] = {"returns", "unavailable", "blocks", "crashed"};
  std::string blocking;
  int working = 0, crashes = 0;
  for (const char *token : tokens) {
    int outcome = try_token(token, 5000);
    std::printf("token %s: %s\n", token, names[outcome]);
    working += outcome == returns;
    crashes += outcome == crashed;
    if (outcome == blocks)
      blocking += (blocking.empty() ? "" : ",") + std::string(token);
  }
  bool ok = working > 0 && crashes == 0;
  std::printf("S9-CXX rdtoken %s random_device tokens that block: %s\n", ok ? "PASS" : "FAIL",
              blocking.empty() ? "none" : blocking.c_str());
  return !ok;
}
