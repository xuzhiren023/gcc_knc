// S9-05: exceptions and RTTI across a DSO boundary, both directions (main and lib may come from
// different compilers: build.py pairs GCC 16 with the donor GCC 5.1.1 both ways).
#include "check.h"
#include "xlib.h"

static void main_throws() { throw std::runtime_error("main"); }

int main() {
  int code = 0;
  try {
    x_throw(9);
  } catch (const XError &e) {
    code = e.code;
  }
  CHECK(code == 9);
  bool inv = false;
  try {
    x_throw(-1);
  } catch (const std::logic_error &) {
    inv = true;
  }
  CHECK(inv);
  CHECK(x_catch_from_main(main_throws) == 'm');
  XShape *sq = x_make(4), *tr = x_make(3);
  CHECK(dynamic_cast<XSquare *>(sq) != nullptr && sq->sides() == 4);
  CHECK(dynamic_cast<XSquare *>(tr) == nullptr && tr->sides() == 3);
  delete sq;
  delete tr;
  return report("xdso");
}
