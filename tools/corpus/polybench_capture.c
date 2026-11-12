/* Complete live-out doubles, materialized before exit; display is external. */
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int corpus_fprintf(FILE *stream, const char *format, ...)
{
  static FILE *output;
  static uint64_t count;
  static long count_offset;
  static int started;
  va_list args;
  int result = 0;
  va_start(args, format);
  if (!strcmp(format, "begin dump: %s")) {
    char name[80] = {0};
    if (output) exit(2);
    output = fopen("arrays.bin", started++ ? "r+b" : "wb");
    if (!output || fseek(output, 0, SEEK_END)) exit(2);
    if (snprintf(name, sizeof name, "%s", va_arg(args, const char *)) >= sizeof name) exit(2);
    count = 0;
    if (fwrite(name, 1, sizeof name, output) != sizeof name) exit(2);
    count_offset = ftell(output);
    if (count_offset < 0 || fwrite(&count, sizeof count, 1, output) != 1) exit(2);
  } else if (!strcmp(format, "%0.2lf ")) {
    double x = va_arg(args, double);
    if (!output || fwrite(&x, sizeof x, 1, output) != 1) exit(2);
    ++count;
  } else if (!strcmp(format, "\nend   dump: %s\n")) {
    if (!output || !count || fseek(output, count_offset, SEEK_SET) ||
        fwrite(&count, sizeof count, 1, output) != 1 || fclose(output)) exit(2);
    output = NULL;
  } else if (strcmp(format, "\n") && !strstr(format, "DUMP_ARRAYS")) {
    result = vfprintf(stream, format, args);
  }
  va_end(args);
  return result;
}
