/* Card check for S3-04 and S3-05: 64-byte packed copies on KNC.

   Uses only copies, zero and constants of the four packed types (no
   vector arithmetic), so it tests storage: aligned moves, pool constants,
   unaligned load/store pairs at every element offset, pairs flush against
   an unmapped guard page, and vectors live across calls at four stack
   alignments.  Prints one summary line; exit 0 only if every case passes.

   Build: xgcc -B<build>/gcc/ -O0|-O2 -march=knc vec_card.c -o vec_card.  */

#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

static unsigned long cases, failures;

static void
fail (const char *what, int type, int a, int b)
{
  if (failures++ < 20)
    printf ("FAIL %s type=%d a=%d b=%d\n", what, type, a, b);
}

/* Opaque call: the compiler must keep live vectors across it.  */
__attribute__ ((noipa)) static void
opaque (void)
{
  __asm__ volatile ("" ::: "memory");
}

/* -DBROKEN_ALIGN is the negative control: the "unaligned" type claims
   64-byte alignment, so GCC emits aligned moves on unaligned addresses,
   which must fault on the card.  */
#ifdef BROKEN_ALIGN
#define U_TYPEDEF(ID, T) typedef v##ID u##ID;
#else
#define U_TYPEDEF(ID, T) typedef v##ID u##ID __attribute__ ((aligned (sizeof (T))));
#endif

#define SENT 0xA5
#define DEFINE_TYPE(ID, T, N)                                                 \
  typedef T v##ID __attribute__ ((vector_size (64)));                         \
  U_TYPEDEF (ID, T)                                                           \
                                                                              \
  __attribute__ ((noipa)) static void                                      \
  copy_a_##ID (v##ID *d, const v##ID *s)                                      \
  {                                                                           \
    *d = *s;                                                                  \
  }                                                                           \
  __attribute__ ((noipa)) static void                                      \
  copy_u_##ID (u##ID *d, const u##ID *s)                                      \
  {                                                                           \
    *d = *s;                                                                  \
  }                                                                           \
  __attribute__ ((noipa)) static void                                      \
  zero_##ID (v##ID *d)                                                        \
  {                                                                           \
    *d = (v##ID){ 0 };                                                        \
  }                                                                           \
  __attribute__ ((noipa)) static void                                      \
  konst_##ID (v##ID *d)                                                       \
  {                                                                           \
    *d = (v##ID){ 1, 2, 3, 4, 5, 6, 7, 8 };                                   \
  }                                                                           \
  /* Load, keep live across a call, store.  */                                \
  __attribute__ ((noipa)) static void                                      \
  across_##ID (u##ID *d, const u##ID *s)                                      \
  {                                                                           \
    v##ID x = *s;                                                             \
    opaque ();                                                                \
    v##ID y = *s;                                                             \
    opaque ();                                                                \
    *d = x;                                                                   \
    d[1] = y;                                                                 \
  }                                                                           \
  __attribute__ ((noipa)) static void                                      \
  across_at_##ID (int pad, u##ID *d, const u##ID *s)                          \
  {                                                                           \
    volatile char *p = __builtin_alloca (pad + 1);                            \
    p[0] = 0;                                                                 \
    across_##ID (d, s);                                                       \
  }                                                                           \
                                                                              \
  static void                                                                 \
  check_##ID (int type, unsigned char *page)                                  \
  {                                                                           \
    static v##ID as, ad;                                                      \
    T want[N];                                                                \
    for (int i = 0; i < N; i++)                                               \
      want[i] = (T) (i * 3 + 1);                                              \
    memcpy (&as, want, 64);                                                   \
    memset (&ad, 0, 64);                                                      \
    copy_a_##ID (&ad, &as);                                                   \
    cases++;                                                                  \
    if (memcmp (&ad, want, 64))                                               \
      fail ("aligned", type, 0, 0);                                           \
    memset (&ad, SENT, 64);                                                   \
    zero_##ID (&ad);                                                          \
    {                                                                         \
      unsigned char z[64] = { 0 };                                            \
      cases++;                                                                \
      if (memcmp (&ad, z, 64))                                                \
        fail ("zero", type, 0, 0);                                            \
    }                                                                         \
    konst_##ID (&ad);                                                         \
    {                                                                         \
      T k[N] = { 1, 2, 3, 4, 5, 6, 7, 8 };                                    \
      cases++;                                                                \
      if (memcmp (&ad, k, 64))                                                \
        fail ("constant", type, 0, 0);                                        \
    }                                                                         \
    /* Unaligned: every source and destination element offset.  */           \
    static unsigned char sbuf[64 * 4] __attribute__ ((aligned (64)));         \
    static unsigned char dbuf[64 * 4] __attribute__ ((aligned (64)));         \
    for (int so = 0; so < N; so++)                                            \
      for (int doff = 0; doff < N; doff++)                                    \
        {                                                                     \
          memset (sbuf, 0, sizeof sbuf);                                      \
          memset (dbuf, SENT, sizeof dbuf);                                   \
          memcpy (sbuf + 64 + so * sizeof (T), want, 64);                     \
          unsigned char *dst = dbuf + 64 + doff * sizeof (T);                 \
          copy_u_##ID ((u##ID *) dst, (const u##ID *) (sbuf + 64              \
                                                      + so * sizeof (T)));    \
          cases++;                                                            \
          int bad = memcmp (dst, want, 64) != 0;                              \
          for (unsigned char *q = dbuf; q < dbuf + sizeof dbuf; q++)          \
            if ((q < dst || q >= dst + 64) && *q != SENT)                     \
              bad = 1;                                                        \
          if (bad)                                                            \
            fail ("unaligned", type, so, doff);                               \
        }                                                                     \
    /* Flush against the guard page after PAGE, and right after the guard   \
       page before PAGE: data wholly mapped must never fault.  */            \
    long ps = sysconf (_SC_PAGESIZE);                                         \
    for (int k = 0; k < N; k++)                                               \
      {                                                                       \
        unsigned char *end = page + ps - 64 - k * sizeof (T);                 \
        unsigned char *beg = page + k * sizeof (T);                           \
        memcpy (end, want, 64);                                               \
        copy_u_##ID ((u##ID *) beg, (const u##ID *) end);                     \
        cases++;                                                              \
        if (memcmp (beg, want, 64))                                           \
          fail ("guard-load", type, k, 0);                                    \
        memset (end, 0, 64);                                                  \
        copy_u_##ID ((u##ID *) end, (const u##ID *) beg);                     \
        cases++;                                                              \
        if (memcmp (end, want, 64))                                           \
          fail ("guard-store", type, k, 0);                                   \
      }                                                                       \
    /* Live across calls, at four stack alignments, aligned and not.  */     \
    for (int pad = 0; pad < 64; pad += 16)                                    \
      for (int off = 0; off < 2; off++)                                       \
        {                                                                     \
          memset (sbuf, 0, sizeof sbuf);                                      \
          memset (dbuf, SENT, sizeof dbuf);                                   \
          memcpy (sbuf + off * sizeof (T), want, 64);                         \
          across_at_##ID (pad, (u##ID *) (dbuf + off * sizeof (T)),           \
                          (const u##ID *) (sbuf + off * sizeof (T)));         \
          cases++;                                                            \
          if (memcmp (dbuf + off * sizeof (T), want, 64)                      \
              || memcmp (dbuf + off * sizeof (T) + 64, want, 64))             \
            fail ("across-call", type, pad, off);                             \
        }                                                                     \
  }

DEFINE_TYPE (sf, float, 16)
DEFINE_TYPE (df, double, 8)
DEFINE_TYPE (si, int, 16)
DEFINE_TYPE (di, long long, 8)

int
main (void)
{
  long ps = sysconf (_SC_PAGESIZE);
  unsigned char *map = mmap (0, 3 * ps, PROT_READ | PROT_WRITE,
                             MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (map == MAP_FAILED || mprotect (map, ps, PROT_NONE)
      || mprotect (map + 2 * ps, ps, PROT_NONE))
    {
      printf ("SETUP FAIL\n");
      return 2;
    }
  unsigned char *page = map + ps;
  check_sf (0, page);
  check_df (1, page);
  check_si (2, page);
  check_di (3, page);
  printf ("S3-VEC %s cases=%lu failures=%lu\n", failures ? "FAIL" : "PASS",
          cases, failures);
  return failures != 0;
}
