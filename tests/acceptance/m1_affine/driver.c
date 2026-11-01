/* M1 acceptance driver.  Runs natively on KNC; also runs on any POSIX host so
   the fixture's own logic can be checked before the compiler under test exists.

   What it proves:
     - runtime-fed loops produce exact results for lengths 0..MAX_N at every
       element offset within a cache line;
     - nothing is written outside [0, n);
     - nothing is read or written past the end of the arrays, even when they
       end flush against an unmapped page (the unaligned load/store pair and
       masked tails must not fault);
     - scalar FP, varargs printf and the vector loops coexist in one program.

   All inputs are exactly representable and all results are exact in FP32 and
   FP64, so x87 excess precision and FMA contraction cannot change any result:
   a mismatch is a code generation bug.  */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/mman.h>
#include "affine.h"

#define MAX_N 65UL
#define CACHE_LINE 64UL
#define SENTINEL 0x5A

static unsigned long failures;

static void
fail (const char *test, unsigned long n, unsigned long off, unsigned long i,
      double got, double want)
{
  if (++failures <= 20)
    printf ("FAIL %s n=%lu off=%lu i=%lu got=%.17g want=%.17g\n",
	    test, n, off, i, got, want);
}

/* Two mapped pages followed by one PROT_NONE page; the returned pointer is
   BYTES before the unmapped page.  */
static void *
flush_against_guard (size_t bytes)
{
  size_t page = (size_t) sysconf (_SC_PAGESIZE);
  size_t mapped = (bytes / page + 2) * page;
  char *base = mmap (NULL, mapped + page, PROT_READ | PROT_WRITE,
		     MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (base == MAP_FAILED || mprotect (base + mapped, page, PROT_NONE) != 0)
    {
      perror ("guard page setup");
      exit (2);
    }
  return base + mapped - bytes;
}

static void
check_bytes (const char *test, const unsigned char *p, size_t count,
	     unsigned long n, unsigned long off)
{
  for (size_t i = 0; i < count; ++i)
    if (p[i] != SENTINEL)
      {
	fail (test, n, off, i, p[i], SENTINEL);
	return;
      }
}

#define DEFINE_AFFINE_CHECK(NAME, TYPE)					\
static void								\
NAME (const char *test,							\
      void (*fn) (TYPE *restrict, const TYPE *restrict, TYPE, TYPE,	\
		  unsigned long))					\
{									\
  enum { PAD = (int) (2 * CACHE_LINE) };				\
  static unsigned char store[2 * PAD + (MAX_N + CACHE_LINE) * sizeof (TYPE)] \
    __attribute__ ((aligned (64)));					\
  static TYPE in[MAX_N + CACHE_LINE] __attribute__ ((aligned (64)));	\
  volatile TYPE a = (TYPE) 2.0, b = (TYPE) 0.5;				\
  for (unsigned long n = 0; n <= MAX_N; ++n)				\
    for (unsigned long off = 0; off < CACHE_LINE / sizeof (TYPE); ++off) \
      {									\
	TYPE *y = (TYPE *) (store + PAD) + off;				\
	memset (store, SENTINEL, sizeof store);				\
	for (unsigned long i = 0; i < n; ++i)				\
	  in[off + i] = (TYPE) i * (TYPE) 0.25;				\
	fn (y, in + off, a, b, n);					\
	for (unsigned long i = 0; i < n; ++i)				\
	  {								\
	    volatile TYPE want = (TYPE) i * (TYPE) 0.5 + (TYPE) 0.5;	\
	    if (y[i] != want)						\
	      fail (test, n, off, i, y[i], want);			\
	  }								\
	check_bytes (test, store, (size_t) ((char *) y - (char *) store), \
		     n, off);						\
	check_bytes (test, (unsigned char *) (y + n),			\
		     (size_t) (store + sizeof store - (unsigned char *) (y + n)), \
		     n, off);						\
      }									\
  /* Same computation with both arrays ending flush against a guard page. */ \
  for (unsigned long n = 1; n <= MAX_N; ++n)				\
    {									\
      TYPE *gy = flush_against_guard (n * sizeof (TYPE));		\
      TYPE *gx = flush_against_guard (n * sizeof (TYPE));		\
      for (unsigned long i = 0; i < n; ++i)				\
	gx[i] = (TYPE) i * (TYPE) 0.25;					\
      fn (gy, gx, a, b, n);						\
      for (unsigned long i = 0; i < n; ++i)				\
	{								\
	  volatile TYPE want = (TYPE) i * (TYPE) 0.5 + (TYPE) 0.5;	\
	  if (gy[i] != want)						\
	    fail (test, n, 0, i, gy[i], want);				\
	}								\
    }									\
}

DEFINE_AFFINE_CHECK (check_affine_f32, float)
DEFINE_AFFINE_CHECK (check_affine_f64, double)

/* Lanes computed independently would give the wrong answer here.  */
static void
check_recurrence (void)
{
  static float x[MAX_N] __attribute__ ((aligned (64)));
  static float y[MAX_N] __attribute__ ((aligned (64)));
  for (unsigned long n = 0; n <= MAX_N; ++n)
    {
      volatile float prev = 0.0f;
      for (unsigned long i = 0; i < n; ++i)
	x[i] = (float) (i + 1);
      recurrence_f32 (y, x, n);
      for (unsigned long i = 0; i < n; ++i)
	{
	  volatile float want = x[i] - prev;
	  if (y[i] != want)
	    fail ("recurrence_f32", n, 0, i, y[i], want);
	  prev = want;
	}
    }
}

#ifdef KNC_WITH_FORTRAN
static void
fortran_adapter (float *restrict y, const float *restrict x, float a, float b,
		 unsigned long n)
{
  affine_f32_fortran (y, x, &a, &b, &n);
}
#endif

int
main (void)
{
  /* Keep earlier FAIL lines when a guard page ends the process.  */
  setvbuf (stdout, NULL, _IOLBF, 0);

  check_affine_f32 ("affine_f32", affine_f32);
  check_affine_f64 ("affine_f64", affine_f64);
  check_recurrence ();
#ifdef KNC_WITH_FORTRAN
  check_affine_f32 ("affine_f32_fortran", fortran_adapter);
#endif

  /* Scalar FP through varargs after the vector loops have run.  */
  volatile double scalar = 1.5;
  printf ("%s scalar=%.2f failures=%lu\n",
	  failures ? "ACCEPT-FAIL" : "ACCEPT-PASS", scalar * 2.0, failures);
  return failures ? 1 : 0;
}
