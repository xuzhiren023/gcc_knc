/* S8-02 (E4-04): masked loop tails and short masked loops against PROT_NONE
   pages on both sides of every array, at every element-aligned byte offset
   0-63 within a 64-byte line and at lengths 0-33 (runtime kernels), both
   with the array starting o bytes after the low guard and ending o bytes
   before the high guard.  Build the kernels with -DKNC_TAIL_LOOPS -O2
   -ftree-vectorize -fwrapv and the driver at -O0 -fwrapv (never vectorized);
   tools/s8_02_checks.py native builds, lints and stages the binaries under
   .work/_shared/S8-02.  The lead runs them on the card:
   knc-tail-guard.mic prints "S8-02-TAIL PASS failures=0 ..." and exits 0;
   knc-tail-guard-control{1,2,3}.mic (kernels built with -DGUARD_CONTROL=1,
   2 or 3: the gather tail and the whole-loop gather each read one element
   past the end; the aligned length-16 kernel reads one element past its
   last line) must die on a guard page and exit 3.  Control 3 cannot be an
   aligned masked over-read: an aligned masked access stays within its own
   64-byte line, so one element past an aligned array of 5 shares the line
   with elements 0-4 and never reaches the guard (lead, round 1).  It is
   the whole-vector access that crosses into the next line, with the array
   ending at the high guard.  A runtime mask of unknown alignment is chosen
   at run time (round 1): remainders and short lengths within C6's x87
   limit (lengths 1-3, 17-19, 33: lanes 0-2 only) move each active lane
   through a single-lane vloadunpackl/vpackstorel at the element's address,
   the others (4-15, 20-31) take the gather/scatter, so the sweep at offsets
   0-63 covers both paths against the guards.  Inputs are dyadic values with
   exact sums, so x87 extended precision in the reference cannot differ
   from the vector result.
   ADR-0007 point 7; ADR-0009 amendment 1 point 9; C6 in
   docs/research/knc-characterization.md.  */
#include <stddef.h>

#ifndef GUARD_CONTROL
#define GUARD_CONTROL 0
#endif
#define LOOP for (int i = 0; i < n; i++)
#define AL(p) __builtin_assume_aligned (p, 64)

void add_f32 (float *restrict, const float *restrict, const float *restrict, int);
void add_f64 (double *restrict, const double *restrict, const double *restrict, int);
void add_i32 (int *restrict, const int *restrict, const int *restrict, int);
void add_i64 (long *restrict, const long *restrict, const long *restrict, int);
void add_al_f32 (float *restrict, const float *restrict, const float *restrict, int);
void affine_f32 (float *restrict, const float *restrict, float, float, int);
void cst_f32 (float *restrict, const float *restrict, const float *restrict, int);
void small_f32 (float *restrict, const float *restrict, const float *restrict, unsigned);
void fix_f32_5 (float *restrict, const float *restrict, const float *restrict);
void fix_f32_13 (float *restrict, const float *restrict, const float *restrict);
void fix_f32_20 (float *restrict, const float *restrict, const float *restrict);
void fix_al_f32_5 (float *restrict, const float *restrict, const float *restrict);
void fix_al_f32_13 (float *restrict, const float *restrict, const float *restrict);
void fix_al_f32_16 (float *restrict, const float *restrict, const float *restrict);
void fix_al_f32_18 (float *restrict, const float *restrict, const float *restrict);
void fix_f64_5 (double *restrict, const double *restrict, const double *restrict);
void fix_al_f64_5 (double *restrict, const double *restrict, const double *restrict);

#ifdef KNC_TAIL_LOOPS
/* Runtime length, unknown alignment: the gather/scatter tail.  Control 1
   reads one element past the end of b.  */
void add_f32 (float *restrict c, const float *restrict a,
              const float *restrict b, int n)
{ LOOP c[i] = a[i] + b[i + (GUARD_CONTROL == 1)]; }
#define ADD(T, S)                                                         \
  void add_##S (T *restrict c, const T *restrict a, const T *restrict b,  \
                int n)                                                    \
  { LOOP c[i] = a[i] + b[i]; }
ADD (double, f64) ADD (int, i32) ADD (long, i64)

/* Runtime length, known alignment: the S4-05 aligned masked tail.  */
void add_al_f32 (float *restrict c, const float *restrict a,
                 const float *restrict b, int n)
{
  float *cc = AL (c); const float *aa = AL (a), *bb = AL (b);
  LOOP cc[i] = aa[i] + bb[i];
}

void affine_f32 (float *restrict c, const float *restrict x, float a,
                 float b, int n)
{ LOOP c[i] = a * x[i] + b; }

/* S4-14's conditional store through unknown alignment.  */
void cst_f32 (float *restrict c, const float *restrict a,
              const float *restrict x, int n)
{ LOOP if (a[i] > 0) c[i] = x[i]; }

/* A trip count known to stay below the vector length.  */
void small_f32 (float *restrict c, const float *restrict a,
                const float *restrict b, unsigned n)
{
  n &= 15;
  for (unsigned i = 0; i < n; i++) c[i] = a[i] + b[i];
}

/* Constant lengths: whole-loop masks (5, 13), a full vector plus a masked
   tail (20, 18), one full aligned vector (16).  Control 2 reads one element
   past the end of b; control 3 reads one element past the aligned line.  */
#define FIX(T, S, N, OVER)                                                \
  void fix_##S##_##N (T *restrict c, const T *restrict a,                 \
                      const T *restrict b)                                \
  { for (int i = 0; i < N; i++) c[i] = a[i] + b[i + (OVER)]; }
#define FIX_AL(T, S, N, OVER)                                             \
  void fix_al_##S##_##N (T *restrict c, const T *restrict a,              \
                         const T *restrict b)                             \
  {                                                                       \
    T *cc = AL (c); const T *aa = AL (a), *bb = AL (b);                   \
    for (int i = 0; i < N; i++) cc[i] = aa[i] + bb[i + (OVER)];           \
  }
FIX (float, f32, 5, GUARD_CONTROL == 2) FIX (float, f32, 13, 0)
FIX (float, f32, 20, 0)
FIX_AL (float, f32, 5, 0) FIX_AL (float, f32, 13, 0)
FIX_AL (float, f32, 16, GUARD_CONTROL == 3) FIX_AL (float, f32, 18, 0)
FIX (double, f64, 5, 0) FIX_AL (double, f64, 5, 0)
#else
#define _GNU_SOURCE 1
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#define MAXN 33
static unsigned long checks, failures;
static long page;

static const char *cur = "setup";
static int cur_n, cur_o, cur_where;
static void
on_fault (int sig, siginfo_t *info, void *ctx)
{
  (void) ctx;
  printf ("S8-02-TAIL FAULT sig=%d kernel=%s n=%d o=%d where=%d addr=%p\n",
          sig, cur, cur_n, cur_o, cur_where, info->si_addr);
  fflush (stdout);
  _exit (3);
}

static void
fail (const char *what, int n, int i, int o, int where)
{
  if (failures++ < 20)
    printf ("FAIL %s n=%d i=%d o=%d where=%d\n", what, n, i, o, where);
}

/* Dyadic values in [-125, 125] with three fraction bits: every sum, and
   every a * x + b with the affine constants below, is exact in float.  */
static uint64_t seed = 0x9e3779b97f4a7c15ull;
static uint64_t
rnd (void)
{
  seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17;
  return seed;
}
static double
exact (void)
{
  return (double) ((long) (rnd () >> 8) % 2001 - 1000) / 8.0;
}

/* One guarded page per array: PROT_NONE pages on both sides.  */
struct buf { unsigned char *lo; };
static struct buf
guarded (void)
{
  unsigned char *p = mmap (0, 3 * page, PROT_READ | PROT_WRITE,
                           MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (p == MAP_FAILED) { perror ("mmap"); _exit (2); }
  mprotect (p, page, PROT_NONE);
  mprotect (p + 2 * page, page, PROT_NONE);
  struct buf b = { p + page };
  return b;
}
/* n elements of SIZE bytes at byte offset O after the low guard (WHERE 0)
   or ending O bytes before the high guard (WHERE 1); the 256 bytes on each
   side, clipped to the page, are sentinels.  */
#define SLACK 256
static unsigned char *
win_lo (struct buf b, unsigned char *p)
{
  return p - b.lo > SLACK ? p - SLACK : b.lo;
}
static unsigned char *
win_hi (struct buf b, unsigned char *p, int bytes)
{
  return b.lo + page - (p + bytes) > SLACK ? p + bytes + SLACK : b.lo + page;
}
static void *
place (struct buf b, int size, int n, int o, int where)
{
  unsigned char *p = where ? b.lo + page - n * size - o : b.lo + o;
  unsigned char *lo = win_lo (b, p), *hi = win_hi (b, p, n * size);
  memset (lo, 0xA5, hi - lo);
  return p;
}
static int
sentinels_ok (struct buf b, void *p, int bytes)
{
  unsigned char *s = p;
  for (unsigned char *q = win_lo (b, s); q < win_hi (b, s, bytes); q++)
    if ((q < s || q >= s + bytes) && *q != 0xA5)
      return 0;
  return 1;
}

static struct buf A, B, C, X;

/* Every element-aligned byte offset o in a line, both guard sides, lengths
   LO..HI: c = REF (a, b) bit-exact, nothing written outside c.  */
#define SWEEP(T, S, NAME, LO, HI, CALL, REF)                                \
  for (int where = 0; where < 2; where++)                                   \
    for (int n = (LO); n <= (HI); n++)                                      \
      for (int o = 0; o < 64; o += sizeof (T))                              \
        {                                                                   \
          T *a = place (A, sizeof (T), n, o, where);                        \
          T *b = place (B, sizeof (T), n, o, where);                        \
          T *x = place (X, sizeof (T), n, o, where);                        \
          T *c = place (C, sizeof (T), n, o, where);                        \
          T old[MAXN + 1];                                                  \
          for (int i = 0; i < n; i++)                                       \
            { a[i] = GEN_##S (); b[i] = GEN_##S (); x[i] = GEN_##S ();      \
              c[i] = old[i] = GEN_##S (); }                                 \
          cur = #NAME; cur_n = n; cur_o = o; cur_where = where;             \
          CALL;                                                             \
          for (int i = 0; i < n; i++, checks++)                             \
            {                                                               \
              T r = (REF);                                                  \
              if (memcmp (&c[i], &r, sizeof (T)))                           \
                fail (#NAME, n, i, o, where);                               \
            }                                                               \
          if (!sentinels_ok (C, c, n * sizeof (T)))                         \
            fail (#NAME " wrote outside", n, -1, o, where);                 \
        }
#define GEN_f32() ((float) exact ())
#define GEN_f64() (exact ())
#define GEN_i32() ((int) rnd ())
#define GEN_i64() ((long) rnd ())
/* Aligned kernels: o must keep the 64-byte alignment the kernel assumes,
   so the sweep runs only o = 0 for them (place keeps n * size + o
   congruent to the page end, which is line aligned).  */
#define SWEEP_AL(T, S, NAME, LO, HI, CALL, REF)                             \
  for (int where = 0; where < 2; where++)                                   \
    for (int n = (LO); n <= (HI); n++)                                      \
      {                                                                     \
        int o = where ? (64 - n * sizeof (T) % 64) % 64 : 0;                \
        T *a = place (A, sizeof (T), n, o, where);                          \
        T *b = place (B, sizeof (T), n, o, where);                          \
        T *c = place (C, sizeof (T), n, o, where);                          \
        for (int i = 0; i < n; i++)                                         \
          { a[i] = GEN_##S (); b[i] = GEN_##S (); c[i] = GEN_##S (); }      \
        cur = #NAME; cur_n = n; cur_o = o; cur_where = where;               \
        CALL;                                                               \
        for (int i = 0; i < n; i++, checks++)                               \
          {                                                                 \
            T r = (REF);                                                    \
            if (memcmp (&c[i], &r, sizeof (T)))                             \
              fail (#NAME, n, i, o, where);                                 \
          }                                                                 \
        if (!sentinels_ok (C, c, n * sizeof (T)))                           \
          fail (#NAME " wrote outside", n, -1, o, where);                   \
      }

int
main (void)
{
  page = sysconf (_SC_PAGESIZE);
  if (page < 4096)
    return 2;
  struct sigaction sa;
  memset (&sa, 0, sizeof sa);
  sa.sa_sigaction = on_fault;
  sa.sa_flags = SA_SIGINFO;
  sigaction (SIGSEGV, &sa, 0);
  sigaction (SIGBUS, &sa, 0);
  A = guarded (); B = guarded (); C = guarded (); X = guarded ();

  SWEEP (float, f32, add_f32, 0, MAXN, add_f32 (c, a, b, n), a[i] + b[i]);
  SWEEP (double, f64, add_f64, 0, MAXN, add_f64 (c, a, b, n), a[i] + b[i]);
  SWEEP (int, i32, add_i32, 0, MAXN, add_i32 (c, a, b, n), a[i] + b[i]);
  SWEEP (long, i64, add_i64, 0, MAXN, add_i64 (c, a, b, n), a[i] + b[i]);
  SWEEP (float, f32, affine_f32, 0, MAXN, affine_f32 (c, a, 2.0f, 0.5f, n),
         2.0f * a[i] + 0.5f);
  SWEEP (float, f32, cst_f32, 0, MAXN, cst_f32 (c, a, x, n),
         a[i] > 0 ? x[i] : old[i]);
  SWEEP (float, f32, small_f32, 0, 15, small_f32 (c, a, b, n), a[i] + b[i]);
  SWEEP (float, f32, fix_f32_5, 5, 5, fix_f32_5 (c, a, b), a[i] + b[i]);
  SWEEP (float, f32, fix_f32_13, 13, 13, fix_f32_13 (c, a, b), a[i] + b[i]);
  SWEEP (float, f32, fix_f32_20, 20, 20, fix_f32_20 (c, a, b), a[i] + b[i]);
  SWEEP (double, f64, fix_f64_5, 5, 5, fix_f64_5 (c, a, b), a[i] + b[i]);
  SWEEP_AL (float, f32, add_al_f32, 0, MAXN, add_al_f32 (c, a, b, n),
            a[i] + b[i]);
  SWEEP_AL (float, f32, fix_al_f32_5, 5, 5, fix_al_f32_5 (c, a, b),
            a[i] + b[i]);
  SWEEP_AL (float, f32, fix_al_f32_13, 13, 13, fix_al_f32_13 (c, a, b),
            a[i] + b[i]);
  SWEEP_AL (float, f32, fix_al_f32_16, 16, 16, fix_al_f32_16 (c, a, b),
            a[i] + b[i]);
  SWEEP_AL (float, f32, fix_al_f32_18, 18, 18, fix_al_f32_18 (c, a, b),
            a[i] + b[i]);
  SWEEP_AL (double, f64, fix_al_f64_5, 5, 5, fix_al_f64_5 (c, a, b),
            a[i] + b[i]);

  printf ("S8-02-TAIL %s failures=%lu checks=%lu control=%d\n",
          failures ? "FAIL" : "PASS", failures, checks, GUARD_CONTROL);
  return failures != 0;
}
#endif
