/* S12-23: discriminating tiny-result probes and isolated x87 recovery.
   R27 Table 2.15 p.39 and section 4.1 pp.55-56: verified interface facts
   from the early KNC specification, not a production-card observation.
   R12 CD28 p.25: verified production x100 erratum and save/restore remedy.
   R12 CD19 p.23: verified production erratum; a faulting vector instruction
   can modify MXCSR. These numerical oracles use nonfaulting operands; they
   must not be reused as assertions about MXCSR in a vector fault handler.
   No card result is claimed by compilation or the assembly checks. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <errno.h>
#include <sys/wait.h>
#include <sys/resource.h>
#include "constants.h"
static struct { int fpe; } options;
static void estr_write(const char *s) { fputs(s, stderr); }
#include "fpu-knc.h"

typedef union { unsigned int u[16]; float f[16]; } lanes;
static lanes a __attribute__((aligned(64)));
static lanes b __attribute__((aligned(64)));
static lanes result __attribute__((aligned(64)));
struct x87_image { unsigned short w[54]; };
_Static_assert(sizeof(struct x87_image) == 108, "x87 save area");
static volatile sig_atomic_t phase;

static void save(struct x87_image *p)
{ __asm__ volatile("fnsave %0" : "=m"(*p) : : "memory"); }
static void restore(const struct x87_image *p)
{ __asm__ volatile("frstor %0" : : "m"(*p) : "memory"); }
static unsigned int mx(void)
{
  unsigned int v;
  __asm__ volatile("stmxcsr %0" : "=m"(v));
  return v;
}
static void put_mx(unsigned int v)
{
  /* Preserve DUE (21); never introduce reserved bits 7-12 or 20. */
  if ((v & 0x101f80u) || ((v ^ mx()) & ~0xe07fu)) _exit(90);
  __asm__ volatile("ldmxcsr %0" : : "m"(v) : "memory");
}
static void multiply(int vector)
{
  if (vector)
    __asm__ volatile("vmovaps %1, %%zmm0; vmovaps %2, %%zmm1; "
                     "vmulps %%zmm1, %%zmm0, %%zmm0; vmovaps %%zmm0, %0"
                     : "=m"(result) : "m"(a), "m"(b)
                     : "zmm0", "zmm1", "memory");
  else
    __asm__ volatile("flds %1; fmuls %2; fstps %0; fwait"
                     : "=m"(result.f[0]) : "m"(a.f[0]), "m"(b.f[0])
                     : "st", "memory");
}

static int tiny(void)
{
  /* Exact input case: 2^-149 * 2^126 = 2^-23, a normal result.
     Tiny cases use NORMAL inputs so DAZ cannot explain a zero output:
       2^-126 * 1/2 = 2^-127 (exact binary32 subnormal),
       2^-126 * (1/2 + 2^-24) = 2^-127 + 2^-150 (inexact tie).
     Nearest-even rounds the tie to 0x00400000, not zero.
     The old 2^-126 * 2^-126 control rounds to zero in either mode. */
  static const struct { const char *name; unsigned int x, y, gradual; } c[] = {
    {"subnormal-input-normal-output", 1, 0x7e800000, 0x34000000},
    {"exact-tiny-output", 0x00800000, 0x3f000000, 0x00400000},
    {"inexact-tiny-output", 0x00800000, 0x3f000001, 0x00400000},
    {"old-rounds-to-zero-control", 0x00800000, 0x00800000, 0}
  };
  unsigned int initial = mx();
  int failures = 0;
  struct x87_image original;
  save(&original);
  for (int vector = 0; vector < 2; ++vector)
    for (int controls = 0; controls < 4; ++controls)
      for (int n = 0; n < 4; ++n)
        {
          struct x87_image clean;
          save(&clean); /* Reset between independent masked cases. */
          put_mx((initial & ~0xe07fu) | ((controls & 1) ? 0x40 : 0)
                 | ((controls & 2) ? 0x8000 : 0));
          for (int i = 0; i < 16; ++i)
            { a.u[i] = c[n].x; b.u[i] = c[n].y; result.u[i] = 0xdeadbeef; }
          multiply(vector);
          unsigned short sw;
          __asm__ volatile("fnstsw %0" : "=am"(sw));
          unsigned int after = mx(), expected = c[n].gradual;
          if (vector && ((n == 0 && (controls & 1))
                         || (n != 0 && (controls & 2)))) expected = 0;
          int ok = 1;
          for (int i = 0; i < (vector ? 16 : 1); ++i)
            ok &= result.u[i] == expected;
          failures += !ok;
          printf("%s domain=%s DAZ=%d FZ=%d case=%s result=%08x expected=%08x mx=%08x sw=%04x\n",
                 ok ? "PASS" : "FAIL", vector ? "IMCI" : "x87",
                 controls & 1, (controls >> 1) & 1, c[n].name,
                 result.u[0], expected, after, sw);
        }
  put_mx(initial);
  restore(&original);
  return failures != 0;
}

static void trapped(int sig, siginfo_t *info, void *context)
{
  (void)sig; (void)context;
  /* Only the NEW divide-by-zero is a pass, never a stale invalid trap. */
  _exit(phase == 2 && info->si_code == FPE_FLTDIV ? 0 : 81);
}

static void recovery(int state)
{
  struct sigaction action;
  struct x87_image before, after;
  unsigned char clean_state[GFC_FPE_STATE_BUFFER_SIZE];
  unsigned int initial = mx();
  memset(&action, 0, sizeof(action));
  action.sa_sigaction = trapped;
  action.sa_flags = SA_SIGINFO;
  sigemptyset(&action.sa_mask);
  if (sigaction(SIGFPE, &action, NULL)) _exit(80);
  alarm(5);
  /* Two occupied stack entries must survive both runtime clearing routes. */
  __asm__ volatile("fninit; fld1; fldpi" : : : "st", "memory");
  save(&before);
  before.w[0] = (before.w[0] & ~0xc05u) | 0x400u;
  restore(&before);
  get_fpu_state(clean_state);
  /* A masked arithmetic invalid creates the sticky condition. Unmask it
     without FWAIT, so the runtime receives foreign pending x87 state. */
  before.w[0] |= 1;
  restore(&before);
  __asm__ volatile("fldz; fldz; fdivp; fstp %%st(0)" : : : "st", "memory");
  unsigned short unmasked = before.w[0] & ~1u;
  __asm__ volatile("fldcw %0" : : "m"(unmasked) : "memory");
  phase = 1;
  if (state) set_fpu_state(clean_state);
  else set_fpu_except_flags(0, GFC_FPE_INVALID);
  __asm__ volatile("fwait");
  save(&after);
  int ok = after.w[0] == unmasked && !(after.w[2] & 0x80ff)
           && after.w[4] == before.w[4]
           && (after.w[2] & 0x3800) == (before.w[2] & 0x3800)
           && !memcmp((char *)&before + 28, (char *)&after + 28, 20)
           && mx() == initial;
  if (!ok) _exit(82);
  restore(&after);
  phase = 2;
  /* fdivs with a zero memory operand avoids AT&T fdivp order ambiguity. */
  static const float zero;
  __asm__ volatile("fld1; fdivs %0; fwait" : : "m"(zero) : "st", "memory");
  _exit(83); /* Missing new exception is also failure. */
}

int main(int argc, char **argv)
{
  struct rlimit limit = {0, 0};
  setvbuf(stdout, NULL, _IONBF, 0);
  if (setrlimit(RLIMIT_CORE, &limit)) return 1;
  if (argc != 2) { fprintf(stderr, "usage: %s tiny|clear|restore\n", argv[0]); return 2; }
  if (!strcmp(argv[1], "tiny")) return tiny();
  int state = !strcmp(argv[1], "restore");
  if (!state && strcmp(argv[1], "clear")) return 2;
  pid_t pid = fork();
  if (pid < 0) return 1;
  if (!pid) recovery(state);
  int status;
  while (waitpid(pid, &status, 0) < 0) if (errno != EINTR) return 1;
  int ok = WIFEXITED(status) && WEXITSTATUS(status) == 0;
  printf("%s recovery=%s wait-status=%04x (new divide-by-zero required)\n",
         ok ? "PASS" : "FAIL", argv[1], status);
  return !ok;
}
