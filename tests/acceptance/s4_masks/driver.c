/* Sprint 4 acceptance driver: scalar references, bit-exact checks, guard
   pages.  Build at -O0 -fwrapv (never vectorized), link with loops.c.
   Prints "S4-MASKS PASS failures=0" and one INFO line; exit 0 only if every
   check passes.  */
#include <math.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include "masks.h"

#define MAXN 65
#define MAXO 16
static unsigned long checks, failures;
static long page;

/* A fault names the kernel and case, then exits 3 (the guard control's
   expected end).  */
static const char *cur = "setup";
static int cur_n, cur_o, cur_where;
static void
on_fault (int sig, siginfo_t *info, void *ctx)
{
  (void) ctx;
  printf ("S4-MASKS FAULT sig=%d kernel=%s n=%d o=%d where=%d addr=%p\n", sig,
          cur, cur_n, cur_o, cur_where, info->si_addr);
  fflush (stdout);
  _exit (3);
}
#define SET_CASE(NAME) (cur = (NAME), cur_n = n, cur_o = o, cur_where = where)

static void
fail (const char *what, int n, int i, int o)
{
  if (failures++ < 20)
    printf ("FAIL %s n=%d i=%d o=%d\n", what, n, i, o);
}

/* Deterministic inputs.  "bits" gives any pattern (selects and compares
   copy or compare bits); "exact" gives dyadic values whose sums are exact,
   so x87 extended precision cannot change a reference.  */
static uint64_t seed = 0x9e3779b97f4a7c15ull;
static uint64_t
rnd (void)
{
  seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17;
  return seed;
}
static const float fspecial[] = { 0.0f, -0.0f, 1.0f, -1.0f, INFINITY,
  -INFINITY, NAN, -NAN, 1e-45f, -1e-45f, 3.4e38f, -3.4e38f, 2.0f, 0.5f };
static const double dspecial[] = { 0.0, -0.0, 1.0, -1.0, INFINITY, -INFINITY,
  NAN, -NAN, 5e-324, -5e-324, 1.7e308, -1.7e308, 2.0, 0.5 };
#define NSPEC 14
static float
fbits (void)
{
  uint64_t r = rnd ();
  if (r % 3 == 0) return fspecial[(r >> 8) % NSPEC];
  if (r % 3 == 1) return (float) ((int) (r >> 20) % 7 - 3);  /* ties */
  float f; uint32_t u = (uint32_t) (r >> 16);
  memcpy (&f, &u, 4);
  if (isnan (f)) f = NAN;  /* no signalling NaN: x87 would quiet it */
  return f;
}
static double
dbits (void)
{
  uint64_t r = rnd ();
  if (r % 3 == 0) return dspecial[(r >> 8) % NSPEC];
  if (r % 3 == 1) return (double) ((int) (r >> 20) % 7 - 3);
  double d; uint64_t u = rnd ();
  memcpy (&d, &u, 8);
  if (isnan (d)) d = NAN;
  return d;
}
static double
exact (void)
{
  uint64_t r = rnd ();
  if (r % 11 == 0) return dspecial[(r >> 8) % 8];
  return (double) ((long) (r >> 8) % 2000 - 1000) / 8.0;
}
static long
lbits (void)
{
  static const long edge[] = { 0, 1, -1, 0xffffffffL, 0x100000000L,
    INT64_MAX, INT64_MIN, 0x7fffffffL, -0x80000000L };
  uint64_t r = rnd ();
  return r % 4 == 0 ? edge[(r >> 8) % 9] : (long) rnd ();
}

/* One guarded page per array: PROT_NONE pages on both sides.  "where"
   places n elements at element offset o from the low guard (where = 0) or
   ending o elements before the high guard (where = 1).  */
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
/* Sentinel window: SLACK bytes each side of the array (four vectors),
   clipped to the page.  */
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
  unsigned char *p = where ? b.lo + page - (n + o) * size : b.lo + o * size;
  unsigned char *lo = win_lo (b, p), *hi = win_hi (b, p, n * size);
  memset (lo, 0xA5, hi - lo);
  return p;
}
/* Every byte of the window outside [p, p + bytes) is still 0xA5.  */
static int
sentinels_ok (struct buf b, void *p, int bytes)
{
  unsigned char *s = p;
  for (unsigned char *q = win_lo (b, s); q < win_hi (b, s, bytes); q++)
    if ((q < s || q >= s + bytes) && *q != 0xA5)
      return 0;
  return 1;
}

static struct buf A, B, C, X, Y, M;

#define SAMEBITS(T, u, v) (memcmp (&(u), &(v), sizeof (T)) == 0)
#define NANEQ(u, v) (isnan (u) && isnan (v))

/* Compare kernels: every n and o, both guard sides.  */
#define CHECK_CMP(T, S, GEN, NAME, EXPR)                                      \
  for (int where = 0; where < 2; where++)                                     \
    for (int n = 0; n <= MAXN; n++)                                           \
      for (int o = 0; o < MAXO; o += (n > 20 ? 5 : 1))                        \
        {                                                                     \
          T *a = place (A, sizeof (T), n, o, where);                          \
          T *b = place (B, sizeof (T), n, o, where);                          \
          int *m = place (M, sizeof (int), n, o, where);                      \
          for (int i = 0; i < n; i++) { a[i] = GEN (); b[i] = GEN ();         \
                                        if (i % 5 == 0) b[i] = a[i]; }        \
          SET_CASE ("cmp_" #NAME "_" #S);                                     \
          cmp_##NAME##_##S (m, a, b, n);                                      \
          for (int i = 0; i < n; i++, checks++)                               \
            if (m[i] != (int) (EXPR)) fail ("cmp_" #NAME "_" #S, n, i, o);    \
          if (!sentinels_ok (M, m, n * sizeof (int)))                         \
            fail ("cmp_" #NAME "_" #S " wrote outside", n, -1, o);            \
        }
#define CHECK_CMPS(T, S, GEN)                                                 \
  CHECK_CMP (T, S, GEN, eq, a[i] == b[i]) CHECK_CMP (T, S, GEN, ne, a[i] != b[i]) \
  CHECK_CMP (T, S, GEN, lt, a[i] < b[i]) CHECK_CMP (T, S, GEN, le, a[i] <= b[i])  \
  CHECK_CMP (T, S, GEN, gt, a[i] > b[i]) CHECK_CMP (T, S, GEN, ge, a[i] >= b[i])

/* Element-wise kernels c = f(a, b, x, y): bit-exact reference REF into r;
   OK(u, v) decides equality.  */
#define CHECK_EW(T, S, GENA, GENB, NAME, CALL, REF, OK)                       \
  for (int where = 0; where < 2; where++)                                     \
    for (int n = 0; n <= MAXN; n++)                                           \
      for (int o = 0; o < MAXO; o += (n > 20 ? 5 : 1))                        \
        {                                                                     \
          T *a = place (A, sizeof (T), n, o, where);                          \
          T *b = place (B, sizeof (T), n, o, where);                          \
          T *x = place (X, sizeof (T), n, o, where);                          \
          T *y = place (Y, sizeof (T), n, o, where);                          \
          T *c = place (C, sizeof (T), n, o, where);                          \
          int *m = place (M, sizeof (int), n, o, where);                      \
          T old[MAXN + 1];                                                    \
          for (int i = 0; i < n; i++)                                         \
            { a[i] = GENA (); b[i] = GENB (); x[i] = GENB (); y[i] = GENB (); \
              c[i] = old[i] = GENB (); m[i] = (int) (rnd () & 1);             \
              if (i % 5 == 0) b[i] = a[i]; }                                  \
          SET_CASE (#NAME "_" #S);                                            \
          CALL;                                                               \
          for (int i = 0; i < n; i++, checks++)                               \
            {                                                                 \
              T r; REF;                                                       \
              if (!(OK)) fail (#NAME "_" #S, n, i, o);                        \
            }                                                                 \
          if (!sentinels_ok (C, c, n * sizeof (T)))                           \
            fail (#NAME "_" #S " wrote outside", n, -1, o);                   \
        }
#define BITS_OK(T) (SAMEBITS (T, c[i], r))
#define FP_OK(T) (SAMEBITS (T, c[i], r) || NANEQ (c[i], r))
/* fmin/fmax: C leaves the sign of a zero result and the NaN payload open.  */
#define FMINMAX_OK(T) (FP_OK (T) || (c[i] == 0 && r == 0))

#define CHECK_FP(T, S, GEN, U, SIGN)                                          \
  CHECK_CMPS (T, S, GEN)                                                      \
  CHECK_CMP (T, S, GEN, un, isunordered (a[i], b[i]))                         \
  CHECK_CMP (T, S, GEN, nlt, !(a[i] < b[i]))                                  \
  CHECK_EW (T, S, GEN, GEN, abs, abs_##S (c, a, n),                           \
            { U u; memcpy (&u, &a[i], sizeof u); u &= ~SIGN;                  \
              memcpy (&r, &u, sizeof r); }, BITS_OK (T))                      \
  CHECK_EW (T, S, GEN, GEN, minx, minx_##S (c, a, b, n),                      \
            { memcpy (&r, a[i] < b[i] ? &a[i] : &b[i], sizeof r); }, BITS_OK (T)) \
  CHECK_EW (T, S, GEN, GEN, maxx, maxx_##S (c, a, b, n),                      \
            { memcpy (&r, a[i] > b[i] ? &a[i] : &b[i], sizeof r); }, BITS_OK (T)) \
  CHECK_EW (T, S, GEN, GEN, fmin, fmin_##S (c, a, b, n),                      \
            { r = isnan (a[i]) ? b[i] : isnan (b[i]) ? a[i]                   \
                  : a[i] < b[i] ? a[i] : b[i]; }, FMINMAX_OK (T))             \
  CHECK_EW (T, S, GEN, GEN, fmax, fmax_##S (c, a, b, n),                      \
            { r = isnan (a[i]) ? b[i] : isnan (b[i]) ? a[i]                   \
                  : a[i] > b[i] ? a[i] : b[i]; }, FMINMAX_OK (T))

/* Selects copy bits; cadd/add/sub use exact inputs for FP.  */
#define CHECK_SEL(T, S, GEN, XGEN, OK)                                        \
  CHECK_EW (T, S, GEN, GEN, sel, sel_##S (c, a, b, x, y, n),                  \
            { memcpy (&r, a[i] > b[i] ? &x[i] : &y[i], sizeof r); }, BITS_OK (T)) \
  CHECK_EW (T, S, GEN, GEN, cst, cst_##S (c, a, x, n),                        \
            { memcpy (&r, a[i] > 0 ? &x[i] : &old[i], sizeof r); }, BITS_OK (T)) \
  CHECK_EW (T, S, XGEN, XGEN, cadd, cadd_##S (c, m, x, n),                    \
            { r = m[i] ? (T) (old[i] + x[i]) : old[i]; }, OK)                 \
  CHECK_EW (T, S, XGEN, XGEN, add, add_##S (c, a, b, n),                      \
            { r = (T) (a[i] + b[i]); }, OK)                                   \
  CHECK_EW (T, S, XGEN, XGEN, sub, sub_##S (c, a, b, n),                      \
            { r = (T) (a[i] - b[i]); }, OK)

/* Aligned placement (S4-05): the array starts on a 64-byte line and the line
   after its last element is the PROT_NONE page, so a masked tail that names
   one line too many faults.  Bytes between the last element and the page end
   share its line and are sentinel-checked.  */
static void *
place_al (struct buf b, int size, int n)
{
  int bytes = (n * size + 63) & ~63;
  unsigned char *p = b.lo + page - bytes;
  unsigned char *lo = win_lo (b, p), *hi = win_hi (b, p, n * size);
  memset (lo, 0xA5, hi - lo);
  return p;
}
#define CHECK_AL(T, S, GEN, NAME, CALL, REF, OK)                              \
  for (int n = 0; n <= MAXN; n++)                                             \
    {                                                                         \
      int o = 0, where = 2;                                                   \
      T *a = place_al (A, sizeof (T), n);                                     \
      T *b = place_al (B, sizeof (T), n);                                     \
      T *x = place_al (X, sizeof (T), n);                                     \
      T *c = place_al (C, sizeof (T), n);                                     \
      T old[MAXN + 1];                                                        \
      T ka = GEN (), kb = GEN ();                                             \
      for (int i = 0; i < n; i++)                                             \
        { a[i] = GEN (); b[i] = GEN (); x[i] = GEN (); c[i] = old[i] = GEN (); } \
      SET_CASE (#NAME "_" #S);                                                \
      CALL;                                                                   \
      for (int i = 0; i < n; i++, checks++)                                   \
        {                                                                     \
          T r; REF;                                                           \
          if (!(OK)) fail (#NAME "_" #S, n, i, o);                            \
        }                                                                     \
      if (!sentinels_ok (C, c, n * sizeof (T)))                               \
        fail (#NAME "_" #S " wrote outside", n, -1, o);                       \
      (void) ka; (void) kb;                                                   \
    }

static float fexact (void) { return (float) exact (); }
static int ibits (void) { return (int) rnd (); }
static unsigned ubits (void) { return (unsigned) rnd (); }

int
main (void)
{
  page = sysconf (_SC_PAGESIZE);
  setvbuf (stdout, 0, _IOLBF, 0);
  struct sigaction sa;
  memset (&sa, 0, sizeof sa);
  sa.sa_sigaction = on_fault;
  sa.sa_flags = SA_SIGINFO;
  sigaction (SIGSEGV, &sa, 0);
  sigaction (SIGBUS, &sa, 0);
  A = guarded (); B = guarded (); C = guarded (); X = guarded ();
  Y = guarded (); M = guarded ();

  CHECK_FP (float, f32, fbits, uint32_t, 0x80000000u)
  CHECK_FP (double, f64, dbits, uint64_t, 0x8000000000000000ull)
  CHECK_CMPS (int, i32, ibits)
  CHECK_CMPS (unsigned, u32, ubits)
  CHECK_CMPS (long, i64, lbits)
  CHECK_SEL (float, f32, fbits, fexact, FP_OK (float))
  CHECK_SEL (double, f64, dbits, exact, FP_OK (double))
  CHECK_SEL (int, i32, ibits, ibits, BITS_OK (int))
  CHECK_SEL (long, i64, lbits, lbits, BITS_OK (long))
  CHECK_EW (int, i32, ibits, ibits, mul, mul_i32 (c, a, b, n),
            { r = (int) ((unsigned) a[i] * (unsigned) b[i]); }, BITS_OK (int))
  CHECK_EW (int, i32, ibits, ibits, and, and_i32 (c, a, b, n),
            { r = a[i] & b[i]; }, BITS_OK (int))
  CHECK_EW (int, i32, ibits, ibits, or, or_i32 (c, a, b, n),
            { r = a[i] | b[i]; }, BITS_OK (int))
  CHECK_EW (int, i32, ibits, ibits, xor, xor_i32 (c, a, b, n),
            { r = a[i] ^ b[i]; }, BITS_OK (int))
  CHECK_EW (long, i64, lbits, lbits, and, and_i64 (c, a, b, n),
            { r = a[i] & b[i]; }, BITS_OK (long))
  CHECK_EW (long, i64, lbits, lbits, or, or_i64 (c, a, b, n),
            { r = a[i] | b[i]; }, BITS_OK (long))
  CHECK_EW (long, i64, lbits, lbits, xor, xor_i64 (c, a, b, n),
            { r = a[i] ^ b[i]; }, BITS_OK (long))

  CHECK_AL (float, f32, fexact, add_al, add_al_f32 (c, a, b, n),
            { r = (float) (a[i] + b[i]); }, FP_OK (float))
  CHECK_AL (double, f64, exact, add_al, add_al_f64 (c, a, b, n),
            { r = a[i] + b[i]; }, FP_OK (double))
  CHECK_AL (int, i32, ibits, add_al, add_al_i32 (c, a, b, n),
            { r = (int) ((unsigned) a[i] + (unsigned) b[i]); }, BITS_OK (int))
  CHECK_AL (float, f32, fexact, affine_al, affine_al_f32 (c, x, ka, kb, n),
            { r = (float) (ka * x[i] + kb); }, FP_OK (float))
  CHECK_AL (double, f64, exact, affine_al, affine_al_f64 (c, x, ka, kb, n),
            { r = ka * x[i] + kb; }, FP_OK (double))
  CHECK_AL (float, f32, fbits, cst_al, cst_al_f32 (c, a, x, n),
            { memcpy (&r, a[i] > 0 ? &x[i] : &old[i], sizeof r); }, BITS_OK (float))

  printf ("INFO checks=%lu\n", checks);
  if (failures)
    {
      printf ("S4-MASKS FAIL failures=%lu\n", failures);
      return 1;
    }
  printf ("S4-MASKS PASS failures=0\n");
  return 0;
}
