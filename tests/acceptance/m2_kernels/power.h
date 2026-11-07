#ifndef M2_POWER_H
#define M2_POWER_H
#include <stdio.h>
int power_parse(FILE *file, double *watts);
double power_joules(double watts, double ns_per_element);
#endif
