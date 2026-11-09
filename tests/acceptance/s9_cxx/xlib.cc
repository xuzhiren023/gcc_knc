// S9-05: the shared library half of the cross-DSO check (built by either compiler).
#include "xlib.h"
XError::XError(const char *what, int c) : std::runtime_error(what), code(c) {}
XError::~XError() {}
XShape::~XShape() {}
XSquare::~XSquare() {}
int XSquare::sides() const { return 4; }
struct XTriangle : XShape {
  int sides() const override { return 3; }
};
void x_throw(int code) {
  if (code < 0)
    throw std::invalid_argument("negative");
  throw XError("x", code);
}
XShape *x_make(int kind) {
  if (kind == 4)
    return new XSquare;
  return new XTriangle;
}
int x_catch_from_main(void (*fn)()) {
  try {
    fn();
  } catch (const std::exception &e) {
    return e.what()[0];
  }
  return 0;
}
