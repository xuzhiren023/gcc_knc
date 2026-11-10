// S9-03/S9-05: throw and catch through frames, unwinding destructors, rethrow, exception_ptr.
#include "check.h"
#include <exception>
#include <new>
#include <stdexcept>
#include <string>
#include <vector>

static int destroyed;
struct Guard {
  ~Guard() { ++destroyed; }
};
struct Base {
  int code;
  explicit Base(int c) : code(c) {}
  virtual ~Base() {}
};
struct Derived : Base {
  explicit Derived(int c) : Base(c) {}
};

__attribute__((noinline)) static void level3(int k) {
  Guard g;
  if (k > 0)
    throw Derived(k);
}
__attribute__((noinline)) static void level2(int k) {
  Guard g;
  level3(k);
}
__attribute__((noinline)) static void level1(int k) {
  Guard g;
  level2(k);
}

int main() {
  int caught = 0;
  try {
    throw 17;
  } catch (int v) {
    caught = v;
  }
  CHECK(caught == 17);

  destroyed = 0;
  try {
    level1(5);
  } catch (const Base &e) {
    caught = e.code;
  }
  CHECK(caught == 5 && destroyed == 3);

  destroyed = 0;
  level1(0);
  CHECK(destroyed == 3);

  try {
    try {
      throw std::string("inner");
    } catch (...) {
      throw;
    }
  } catch (const std::string &s) {
    caught = (int)s.size();
  }
  CHECK(caught == 5);

  std::exception_ptr p;
  try {
    std::vector<int> v(3);
    (void)v.at(10);
  } catch (...) {
    p = std::current_exception();
  }
  bool range = false;
  try {
    std::rethrow_exception(p);
  } catch (const std::out_of_range &) {
    range = true;
  }
  CHECK(range);

  bool alloc = false;
  try {
    volatile std::size_t huge = ~(std::size_t)0 / 4;
    // The pointer escapes: GCC 10+ may delete an unused new/delete pair (C++14 allocation
    // elision), which GCC 16 does at -O2, and then nothing throws.
    static char *volatile sink;
    sink = new char[huge];
    delete[] sink;
  } catch (const std::bad_alloc &) {
    alloc = true;
  }
  CHECK(alloc);

  try {
    try {
      throw std::runtime_error("first");
    } catch (const std::exception &) {
      throw std::logic_error("second");
    }
  } catch (const std::logic_error &e) {
    caught = std::string(e.what()) == "second";
  }
  CHECK(caught == 1);
  return report("eh");
}
