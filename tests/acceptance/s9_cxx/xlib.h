// S9-05: types shared across the DSO boundary; key functions live in xlib.cc.
#include <stdexcept>
struct XError : std::runtime_error {
  int code;
  XError(const char *what, int c);
  ~XError() override;
};
struct XShape {
  virtual ~XShape();
  virtual int sides() const = 0;
};
struct XSquare : XShape {
  ~XSquare() override;
  int sides() const override;
};
void x_throw(int code);
XShape *x_make(int kind);
int x_catch_from_main(void (*fn)());
