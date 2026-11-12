/* S10-13: a matching declaration and the explicit builtin must both be safe.
   Nonconstant arguments prevent compile-time folding.  The T1 runner checks
   both optimization levels, the default warning, its suppression and x86. */
#if !defined(CBRTL_MODEL) && !defined(CBRTL_NATIVE) && !defined(CBRTL_FAULT)
extern long double cbrtl (long double);

long double direct_root (long double x)
{
  return cbrtl (x);
}

long double builtin_root (long double x)
{
  return __builtin_cbrtl (x);
}
#else
/* The same deterministic corpus is used by the host and card.  Only the
   ten meaningful bytes of x87 values are stored; ABI padding is ignored. */
#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <pthread.h>
#include <sched.h>
#ifdef CBRTL_MODEL
#include <mpfr.h>
#endif
extern long double __knc_cbrtl (long double);
typedef union {
  long double value;
  struct { uint64_t mantissa; uint16_t exponent; } bits;
} extended;
#define NORMALS (32766u * 6u)
#define EDGES (NORMALS + 256u + 6u)
#define COUNT (EDGES + (1u << 24))
#define PART ((COUNT + 3) / 4)
static unsigned char *expected;
static unsigned workers, first, last = COUNT;
struct job { unsigned id, failed; long double worst; };

static uint64_t random_word (uint64_t *state)
{
  *state ^= *state >> 12;
  *state ^= *state << 25;
  *state ^= *state >> 27;
  return *state * UINT64_C(2685821657736338717);
}

static long double input (unsigned i)
{
  extended x = {0};
  if (i < NORMALS)
    {
      static const uint64_t m[] = {UINT64_C(0x8000000000000000),
        UINT64_C(0x8000000000000001), UINT64_MAX};
      x.bits.mantissa = m[(i / 2) % 3];
      x.bits.exponent = 1 + i / 6 + ((i & 1) << 15);
    }
  else if ((i -= NORMALS) < 256)
    {
      x.bits.mantissa = UINT64_C(1) << ((i / 4) % 64);
      if (i & 2) --x.bits.mantissa;
      /* Bit 63 denotes the minimum normal, not a pseudo-denormal. */
      x.bits.exponent = (x.bits.mantissa >> 63) + ((i & 1) << 15);
    }
  else if ((i -= 256) < 6)
    {
      x.bits.exponent = (i / 2 ? 0x7fff : 0) + ((i & 1) << 15);
      x.bits.mantissa = i / 2 == 1 ? UINT64_C(0x8000000000000000)
        : i / 2 == 2 ? UINT64_C(0xc000000000000123) : 0;
    }
  else
    {
      uint64_t state = (uint64_t) (i - 6) + UINT64_C(0x13579bdf2468ace1);
      x.bits.mantissa = random_word (&state) | UINT64_C(0x8000000000000000);
      uint64_t e = random_word (&state);
      x.bits.exponent = e % 32767 + ((e >> 32 & 1) << 15);
      if (!(x.bits.exponent & 0x7fff)) x.bits.mantissa >>= 1;
    }
  return x.value;
}

static void *check (void *opaque)
{
  struct job *job = opaque;
#ifdef CBRTL_MODEL
  mpfr_t a, ref, error;
  mpfr_inits2 (192, a, ref, error, (mpfr_ptr) 0);
#endif
  for (unsigned i = first + job->id; i < last; i += workers)
    {
      long double x = input (i);
      extended got = {.value = __knc_cbrtl (x)};
#ifdef CBRTL_MODEL
      if (isfinite (x) && x != 0)
        {
          mpfr_set_ld (a, x, MPFR_RNDN);
          mpfr_cbrt (ref, a, MPFR_RNDN);
          mpfr_set_ld (a, got.value, MPFR_RNDN);
          mpfr_sub (error, a, ref, MPFR_RNDN);
          mpfr_abs (error, error, MPFR_RNDN);
          mpfr_mul_2si (error, error, 64 - mpfr_get_exp (ref), MPFR_RNDN);
          long double ulp = mpfr_get_ld (error, MPFR_RNDU);
          if (ulp > job->worst) job->worst = ulp;
          if (!(ulp <= 1)) ++job->failed;
        }
      else if (isnan (x) ? !isnan (got.value)
               : got.value != x || !!signbit (got.value) != !!signbit (x))
        ++job->failed;
      memcpy (expected + (size_t) i * 10, &got, 10);
#else
      if (memcmp (expected + (size_t) (i - first) * 10, &got, 10)) ++job->failed;
#endif
    }
#ifdef CBRTL_MODEL
  mpfr_clears (a, ref, error, (mpfr_ptr) 0);
#endif
  return NULL;
}

int main (int argc, char **argv)
{
#ifdef CBRTL_FAULT
  /* Deliberately bypass compiler redirection; run as a separate command. */
  extern long double unsafe_root (long double) __asm__ ("cbrtl");
  volatile long double x = 1e-5L;
  printf ("MPSS direct cbrtl(1e-5) = %La\n", unsafe_root (x));
  return 1; /* Reaching here did not reproduce the expected fault. */
#else
  if (argc < 2 || sizeof (long double) != 16 || __LDBL_MANT_DIG__ != 64)
    return 2;
#ifndef CBRTL_MODEL
  if (argc != 3 || strlen (argv[2]) != 1 || argv[2][0] < '0' || argv[2][0] > '3')
    return 2;
  first = (argv[2][0] - '0') * PART;
  last = first + PART < COUNT ? first + PART : COUNT;
#endif
  expected = malloc ((size_t) COUNT * 10);
  if (!expected) return 2;
#ifndef CBRTL_MODEL
  FILE *f = fopen (argv[1], "rb");
  if (!f || fread (expected, 10, last - first, f) != last - first || fgetc (f) != EOF)
    return 2;
  fclose (f);
  cpu_set_t cpus;
  if (sched_getaffinity (0, sizeof cpus, &cpus)) return 2;
  workers = CPU_COUNT (&cpus);
#else
  workers = 12;
#endif
  pthread_t *threads = calloc (workers, sizeof *threads);
  struct job *jobs = calloc (workers, sizeof *jobs);
  if (!workers || !threads || !jobs) return 2;
  for (unsigned j = 0; j < workers; ++j)
    { jobs[j].id = j; if (pthread_create (&threads[j], NULL, check, &jobs[j])) return 2; }
  unsigned failed = 0;
  long double worst = 0;
  for (unsigned j = 0; j < workers; ++j)
    {
      if (pthread_join (threads[j], NULL)) return 2;
      failed += jobs[j].failed;
      if (jobs[j].worst > worst) worst = jobs[j].worst;
    }
#ifdef CBRTL_MODEL
  for (unsigned part = 0; part < 4; ++part)
    {
      char name[1024];
      if (snprintf (name, sizeof name, "%s-%u.bin", argv[1], part) >= sizeof name) return 2;
      unsigned start = part * PART, n = COUNT - start < PART ? COUNT - start : PART;
      FILE *f = fopen (name, "wb");
      if (!f || fwrite (expected + (size_t) start * 10, 10, n, f) != n || fclose (f)) return 2;
    }
  printf ("MPFR 192-bit reference: worst error %.12Lf ULP\n", worst);
#endif
  printf ("cbrtl: %u inputs, %u workers, %u failures\n", last - first, workers, failed);
  free (threads); free (jobs); free (expected);
  return failed != 0;
#endif
}
#endif
