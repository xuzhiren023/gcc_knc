/* S5-01: card probe for the facts Intel 327364-001 leaves open about
   VGATHERDPS/PD, VPGATHERDD/DQ (pp.297-302, 484-488), VSCATTERDPS/PD,
   VPSCATTERDD/DQ (pp.530-535, 595-600) and VGMAXPS/PD, VGMINPS/PD,
   VGMAXABSPS (pp.329-348).  See docs/research/knc-gather-reduce.md.
   Every instruction is inline asm; the compiler emits no vector code.

   Host: compile only.  From the repository root (Git Bash; from a ticket
   worktree root, read ../_shared for .work/_shared):
     T=.work/_shared/toolchain B=.work/_shared/gcc-build/gcc
     mkdir -p .work/_shared/tmp/S5-01
     PATH=$T/cross/bin:$T/cygwin/bin:$PATH $B/xgcc -B$B/ -march=knc -O0 \
       -std=gnu99 -Wall -Wextra -Werror -Wa,--march=k1om \
       tests/regress/knc-gather-probe.c -lm \
       -o .work/_shared/tmp/S5-01/knc-gather-probe.mic
   Card (lead, through tools/card_run only, 64 MiB):
     knc-gather-probe.mic --native
   Each line ends in check=ok, FAIL (contradicts the manual or a fact GCC
   relies on) or INFO (the manual is silent; the line is the observation).
   Exit status 1 when any line is FAIL.  */
#define _GNU_SOURCE 1
#include <math.h>
#include <setjmp.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

enum { PS, PD, D, Q };
static const char *const gname[] = { "vgatherdps", "vgatherdpd", "vpgatherdd", "vpgatherdq" };
static const char *const sname[] = { "vscatterdps", "vscatterdpd", "vpscatterdd", "vpscatterdq" };
static int esize (int f) { return (f & 1) ? 8 : 4; }
static int lanes (int f) { return 64 / esize (f); }
static unsigned full (int f) { return (1u << lanes (f)) - 1; }

static long page;
static unsigned char *memory;   /* one RW page between two PROT_NONE pages */
static unsigned char *guard;    /* memory + page: the upper PROT_NONE page */
static int32_t idx[16] __attribute__ ((aligned (64)));
static unsigned char vin[64] __attribute__ ((aligned (64)));  /* old value or store data */
static unsigned char vout[64] __attribute__ ((aligned (64)));
static unsigned char *image, *gimage;
static int failures;

enum { OFF, JUMP, RESUME };
static sigjmp_buf recovery;
static volatile sig_atomic_t mode, faults;
static unsigned char *volatile fault_addr;

/* JUMP abandons the instruction.  RESUME makes the upper guard page
   readable and writable and returns, so the instruction is re-executed.  */
static void handler (int sig, siginfo_t *info, void *context)
{
  unsigned char *a = info->si_addr;
  (void) context;
  if (mode == JUMP)
    {
      ++faults;
      fault_addr = a;
      siglongjmp (recovery, 1);
    }
  if (mode == RESUME && a >= guard && a < guard + page && faults < 8)
    {
      if (!faults++)
        fault_addr = a;
      if (mprotect (guard, (size_t) page, PROT_READ | PROT_WRITE))
        _exit (3);
      return;
    }
  _exit (128 + sig);
}

static void reset_guard (void)
{
  if (mprotect (guard, (size_t) page, PROT_READ | PROT_WRITE))
    exit (2);
  memset (guard, 0, (size_t) page);
  if (mprotect (guard, (size_t) page, PROT_NONE))
    exit (2);
}

static int guard_open;   /* set when a RESUME fault left the guard RW */

static void fill_memory (void)
{
  long i;
  for (i = 0; i < page / 4; ++i)
    {
      uint32_t w = 0x3f800000u + (uint32_t) i * 0x100u;  /* normal floats */
      memcpy (memory + 4 * i, &w, 4);
    }
}

static void fill_data (int f)
{
  int l;
  for (l = 0; l < lanes (f); ++l)
    if (esize (f) == 4)
      {
        uint32_t w = 0x40000000u + (uint32_t) l * 0x10101u;
        memcpy (vin + 4 * l, &w, 4);
      }
    else
      {
        uint64_t w = UINT64_C (0x4000000000000000) + (uint64_t) l * 0x1010101u;
        memcpy (vin + 8 * l, &w, 8);
      }
}

/* The loop the manual prescribes (p.297): re-execute until k1 is clear.
   An 8-lane form zeroes k1[15:8] itself (p.298), so jknzd is exact.
   The count is capped at 64 executions.  */
#define LOOP_TAIL \
  "addl $1, %[it]\n\t" "cmpl $64, %[it]\n\t" "jae 2f\n\t" \
  "jknzd 1b, %%k1\n" "2:\n\t" "kmov %%k1, %[ko]\n\t"
#define GATHER(insn, scale) \
  __asm__ volatile ("vmovdqa32 (%[old]), %%zmm0\n\t" \
                    "vmovdqa32 (%[ix]), %%zmm1\n\t" \
                    "kmov %[m], %%k1\n\t" "xorl %[it], %[it]\n" "1:\n\t" \
                    insn " (%[b],%%zmm1," scale "), %%zmm0%{%%k1%}\n\t" \
                    LOOP_TAIL "vmovdqa32 %%zmm0, (%[out])" \
    : [it] "=&r" (it), [ko] "=&r" (ko) \
    : [old] "r" (vin), [ix] "r" (idx), [m] "r" (mask), [b] "r" (base), \
      [out] "r" (vout) \
    : "zmm0", "zmm1", "k1", "memory", "cc")
#define SCATTER(insn, scale) \
  __asm__ volatile ("vmovdqa32 (%[src]), %%zmm0\n\t" \
                    "vmovdqa32 (%[ix]), %%zmm1\n\t" \
                    "kmov %[m], %%k1\n\t" "xorl %[it], %[it]\n" "1:\n\t" \
                    insn " %%zmm0, (%[b],%%zmm1," scale ")%{%%k1%}\n\t" \
                    LOOP_TAIL \
    : [it] "=&r" (it), [ko] "=&r" (ko) \
    : [src] "r" (vin), [ix] "r" (idx), [m] "r" (mask), [b] "r" (base) \
    : "zmm0", "zmm1", "k1", "memory", "cc")

static unsigned iterations, final_mask;

__attribute__ ((noinline)) static void run (int f, int store, unsigned char *base,
                                           unsigned mask)
{
  unsigned it = 0, ko = 0;
  if (!store)
    switch (f)
      {
      case PS: GATHER ("vgatherdps", "4"); break;
      case PD: GATHER ("vgatherdpd", "8"); break;
      case D: GATHER ("vpgatherdd", "4"); break;
      default: GATHER ("vpgatherdq", "8"); break;
      }
  else
    switch (f)
      {
      case PS: SCATTER ("vscatterdps", "4"); break;
      case PD: SCATTER ("vscatterdpd", "8"); break;
      case D: SCATTER ("vpscatterdd", "4"); break;
      default: SCATTER ("vpscatterdq", "8"); break;
      }
  iterations = it;
  final_mask = ko;
}

/* Returns nonzero when a fault was taken.  */
static int guarded (int f, int store, unsigned char *base, unsigned mask, int how)
{
  faults = 0;
  fault_addr = NULL;
  iterations = final_mask = 0xdead;
  if (sigsetjmp (recovery, 1) == 0)
    {
      mode = how;
      run (f, store, base, mask);
    }
  mode = OFF;
  guard_open = how == RESUME && faults;
  return faults != 0;
}

static unsigned char *target (int f, unsigned char *base, int l)
{
  return base + (intptr_t) idx[l] * esize (f);   /* address width, then scale */
}

static void report (const char *group, const char *name, int f, int store,
                    const char *what, unsigned mask, const char *check,
                    const char *detail)
{
  long off = fault_addr ? (long) (fault_addr - guard) : 0;
  printf ("S5-01 group=%s form=%s case=%s mask=0x%04x faults=%d fault_off=%ld "
          "iterations=%u final_mask=0x%04x %s check=%s\n", group,
          store ? sname[f] : gname[f], what ? what : name, mask, (int) faults,
          off, iterations, final_mask, detail ? detail : "", check);
  if (!strcmp (check, "FAIL"))
    ++failures;
}

/* Gather: expected lanes from memory (the upper guard reads as zero once a
   RESUME fault opened it); inactive lanes keep the old value (p.297).  */
static int gather_bad (int f, unsigned char *base, unsigned mask)
{
  int l, es = esize (f);
  unsigned char want[64];
  memcpy (want, vin, 64);
  for (l = 0; l < lanes (f); ++l)
    if (mask & (1u << l))
      {
        unsigned char *a = target (f, base, l);
        if (a >= guard && a < guard + page)
          memset (want + l * es, 0, es);
        else
          memcpy (want + l * es, a, es);
      }
  return memcmp (want, vout, 64) != 0;
}

static void gather_case (const char *what, int f, unsigned char *base,
                         unsigned mask, int how, int expect_fault)
{
  int fault;
  fill_memory ();
  memset (vout, 0, 64);
  fault = guarded (f, 0, base, mask, how);
  report ("gather", NULL, f, 0, what, mask,
          fault != expect_fault || gather_bad (f, base, mask) ? "FAIL" : "ok", NULL);
  if (guard_open)
    reset_guard ();
}

/* Scatter: lanes in LSB-to-MSB order, so the highest duplicate wins
   (pp.530, 595, 598).  IMAGE and GIMAGE model the page and upper guard.  */
static void scatter_model (int f, unsigned char *base, unsigned mask)
{
  int l, es = esize (f);
  memset (image, 0xa5, (size_t) page);
  memset (gimage, 0, (size_t) page);
  for (l = 0; l < lanes (f); ++l)
    if (mask & (1u << l))
      {
        unsigned char *a = target (f, base, l);
        if (a >= memory && a < memory + page)
          memcpy (image + (a - memory), vin + l * es, es);
        else if (a >= guard && a < guard + page)
          memcpy (gimage + (a - guard), vin + l * es, es);
      }
}

/* After an abandoned scatter: every changed byte must belong to an active
   lane's element and hold that lane's byte.  STORED gets the lanes whose
   whole element is present.  */
static int scatter_partial_bad (int f, unsigned char *base, unsigned mask,
                                unsigned *stored)
{
  long i;
  int l, es = esize (f), bad = 0;
  *stored = 0;
  for (i = 0; i < page; ++i)
    if (memory[i] != 0xa5)
      {
        int ok = 0;
        for (l = 0; l < lanes (f); ++l)
          if ((mask & (1u << l)) && memory + i >= target (f, base, l)
              && memory + i < target (f, base, l) + es
              && memory[i] == vin[l * es + (memory + i - target (f, base, l))])
            ok = 1;
        bad += !ok;
      }
  for (l = 0; l < lanes (f); ++l)
    if ((mask & (1u << l)) && target (f, base, l) >= memory
        && target (f, base, l) < memory + page
        && !memcmp (target (f, base, l), vin + l * es, es))
      *stored |= 1u << l;
  return bad;
}

static void scatter_case (const char *what, int f, unsigned char *base,
                          unsigned mask, int how, int expect_fault)
{
  char detail[64] = "";
  const char *check = "ok";
  int fault;
  fill_data (f);
  memset (memory, 0xa5, (size_t) page);
  scatter_model (f, base, mask);
  fault = guarded (f, 1, base, mask, how);
  if (fault != expect_fault)
    check = "FAIL";
  else if (how == JUMP && fault)
    {
      unsigned stored;
      check = scatter_partial_bad (f, base, mask, &stored) ? "FAIL" : "INFO";
      snprintf (detail, sizeof detail, "stored_lanes=0x%04x", stored);
    }
  else if (memcmp (memory, image, (size_t) page)
           || (guard_open && memcmp (guard, gimage, (size_t) page)))
    check = "FAIL";
  report ("scatter", NULL, f, 1, what, mask, check, detail);
  if (guard_open)
    reset_guard ();
}

static void set_idx (int f, int stride, int first)
{
  int l;
  for (l = 0; l < 16; ++l)
    idx[l] = first + l * stride;
  if (lanes (f) == 8)       /* dwords 15:8 are not indices (p.298): point */
    for (l = 8; l < 16; ++l) /* them at the guard to show they are ignored */
      idx[l] = (int32_t) (page / esize (f)) + l;
}

static void memory_cases (int f, int store)
{
  int L = lanes (f), es = esize (f), in_guard = (int) (page / es), j;
  int mids[3] = { 0, L / 2, L - 1 };
  char name[48];
  void (*one) (const char *, int, unsigned char *, unsigned, int, int)
    = store ? scatter_case : gather_case;

  set_idx (f, 5, 3);
  one ("all-active", f, memory, full (f), JUMP, 0);
  for (j = 0; j < 3; ++j)
    {
      int m = mids[j];
      set_idx (f, 5, 3);
      idx[m] = in_guard;
      snprintf (name, sizeof name, "masked-off-upper-guard-lane%d", m);
      one (name, f, memory, full (f) & ~(1u << m), JUMP, 0);
      idx[m] = -64 / es;
      snprintf (name, sizeof name, "masked-off-lower-guard-lane%d", m);
      one (name, f, memory, full (f) & ~(1u << m), JUMP, 0);
    }
  set_idx (f, 0, in_guard);
  one ("empty-mask-all-guard", f, memory, 0, JUMP, 0);
  set_idx (f, 5, 3);
  idx[0] = in_guard - 1;
  one ("last-element-of-page", f, memory, full (f), JUMP, 0);
  /* A fault on active lane m.  The handler opens the page and returns, as
     demand paging does; the result must be complete and correct.  */
  for (j = 0; j < 3; ++j)
    {
      int m = mids[j];
      set_idx (f, 5, 3);
      idx[m] = in_guard + m;
      snprintf (name, sizeof name, "fault-lane%d-resume", m);
      one (name, f, memory, full (f), RESUME, 1);
      if (store)
        {
          snprintf (name, sizeof name, "fault-lane%d-abandon", m);
          one (name, f, memory, full (f), JUMP, 1);
        }
    }
}

static void duplicate_cases (int f)
{
  int L = lanes (f), es = esize (f), l;
  set_idx (f, 0, 7);
  scatter_case ("dup-all-same", f, memory, full (f), JUMP, 0);
  scatter_case ("dup-all-same-mask-5555", f, memory, full (f) & 0x5555, JUMP, 0);
  for (l = 0; l < L; ++l)
    idx[l] = (l & 1 ? 512 : 128) / es;
  scatter_case ("dup-two-lines", f, memory, full (f), JUMP, 0);
  for (l = 0; l < L; ++l)
    idx[l] = ((l % 4) * 256 + 64) / es;
  scatter_case ("dup-four-lines", f, memory, full (f), JUMP, 0);
  /* Lanes 0 and 2 share an element; lane 1 faults between them.  */
  set_idx (f, 0, 128 / es);
  idx[1] = (int32_t) (page / es);
  scatter_case ("dup-around-fault-resume", f, memory, 7, RESUME, 1);
  scatter_case ("dup-around-fault-abandon", f, memory, 7, JUMP, 1);
}

/* p.300 prints mvt[n] = BASE + SignExtend(VINDEX * SCALE).  GCC's
   gather_load extends first, then scales (md.texi).  BIG * scale = 2^31:
   address width gives MEMORY, a 32-bit product gives MEMORY - 2^32.  */
static void index_cases (int f)
{
  int es = esize (f);
  intptr_t big = (intptr_t) 1 << (31 - (es == 8 ? 3 : 2));
  unsigned char *base = (unsigned char *) ((uintptr_t) memory - ((uintptr_t) big * es));
  char detail[96];
  const char *how;
  int fault;
  set_idx (f, 0, 0);
  idx[0] = (int32_t) big;
  fill_memory ();
  memset (vout, 0, 64);
  fault = guarded (f, 0, base, 1, JUMP);
  if (fault)
    how = fault_addr == memory - ((uintptr_t) 1 << 32) ? "32-bit-product" : "fault-elsewhere";
  else
    how = memcmp (vout, memory, es) ? "other-data" : "address-width";
  snprintf (detail, sizeof detail, "index=0x%08x scale=%d semantics=%s",
            (unsigned) idx[0], es, how);
  report ("index", NULL, f, 0, "scaled-index-2^31", 1, "INFO", detail);
  set_idx (f, 0, 0);
  idx[0] = -16;   /* signed dword index (p.297 title, p.44 VSIB) */
  gather_case ("negative-index", f, memory + 16 * es, 1, JUMP, 0);
}

/* VGMAXPS p.338, VGMINPS p.346, VGMAXPD p.334, VGMINPD p.342,
   VGMAXABSPS p.330: the pseudocode, transcribed.  */
static int isnan_bits (uint64_t b, int dbl)
{
  return dbl ? (b & ~(UINT64_C (1) << 63)) > UINT64_C (0x7ff0000000000000)
             : (b & 0x7fffffffu) > 0x7f800000u;
}
static double value (uint64_t b, int dbl)
{
  float s;
  double d;
  uint32_t w = (uint32_t) b;
  if (dbl) { memcpy (&d, &b, 8); return d; }
  memcpy (&s, &w, 4);
  return s;
}
static uint64_t model (int op, uint64_t a, uint64_t b, int dbl)
{
  uint64_t sign = dbl ? UINT64_C (1) << 63 : 0x80000000u;
  uint64_t inf = dbl ? UINT64_C (0x7ff0000000000000) : 0x7f800000u;
  int na = isnan_bits (a, dbl), nb = isnan_bits (b, dbl);
  if (op == 2)    /* FpMaxAbs */
    {
      if (na && nb) return a & ~sign;
      if (na) return b & ~sign;
      if (nb) return a & ~sign;
      if ((a & ~sign) == inf || (b & ~sign) == inf) return inf;
      return fabs (value (a, dbl)) >= fabs (value (b, dbl)) ? a & ~sign : b & ~sign;
    }
  if (a == sign && b == 0) return op ? a : b;
  if (a == 0 && b == sign) return op ? b : a;
  if (na && nb) return a;
  if (na) return b;
  if (nb) return a;
  if (a == (inf | sign)) return op ? a : b;
  if (b == (inf | sign)) return op ? b : a;
  if (a == inf) return op ? b : a;
  if (b == inf) return op ? a : b;
  if (op)
    return value (a, dbl) < value (b, dbl) ? a : b;
  return value (a, dbl) >= value (b, dbl) ? a : b;
}

static const uint32_t fa[16] = {
  0x80000000, 0x00000000, 0x7fc00001, 0x3f800000, 0x7fc00001, 0x7f800001,
  0x3f800000, 0x7f800001, 0xbf800000, 0x40000000, 0xff800000, 0x7f800000,
  0xc0400000, 0x80000000, 0x00000000, 0xffc00003 };
static const uint32_t fb[16] = {
  0x00000000, 0x80000000, 0x3f800000, 0x7fc00001, 0x7fc00002, 0x3f800000,
  0x7f800001, 0x7fc00002, 0x40000000, 0xbf800000, 0xc0000000, 0x7fc00001,
  0x40000000, 0x80000000, 0x00000000, 0xc0a00000 };
static const uint64_t da[8] = {
  UINT64_C (0x8000000000000000), 0, UINT64_C (0x7ff8000000000001),
  UINT64_C (0x3ff0000000000000), UINT64_C (0x7ff8000000000001),
  UINT64_C (0x7ff0000000000001), UINT64_C (0x3ff0000000000000),
  UINT64_C (0xc008000000000000) };
static const uint64_t db[8] = {
  0, UINT64_C (0x8000000000000000), UINT64_C (0x3ff0000000000000),
  UINT64_C (0x7ff8000000000001), UINT64_C (0x7ff8000000000002),
  UINT64_C (0x3ff0000000000000), UINT64_C (0x7ff0000000000001),
  UINT64_C (0x4000000000000000) };

static unsigned char ra[64] __attribute__ ((aligned (64)));
static unsigned char rb[64] __attribute__ ((aligned (64)));
static unsigned char rr[64] __attribute__ ((aligned (64)));
#define MINMAX(insn) \
  __asm__ volatile ("vmovaps (%[a]), %%zmm1\n\t" "vmovaps (%[b]), %%zmm2\n\t" \
                    insn " %%zmm2, %%zmm1, %%zmm0\n\t" "vmovaps %%zmm0, (%[r])" \
                    : : [a] "r" (ra), [b] "r" (rb), [r] "r" (rr) \
                    : "zmm0", "zmm1", "zmm2", "memory")

static void minmax_case (const char *insn, int op, int dbl)
{
  int l, n = dbl ? 8 : 16, es = dbl ? 8 : 4;
  memcpy (ra, dbl ? (const void *) da : (const void *) fa, 64);
  memcpy (rb, dbl ? (const void *) db : (const void *) fb, 64);
  if (!strcmp (insn, "vgmaxps")) MINMAX ("vgmaxps");
  else if (!strcmp (insn, "vgminps")) MINMAX ("vgminps");
  else if (!strcmp (insn, "vgmaxpd")) MINMAX ("vgmaxpd");
  else if (!strcmp (insn, "vgminpd")) MINMAX ("vgminpd");
  else MINMAX ("vgmaxabsps");
  for (l = 0; l < n; ++l)
    {
      uint64_t a = 0, b = 0, r = 0, m, c = 0;
      int zeros;
      memcpy (&a, ra + l * es, es);
      memcpy (&b, rb + l * es, es);
      memcpy (&r, rr + l * es, es);
      m = model (op, a, b, dbl);
      /* libm on the card, for comparison with C fmin/fmax.  */
      if (op != 2)
        {
          volatile double x = value (a, dbl), y = value (b, dbl);
          if (dbl) { double z = op ? fmin (x, y) : fmax (x, y); memcpy (&c, &z, 8); }
          else { float z = op ? fminf ((float) x, (float) y) : fmaxf ((float) x, (float) y);
                 memcpy (&c, &z, 4); }
        }
      {
        uint64_t mag = dbl ? ~(UINT64_C (1) << 63) : 0x7fffffffu;
        zeros = !(a & mag) && !(b & mag) && a != b;   /* -0 against +0 */
      }
      printf ("S5-01 group=minmax form=%s lane=%d a=0x%0*llx b=0x%0*llx got=0x%0*llx "
              "pseudocode=0x%0*llx libm=0x%0*llx check=%s\n", insn, l,
              2 * es, (unsigned long long) a, 2 * es, (unsigned long long) b,
              2 * es, (unsigned long long) r, 2 * es, (unsigned long long) m,
              2 * es, (unsigned long long) c,
              r == m ? "ok" : zeros ? "INFO" : "FAIL");
      if (r != m && !zeros)
        ++failures;
    }
}

static int native (void)
{
  struct sigaction action;
  unsigned char *region;
  int f;
  page = sysconf (_SC_PAGESIZE);
  if (page < 4096 || page % 64)
    return 2;
  region = mmap (NULL, (size_t) page * 3, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (region == MAP_FAILED)
    return 2;
  memory = region + page;
  guard = memory + page;
  image = malloc ((size_t) page);
  gimage = malloc ((size_t) page);
  if (!image || !gimage || mprotect (memory, (size_t) page, PROT_READ | PROT_WRITE))
    return 2;
  memset (&action, 0, sizeof action);
  action.sa_sigaction = handler;
  action.sa_flags = SA_SIGINFO;
  sigemptyset (&action.sa_mask);
  if (sigaction (SIGSEGV, &action, NULL) || sigaction (SIGBUS, &action, NULL))
    return 2;
  setvbuf (stdout, NULL, _IOLBF, 0);
  printf ("S5-01 page=%ld memory=%p guard=%p\n", page, (void *) memory, (void *) guard);
  for (f = PS; f <= Q; ++f)
    {
      memset (vin, 0x5a, 64);
      memory_cases (f, 0);
      memory_cases (f, 1);
      duplicate_cases (f);
      memset (vin, 0x5a, 64);
      index_cases (f);
    }
  minmax_case ("vgmaxps", 0, 0);
  minmax_case ("vgminps", 1, 0);
  minmax_case ("vgmaxpd", 0, 1);
  minmax_case ("vgminpd", 1, 1);
  minmax_case ("vgmaxabsps", 2, 0);
  printf ("S5-01 failures=%d\n", failures);
  return failures != 0;
}

int main (int argc, char **argv)
{
  if (argc == 2 && !strcmp (argv[1], "--native"))
    return native ();
  fprintf (stderr, "usage: %s --native (KNC card only)\n", argv[0]);
  return 2;
}
