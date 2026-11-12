/* Numeric checksums of live-out doubles, before their display rounding.
   Summation in long double; tolerance is enforced on the host. */
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

int corpus_fprintf(FILE *stream, const char *format, ...)
{
  static long double sum, absolute, squares, weighted;
  static unsigned long count;
  static char name[80];
  va_list args;
  int result = 0;
  va_start(args, format);
  if (!strcmp(format, "begin dump: %s")) {
    snprintf(name, sizeof name, "%s", va_arg(args, const char *));
    count = 0;
    sum = absolute = squares = weighted = 0;
  } else if (!strcmp(format, "%0.2lf ")) {
    long double x = va_arg(args, double);
    ++count;
    sum += x;
    absolute += fabsl(x);
    squares += x * x;
    weighted += x * (1 + (count % 251));
  } else if (!strcmp(format, "\nend   dump: %s\n")) {
    printf("CORPUS_ARRAY {\"array\":\"%s\",\"count\":%lu,\"sum\":%.17Lg,"
           "\"abs\":%.17Lg,\"squares\":%.17Lg,\"weighted\":%.17Lg}\n",
           name, count, sum, absolute, squares, weighted);
  } else if (strcmp(format, "\n") && !strstr(format, "DUMP_ARRAYS")) {
    result = vfprintf(stream, format, args);
  }
  va_end(args);
  return result;
}
