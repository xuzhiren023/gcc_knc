/* Recorded sysfs example: Southampton thesis, Appendix C, p.163.
   See README for source and the limits of this fixture (not our card's read). */
#define _GNU_SOURCE
#include "power.h"
#include <errno.h>
#include <math.h>
#include <string.h>
/* Exercise the real sampler with a recorded sensor file on the host. */
static const char *sensor_fixture;
static FILE *sensor_open(const char *name, const char *mode) {
  return fopen(strcmp(name,"/sys/class/micras/power") == 0 ? sensor_fixture : name,mode);
}
#define fopen sensor_open
#include "power.c"
#undef fopen
static int failures;
#define CHECK(expr) do { if (!(expr)) { fprintf(stderr,"FAIL: %s\n",#expr); ++failures; } } while (0)
int main(int argc, char **argv) {
  double watts = -1;
  FILE *f = argc == 2 ? fopen(argv[1],"r") : NULL;
  CHECK(f != NULL);
  if (!f) return 1;
  CHECK(power_parse(f,&watts) == 0);
  CHECK(watts == 110.0); /* Total window 0; not rail/instantaneous/peak. */
  fclose(f);
  CHECK(fabs(power_joules(150.0,2.5)-3.75e-7) < 1e-18);
  CHECK(power_joules(150.0,0.0) == 0.0);
  const char *bad[] = {"", "garbage\n", "-1\n", "150000000junk\n", "1e300\n"};
  for (unsigned i = 0; i < sizeof(bad)/sizeof(*bad); ++i) {
    f = tmpfile();
    CHECK(f != NULL);
    if (!f) continue;
    fputs(bad[i],f); rewind(f);
    CHECK(power_parse(f,&watts) == EPROTO);
    fclose(f);
  }
  sensor_fixture = argv[1];
  cpu_set_t workers;
  CPU_ZERO(&workers);
  for (int cpu = 1; cpu <= 240; ++cpu) CPU_SET(cpu,&workers);
  power_init(&workers);
  CHECK(sampler_cpu == -1);
  CHECK(created == 1);
  power_begin(0);
  struct timespec pause = {0,150000000};
  nanosleep(&pause,NULL);
  power_end();
  power_finish();
  CHECK(setup_error == 0);
  CHECK(stats[0].samples > 0);
  CHECK(stats[0].min == 110.0 && stats[0].max == 110.0);
  return failures != 0;
}
