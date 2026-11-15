/* S7-07 discovery, not a libgfortran conformance pass.
   Sources: S7-02 field table; imci.md's legacy MXCSR and IMCI mnemonics.
   All flag positions are candidates. Log complete words before/after/clear.
   Never set MXCSR 7-12 or 20, or change DUE (21)/unknown controls.
   R27 Table 2.15 p.39: verified early KNC specification. x87 unmasking
   probes only whether that mechanism controls IMCI, not every possible trap
   mechanism. Each experiment runs in a child; the lead runs this binary. */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/resource.h>
#include <errno.h>
#include <signal.h>

typedef union { unsigned int u[16]; float f[16]; } lanes;
static lanes a __attribute__((aligned(64)));
static lanes b __attribute__((aligned(64)));
static lanes result __attribute__((aligned(64)));
static unsigned int mx(void)
{
  unsigned int v;
  __asm__ volatile("stmxcsr %0" : "=m"(v));
  return v;
}
static unsigned short sw(void)
{
  unsigned short v;
  __asm__ volatile("fnstsw %0" : "=am"(v));
  return v;
}
static unsigned short cw(void)
{
  unsigned short v;
  __asm__ volatile("fnstcw %0" : "=m"(v));
  return v;
}

static void clear_x87(unsigned short control)
{
  /* R12 CD28 p.25 (verified production x100 erratum): use the full
     save/edit/restore recovery even when foreign code unmasked x87.
     Preserve the stack, tags and condition codes while clearing status. */
  struct { unsigned short w[54]; } state;
  __asm__ volatile("fnsave %0" : "=m"(state) : : "memory");
  state.w[0] = control;
  state.w[2] &= ~0x80ffu;
  __asm__ volatile("frstor %0" : : "m"(state) : "memory");
}

static void put_mx(unsigned int value)
{
  unsigned int old = mx();
  if ((value & 0x101f80) || ((value ^ old) & ~0x603fu))
    { puts("ERROR unsafe MXCSR request"); _exit(90); }
  __asm__ volatile("ldmxcsr %0" : : "m"(value) : "memory");
}

#define VECTOR(OP) \
  __asm__ volatile("vmovaps %1, %%zmm0\n\tvmovaps %2, %%zmm1\n\t" \
                   OP "\n\tvmovaps %%zmm0, %0" \
                   : "=m"(result) : "m"(a), "m"(b) : "zmm0", "zmm1", "memory")

static void operation(int vector, int op)
{
  if (vector)
    {
      if (op == 1) { VECTOR("vmulps %%zmm1, %%zmm0, %%zmm0"); }
      else if (op == 2) { VECTOR("vrcp23ps %%zmm0, %%zmm0"); }
      else { VECTOR("vaddps %%zmm1, %%zmm0, %%zmm0"); }
    }
  else if (op == 1)
    __asm__ volatile("flds %1; fmuls %2; fstps %0; fwait"
                     : "=m"(result.f[0]) : "m"(a.f[0]), "m"(b.f[0]) : "st", "memory");
  else if (op == 2)
    __asm__ volatile("flds %1; fdivs %2; fstps %0; fwait"
                     : "=m"(result.f[0]) : "m"(a.f[0]), "m"(b.f[0]) : "st", "memory");
  else
    __asm__ volatile("flds %1; fadds %2; fstps %0; fwait"
                     : "=m"(result.f[0]) : "m"(a.f[0]), "m"(b.f[0]) : "st", "memory");
}

static void inputs(unsigned int x, unsigned int y)
{
  int i;
  for (i = 0; i < 16; ++i) { a.u[i] = x; b.u[i] = y; result.u[i] = 0; }
}

struct flag_case { const char *name; unsigned int a, b, bit; int op; };
static const struct flag_case cases[] = {
  {"invalid-inf-add", 0x7f800000, 0xff800000, 1, 0},
  {"denormal-input", 1, 0x3f800000, 2, 0},
  {"zero-div-or-recip", 0x3f800000, 0, 4, 2},
  {"overflow", 0x7f7fffff, 0x40000000, 8, 1},
  /* Normal inputs; nearest-even gives 2^-127, with inexact underflow.
     Unlike 2^-252, this distinguishes a tiny rounded result from zero. */
  {"underflow", 0x00800000, 0x3f000001, 16, 1},
  {"inexact", 0x3f800000, 0x33800000, 32, 0}
};

static void flag_probe(int n, int vector, int unmask)
{
  const struct flag_case *c = cases + n;
  unsigned int before, after, cleared;
  unsigned short control, status;
  inputs(vector && c->op == 2 ? 0 : c->a, c->b);
  before = mx();
  printf("BEGIN flag=%s domain=%s unmask-x87=%d initial-mx=%08x cw=%04x\n",
         c->name, vector ? "IMCI" : "x87", unmask, before, cw());
  put_mx(before & ~63u);
  control = cw() | 63;
  if (unmask) control &= ~c->bit;
  clear_x87(control);
  operation(vector, c->op);
  after = mx();
  status = sw();
  /* Mask and clear x87 before libc output; MXCSR remains directly observed. */
  control |= 63;
  clear_x87(control);
  put_mx(after & ~63u);
  cleared = mx();
  printf("OBSERVE flag=%s domain=%s unmask-x87=%d mx=%08x sw=%04x result=%08x clear-mx=%08x clear-sw=%04x\n",
         c->name, vector ? "IMCI" : "x87", unmask, after, status,
         result.u[0], cleared, sw());
  if ((cleared & 63) || ((cleared ^ before) & ~63u)) _exit(91);
}

static void rounding_probe(int mode, int negative)
{
  /* Exactly halfway between adjacent binary32 values at +/-1. */
  const unsigned int pos[] = {0x3f800000,0x3f800000,0x3f800001,0x3f800000};
  const unsigned int neg[] = {0xbf800000,0xbf800001,0xbf800000,0xbf800000};
  unsigned int initial = mx(), scalar, vector, expected;
  unsigned short control = (cw() & ~0xc00) | (mode << 10) | 63;
  int i, all_lanes = 1;
  printf("BEGIN rounding=%d negative=%d initial-mx=%08x\n", mode, negative, initial);
  put_mx((initial & ~0x603fu) | (mode << 13));
  clear_x87(control);
  inputs(negative ? 0xbf800000 : 0x3f800000, negative ? 0xb3800000 : 0x33800000);
  operation(0, 0);
  scalar = result.u[0];
  operation(1, 0);
  vector = result.u[0];
  expected = negative ? neg[mode] : pos[mode];
  for (i = 0; i < 16; ++i) all_lanes &= result.u[i] == expected;
  printf("OBSERVE rounding=%d negative=%d x87=%08x IMCI=%08x expected=%08x all-lanes=%d mx=%08x cw=%04x\n",
         mode, negative, scalar, vector, expected, all_lanes, mx(), cw());
  if (scalar != expected || !all_lanes || ((mx() ^ initial) & ~0x603fu)) _exit(92);
}

static int child(int rounding, int n, int vector, int unmask)
{
  int status;
  pid_t pid = fork();
  if (pid < 0) { perror("fork"); return 1; }
  if (!pid)
    {
      alarm(5);
      if (rounding) rounding_probe(n, vector);
      else flag_probe(n, vector, unmask);
      _exit(0);
    }
  while (waitpid(pid, &status, 0) < 0)
    if (errno != EINTR) { perror("waitpid"); return 1; }
  if (WIFSIGNALED(status))
    {
      printf("SIGNAL rounding=%d case=%d domain-or-sign=%d unmask-x87=%d signal=%d\n",
             rounding, n, vector, unmask, WTERMSIG(status));
      /* SIGFPE in a halting experiment is data, not a conformance failure. */
      return rounding || !unmask || WTERMSIG(status) != SIGFPE;
    }
  printf("EXIT rounding=%d case=%d domain-or-sign=%d unmask-x87=%d code=%d\n",
         rounding, n, vector, unmask, WEXITSTATUS(status));
  return WEXITSTATUS(status) != 0;
}

int main(void)
{
  struct rlimit no_core = {0, 0};
  int i, v, u, errors = 0;
  setvbuf(stdout, NULL, _IONBF, 0);
  if (setrlimit(RLIMIT_CORE, &no_core)) { perror("setrlimit"); return 1; }
  puts("S7-07 discovery: raw flag map and x87-mask/IMCI halting observations; no capability claim");
  for (i = 0; i < 4; ++i)
    for (v = 0; v < 2; ++v) errors += child(1, i, v, 0);
  for (i = 0; i < 6; ++i)
    for (v = 0; v < 2; ++v)
      for (u = 0; u < 2; ++u) errors += child(0, i, v, u);
  printf("Discovery complete: %d infrastructure/rounding/clear errors; interpret flag and halting observations separately\n", errors);
  return errors != 0;
}
