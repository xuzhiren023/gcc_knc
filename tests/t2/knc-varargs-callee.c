#include <stdarg.h>
#include <stdio.h>

/* A printf-style callee must pass its donor-compatible list to card libc. */
int var_format(char *out, unsigned long size, const char *fmt, ...)
{
  int result;
  va_list ap;
  va_start(ap, fmt);
  result = vsnprintf(out, size, fmt, ap);
  va_end(ap);
  return result;
}

/* Consume doubles directly as well as forwarding the register save area. */
double var_sum(int n, ...)
{
  double sum = 0;
  va_list ap;
  va_start(ap, n);
  while (n--) sum += va_arg(ap, double);
  va_end(ap);
  return sum;
}
