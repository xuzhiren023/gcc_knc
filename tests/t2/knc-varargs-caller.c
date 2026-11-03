#include <stdio.h>
#include <string.h>

extern int var_format(char *, unsigned long, const char *, ...)
  __attribute__((format(printf, 3, 4)));
extern double var_sum(int, ...);

int main(void)
{
  char direct[256], forwarded[256];
  const char *fmt = "%d|%.3f|%.4Lf|%.2f|%d\n";
  int a = snprintf(direct, sizeof direct, fmt, 17, 2.5, 3.125L, -0.75, -9);
  int b = var_format(forwarded, sizeof forwarded, fmt,
                     17, 2.5, 3.125L, -0.75, -9);
  if (a < 0 || b != a || strcmp(direct, forwarded)
      || strcmp(direct, "17|2.500|3.1250|-0.75|-9\n")
      || var_sum(0) != 0 || var_sum(1, 1.25) != 1.25
      || var_sum(8, 1., 2., 3., 4., 5., 6., 7., 8.) != 36
      || var_sum(10, 1., 2., 3., 4., 5., 6., 7., 8., 9., 10.) != 55)
    return 1;
  /* Compare stdout of donor-only and both cross-links byte for byte on card. */
  if (printf(fmt, 17, 2.5, 3.125L, -0.75, -9) != a)
    return 2;
  return fputs(forwarded, stdout) < 0;
}
