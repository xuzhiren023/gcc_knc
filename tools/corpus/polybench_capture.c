/* Complete live-out doubles before display rounding; host checks tolerance. */
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <signal.h>
#include <stdlib.h>

int corpus_fprintf(FILE *stream, const char *format, ...)
{
  static unsigned long count;
  static char name[80];
  static int output_started;
  va_list args;
  int result = 0;
  va_start(args, format);
  if (!strcmp(format, "begin dump: %s")) {
    /* The launcher ends timing while this child is stopped, then resumes
       complete output. No formatting or transfer belongs to the kernel. */
    if (!output_started++ && getenv("CORPUS_TIMED")) raise(SIGSTOP);
    snprintf(name, sizeof name, "%s", va_arg(args, const char *));
    count = 0;
    printf("CORPUS_ARRAY {\"array\":\"%s\",\"values\":[", name);
  } else if (!strcmp(format, "%0.2lf ")) {
    double x = va_arg(args, double);
    printf("%s%.17g", count++ ? "," : "", x);
  } else if (!strcmp(format, "\nend   dump: %s\n")) {
    puts("]}");
  } else if (strcmp(format, "\n") && !strstr(format, "DUMP_ARRAYS")) {
    result = vfprintf(stream, format, args);
  }
  va_end(args);
  return result;
}
