// S9 acceptance (lead-owned): each program prints one result line, compared byte for byte on the host.
// Built with -DBREAK, the first check of every program is inverted, so each program can go red.
#include <cstdio>
#ifdef BREAK
static const bool break_first = true;
#else
static const bool break_first = false;
#endif
static int checks, failures;
#define CHECK(cond)                                                     \
  do {                                                                  \
    ++checks;                                                           \
    bool ok_ = (cond);                                                  \
    if (break_first && checks == 1)                                     \
      ok_ = !ok_;                                                       \
    if (!ok_) {                                                         \
      ++failures;                                                       \
      std::printf("check %d failed: %s\n", checks, #cond);              \
    }                                                                   \
  } while (0)
static int report(const char *name) {
  std::printf("S9-CXX %s %s checks=%d failures=%d\n", name, failures ? "FAIL" : "PASS", checks, failures);
  return failures != 0;
}
