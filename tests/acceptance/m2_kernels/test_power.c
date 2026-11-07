/* Recorded sysfs example: Southampton thesis, Appendix C, p.163.
   See README for source and the limits of this fixture (not our card's read). */
#include "power.h"
#include <errno.h>
#include <math.h>
#include <string.h>
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
  return failures != 0;
}
