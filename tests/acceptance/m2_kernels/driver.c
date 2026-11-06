/* S6-02 red-stage correctness gate. No timing is permitted until it passes. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef void (*affine_fn) (float *restrict, const float *restrict,
                          const float *restrict, unsigned long);

/* Pointer parameters avoid imposing a scalar floating-point assembly ABI. */
extern void m2_affine_f32_imci (float *restrict, const float *restrict,
                              const float *restrict, unsigned long);
extern void m2_affine_f32_imci_negative (float *restrict, const float *restrict,
                                       const float *restrict, unsigned long);

static void
reference (float *restrict y, const float *restrict x,
           const float *restrict ab, unsigned long n)
{
  for (unsigned long i = 0; i < n; ++i)
    y[i] = ab[0] * x[i] + ab[1];
}

#ifdef HOST_CHECKER_SELFTEST
/* Host-only checker test: this is NOT an execution/emulation of IMCI. */
static void
wrong_copy (float *restrict y, const float *restrict x,
            const float *restrict ab, unsigned long n)
{
  (void) ab;
  memcpy (y, x, n * sizeof (*y));
}
#endif

static uint32_t
bits (float value)
{
  uint32_t result;
  memcpy (&result, &value, sizeof (result));
  return result;
}

static int
check (affine_fn candidate, unsigned long n)
{
  float *x, *storage, *want;
  static const float ab[16] __attribute__ ((aligned (64))) = { 2.0f, 0.5f };
  if (posix_memalign ((void **) &x, 64, (n + 16) * sizeof (*x))
      || posix_memalign ((void **) &storage, 64, (n + 32) * sizeof (*storage))
      || posix_memalign ((void **) &want, 64, (n + 16) * sizeof (*want)))
    {
      fputs ("ERROR allocation\n", stderr);
      exit (2);
    }
  float *y = storage + 16;
  for (unsigned long i = 0; i < n + 16; ++i)
    x[i] = ((int) (i % 127) - 63) * 0.25f;
  for (unsigned long i = 0; i < n + 32; ++i)
    storage[i] = -12345.0f;
  reference (want, x, ab, n);
  candidate (y, x, ab, n);
  int failed = 0;
  for (unsigned long i = 0; i < n; ++i)
    if (bits (y[i]) != bits (want[i]))
      {
        printf ("FAIL affine_f32 imci length=%lu index=%lu got=%08x want=%08x\n",
                n, i, (unsigned) bits (y[i]), (unsigned) bits (want[i]));
        failed = 1;
        break;
      }
  for (unsigned long i = 0; i < 16; ++i)
    if (storage[i] != -12345.0f || y[n + i] != -12345.0f)
      {
        printf ("FAIL affine_f32 imci length=%lu output guard=%lu\n", n, i);
        failed = 1;
        break;
      }
  free (want);
  free (storage);
  free (x);
  return failed;
}

int
main (void)
{
  static const unsigned long lengths[] = {
    255, 256, 257, 512, 1023, 1024, 1025, 4096, 8192, 16384, 262144
  };
#ifdef HOST_CHECKER_SELFTEST
  puts ("HOST_CHECKER_SELFTEST: C stand-in only; no native IMCI result");
  /* A correct result must reach the success path before exercising rejection. */
  if (check (reference, 17))
    return 2;
  affine_fn candidate = wrong_copy;
#elif defined (NEGATIVE_CONTROL)
  affine_fn candidate = m2_affine_f32_imci_negative;
#else
  affine_fn candidate = m2_affine_f32_imci;
#endif
  unsigned failures = 0;
  for (unsigned long n = 0; n <= 64; ++n)
    failures += check (candidate, n);
  for (unsigned long i = 0; i < sizeof (lengths) / sizeof (*lengths); ++i)
    failures += check (candidate, lengths[i]);
  printf ("correctness affine_f32 imci: %u failing lengths\n", failures);
  return failures ? 1 : 0;
}
