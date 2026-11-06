/* S5-21: a 32-byte short vector result uses a hidden result pointer.
   Distinct constants keep the whole result observable without an argument
   whose ABI could conceal a mistaken register-return convention. */
typedef unsigned short __attribute__((__vector_size__ (32))) V;

#ifdef SHORT_VECTOR_CROSS
#include <stdio.h>
#include <stdarg.h>

V short_vector_return (void);
void short_vector_six (long, long, long, long, long, long, V, long);
void short_vector_float (float, V, double, float);
void short_vector_varargs (int, ...);

/* Print every lane so a misplaced or truncated argument cannot hide. */
static void
print_vector (const V *v)
{
  unsigned i;
  for (i = 0; i < 16; ++i)
    printf ("%u%c", (unsigned) (*v)[i], i == 15 ? '\n' : ' ');
}
#endif

#ifdef SHORT_VECTOR_CALLER
int
main (void)
{
  V a = { 101, 203, 307, 409, 503, 607, 709, 809,
          907, 1009, 1103, 1201, 1301, 1409, 1501, 1601 };
  V b = { 65535, 32768, 16384, 8192, 4096, 2048, 1024, 512,
          256, 128, 64, 32, 16, 8, 4, 2 };
  V r;
  short_vector_six (11, 22, 33, 44, 55, 66, a, 77);
  short_vector_float (1.25f, b, -2.5, 3.75f);
  r = short_vector_return ();
  print_vector (&r);
  short_vector_varargs (91, 4.5, a, 92, b, -6.25);
  return 0;
}
#else
V
short_vector_return (void)
{
  return (V) { 1, 2, 3, 4, 5, 6, 7, 8,
               9, 10, 11, 12, 13, 14, 15, 16 };
}

#ifdef SHORT_VECTOR_CROSS
void
short_vector_six (long a, long b, long c, long d, long e, long f, V v,
                  long tail)
{
  printf ("%ld %ld %ld %ld %ld %ld %ld\n", a, b, c, d, e, f, tail);
  print_vector (&v);
}

void
short_vector_float (float a, V v, double b, float c)
{
  printf ("%.2f %.2f %.2f\n", (double) a, b, (double) c);
  print_vector (&v);
}

void
short_vector_varargs (int tag, ...)
{
  va_list ap;
  V a, b;
  double first, last;
  int middle;
  va_start (ap, tag);
  first = va_arg (ap, double);
  a = va_arg (ap, V);
  middle = va_arg (ap, int);
  b = va_arg (ap, V);
  last = va_arg (ap, double);
  va_end (ap);
  printf ("%d %.2f %d %.2f\n", tag, first, middle, last);
  print_vector (&a);
  print_vector (&b);
}
#endif
#endif
