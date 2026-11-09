// S9-03/S9-05: dynamic_cast down, across and to void*, typeid, bad_cast.
#include "check.h"
#include <typeinfo>

struct Base {
  virtual ~Base() {}
  int b = 1;
};
struct Other {
  virtual ~Other() {}
  int o = 2;
};
struct Derived : Base {
  int d = 3;
};
struct Multi : Derived, Other {
  int m = 4;
};

__attribute__((noinline)) static Base *make(int k) {
  if (k == 0)
    return new Base;
  if (k == 1)
    return new Derived;
  return new Multi;
}

int main() {
  Base *pb = make(0), *pd = make(1), *pm = make(2);
  CHECK(dynamic_cast<Derived *>(pd) != nullptr);
  CHECK(dynamic_cast<Derived *>(pb) == nullptr);
  Other *po = dynamic_cast<Other *>(pm);
  CHECK(po != nullptr && po->o == 2);
  CHECK(dynamic_cast<Other *>(pd) == nullptr);
  CHECK(dynamic_cast<void *>(po) == static_cast<void *>(static_cast<Multi *>(pm)));
  CHECK(typeid(*pm) == typeid(Multi) && typeid(*pd) != typeid(Multi));
  CHECK(typeid(*pd).name()[0] != '\0');
  bool bad = false;
  try {
    (void)dynamic_cast<Derived &>(*pb);
  } catch (const std::bad_cast &) {
    bad = true;
  }
  CHECK(bad);
  delete pb;
  delete pd;
  delete pm;
  return report("rtti");
}
