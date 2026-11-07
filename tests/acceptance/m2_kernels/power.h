#ifndef M2_POWER_H
#define M2_POWER_H
#include <stdio.h>
#include <sched.h>
int power_parse(FILE *file, double *watts);
double power_joules(double watts, double ns_per_element);
void power_init(const cpu_set_t *allowed);
void power_begin(int build);
void power_end(void);
void power_finish(void);
void power_report(int build, const char *name, const char *kernel, int launch,
                  double ns_per_element);
#endif
