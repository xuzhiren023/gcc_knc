// S10-13: use the real libstdc++ overload, including its -O0 wrapper.
#include <cmath>

extern "C" long double std_root (long double x)
{
  return std::cbrt (x);
}

extern "C" long double another_std_root (long double x)
{
  return std::cbrt (x);
}
