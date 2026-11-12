/* S10-12: opt-in Linux/KNC crash tracing for qualify_v1 itself. No numerical
   or input-generation changes. The diagnostic build uses one worker. */
#include <signal.h>
#include <ucontext.h>
#include <unistd.h>

static uint64_t crash_block, crash_grid;
static const char *crash_class = "startup";
static unsigned char crash_stacks[2][65536] __attribute__((aligned(64)));

static char *crash_text(char *p, const char *s) {
  while (*s) *p++ = *s++;
  return p;
}

static char *crash_hex(char *p, uint64_t value) {
  p = crash_text(p,"0x");
  for (int shift = 60; shift >= 0; shift -= 4)
    *p++ = "0123456789abcdef"[(value >> shift) & 15];
  return p;
}

static void crash_signal(int sig, siginfo_t *info, void *context) {
  ucontext_t *uc = context;
  char line[256], *p = line;
  p = crash_text(p,"SIGSEGV si_addr=");
  p = crash_hex(p,(uintptr_t)info->si_addr);
  p = crash_text(p," RIP=");
  p = crash_hex(p,(uint64_t)uc->uc_mcontext.gregs[REG_RIP]);
  p = crash_text(p," RSP=");
  p = crash_hex(p,(uint64_t)uc->uc_mcontext.gregs[REG_RSP]);
  p = crash_text(p," si_code=");
  p = crash_hex(p,(uint64_t)info->si_code);
  *p++ = '\n';
  /* No stdio, allocation, or unwinding in the signal handler. */
  ssize_t unused = write(STDERR_FILENO,line,(size_t)(p-line));
  (void)unused;
  _exit(128+sig);
}

static void crash_stack(int worker) {
  stack_t stack = { .ss_sp = crash_stacks[worker], .ss_size = sizeof crash_stacks[0] };
  if (sigaltstack(&stack,NULL)) { perror("sigaltstack"); exit(2); }
}

static void crash_init(void) {
  struct sigaction action = {0};
  action.sa_sigaction = crash_signal;
  action.sa_flags = SA_SIGINFO | SA_ONSTACK;
  sigemptyset(&action.sa_mask);
  crash_stack(0);
  if (sigaction(SIGSEGV,&action,NULL)) { perror("sigaction"); exit(2); }
  setvbuf(stdout,NULL,_IONBF,0);
  setvbuf(stderr,NULL,_IONBF,0);
}

static void crash_trace_call(const uint64_t *x, const uint64_t *y, int masked, unsigned mask) {
  fprintf(stderr,"trace function=%s block=%llu class=%s entry=%s symbol=__knc_vmath_%s_%d%s mask=0x%08x x=",
          f->name,(unsigned long long)crash_block,crash_class,masked ? "masked" : "full",
          f->name,lanes,masked ? "_m" : "",mask);
  for (int l = 0; l < lanes; ++l)
    fprintf(stderr,"%s%016llx",l ? "," : "",(unsigned long long)x[l]);
  if (pairs) {
    fputs(" y=",stderr);
    for (int l = 0; l < lanes; ++l)
      fprintf(stderr,"%s%016llx",l ? "," : "",(unsigned long long)y[l]);
  }
  fputc('\n',stderr);
}
