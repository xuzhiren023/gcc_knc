/* S10-13: the C type-generic entry must select the long double replacement. */
#include <tgmath.h>

long double generic_root (long double x)
{
  return cbrt (x);
}
