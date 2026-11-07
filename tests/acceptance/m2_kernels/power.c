#include "power.h"
#include <errno.h>
int power_parse(FILE *file, double *watts) {
  (void)file; (void)watts;
  return ENODATA;
}
double power_joules(double watts, double ns_per_element) {
  (void)watts; (void)ns_per_element;
  return 0;
}
