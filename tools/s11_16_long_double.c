/* S11-16: bounded MPSS libm crash audit. No accuracy claims are made. */
#define _GNU_SOURCE
#include <complex.h>
#include <dlfcn.h>
#include <errno.h>
#include <float.h>
#include <pthread.h>
#include <sched.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>

#define FIRST (-16445)
#define COUNT (32829u * 8u)
typedef struct { uint64_t m; uint16_t se; } bits;
enum kind { UNARY, BINARY, SINCOS, GAMMA_R, COMPLEX, HEALTHY, CRASH };
struct candidate { const char *name; enum kind kind; void *address; };
static struct candidate candidates[] = {
  {"cbrtl", UNARY, 0}, {"powl", BINARY, 0}, {"scalbl", BINARY, 0},
  {"lgammal", UNARY, 0}, {"lgammal_r", GAMMA_R, 0},
  {"gammal", UNARY, 0}, {"tgammal", UNARY, 0},
  {"sinl", UNARY, 0}, {"cosl", UNARY, 0}, {"tanl", UNARY, 0},
  {"sincosl", SINCOS, 0}, {"cexpl", COMPLEX, 0}
};
static struct candidate selftests[] = {
  {"healthy_before", HEALTHY, 0}, {"injected_segv", CRASH, 0},
  {"healthy_after", HEALTHY, 0}
};
static const struct candidate *current;
static unsigned workers;
static __thread char fault_line[256];
static __thread size_t fault_length;
struct job { unsigned id; unsigned calls; };

static bits input_bits(unsigned i)
{
  static const uint64_t mantissa[] = {
    UINT64_C(0x8000000000000000), UINT64_C(0xa000000000000000),
    UINT64_C(0xc000000000000000), UINT64_MAX
  };
  int e = FIRST + (int)(i / 8);
  bits b = {mantissa[i % 4], (uint16_t)((i / 4 % 2) << 15)};
  if (e < -16382) b.m >>= -16382 - e;
  else b.se |= e + 16383;
  return b;
}

static long double value(bits b)
{
  unsigned char raw[sizeof(long double)] = {0};
  long double x;
  memcpy(raw, &b.m, 8);
  memcpy(raw + 8, &b.se, 2);
  memcpy(&x, raw, sizeof x);
  return x;
}

/* Only async-signal-safe operations here. Formatting happens in the worker
   before the call, in thread-local storage, so racing workers cannot mix inputs.
   _exit kills this function's child, and the parent starts the next function. */
static void fault(int sig)
{
  if (fault_length) {
    ssize_t ignored = write(STDOUT_FILENO, fault_line, fault_length);
    (void)ignored;
  }
  _exit(128 + sig);
}

static void record_input(bits b, unsigned i, unsigned variant)
{
  fault_length = (size_t)snprintf(fault_line, sizeof fault_line,
    "FAULT %s signal=11 input=%04x:%016llx exponent=%d sign=%u mantissa=%u variant=%u\n",
    current->name, (unsigned)b.se, (unsigned long long)b.m,
    FIRST + (int)(i / 8), i / 4 % 2, i % 4, variant);
}

static void *worker(void *opaque)
{
  struct job *job = opaque;
  for (unsigned i = job->id; i < COUNT; i += workers) {
    bits b = input_bits(i);
    long double x = value(b), a, c;
    volatile long double sink;
    int sign;
    record_input(b, i, 0);
    switch (current->kind) {
    case UNARY:
      sink = ((long double (*)(long double))current->address)(x);
      break;
    case BINARY:
      /* Exercise both argument positions, with positive and negative fixed
         partners. All calls for this input retain the same reported x. */
      sink = ((long double (*)(long double, long double))current->address)(x, 1.5L);
      record_input(b, i, 1);
      sink = ((long double (*)(long double, long double))current->address)(x, -1.5L);
      record_input(b, i, 2);
      sink = ((long double (*)(long double, long double))current->address)(1.5L, x);
      record_input(b, i, 3);
      sink = ((long double (*)(long double, long double))current->address)(-1.5L, x);
      break;
    case SINCOS:
      ((void (*)(long double, long double *, long double *))current->address)(x, &a, &c);
      sink = a + c;
      break;
    case GAMMA_R:
      sink = ((long double (*)(long double, int *))current->address)(x, &sign);
      break;
    case COMPLEX: {
      long double complex z;
      __real__ z = x; __imag__ z = 1.5L;
      z = ((long double complex (*)(long double complex))current->address)(z);
      sink = __real__ z;
      record_input(b, i, 1);
      __real__ z = 1.5L; __imag__ z = x;
      z = ((long double complex (*)(long double complex))current->address)(z);
      sink = __imag__ z;
      break;
    }
    case HEALTHY: sink = x; break;
    case CRASH: raise(SIGSEGV); sink = x; break;
    }
    (void)sink;
    job->calls += current->kind == BINARY ? 4 : current->kind == COMPLEX ? 2 : 1;
  }
  return 0;
}

static int child(void)
{
  struct sigaction action;
  memset(&action, 0, sizeof action);
  action.sa_handler = fault;
  sigemptyset(&action.sa_mask);
  if (sigaction(SIGSEGV, &action, 0)) return 2;
#ifdef PROBE_HOST_TEST
  workers = 2; /* Cygwin has no Linux sched_getaffinity; driver stays threaded. */
#else
  cpu_set_t allowed;
  if (sched_getaffinity(0, sizeof allowed, &allowed)) return 2;
  workers = CPU_COUNT(&allowed);
#endif
  if (!workers) return 2;
  pthread_t *threads = calloc(workers, sizeof *threads);
  struct job *jobs = calloc(workers, sizeof *jobs);
  if (!threads || !jobs) return 2;
  printf("START %s workers=%u inputs=%u\n", current->name, workers, COUNT);
  for (unsigned j = 0; j < workers; ++j) {
    jobs[j].id = j;
    if (pthread_create(&threads[j], 0, worker, &jobs[j])) return 2;
  }
  unsigned calls = 0;
  for (unsigned j = 0; j < workers; ++j) {
    if (pthread_join(threads[j], 0)) return 2;
    calls += jobs[j].calls;
  }
  printf("RESULT %s OK calls=%u\n", current->name, calls);
  free(jobs); free(threads);
  unsigned per_input = current->kind == BINARY ? 4 : current->kind == COMPLEX ? 2 : 1;
  return calls == COUNT * per_input ? 0 : 2;
}

int main(int argc, char **argv)
{
  if (LDBL_MANT_DIG != 64 || LDBL_MAX_EXP != 16384 || sizeof(long double) != 16)
    return 2;
  setvbuf(stdout, 0, _IONBF, 0);
  struct rlimit no_core = {0, 0};
  if (setrlimit(RLIMIT_CORE, &no_core)) return 2;
  if (argc == 2 && !strcmp(argv[1], "--enumerate")) {
    for (unsigned i = 0; i < COUNT; ++i) {
      bits b = input_bits(i);
      printf("INPUT %d %u %u %04x:%016llx\n", FIRST + (int)(i / 8),
             i / 4 % 2, i % 4, (unsigned)b.se, (unsigned long long)b.m);
    }
    return 0;
  }
  struct candidate *list = candidates;
  unsigned count = sizeof candidates / sizeof *candidates;
  if (argc == 2 && !strcmp(argv[1], "--selftest")) {
    list = selftests; count = sizeof selftests / sizeof *selftests;
  } else if (argc != 1) return 2;
  void *lib = 0;
  if (list == candidates) {
    lib = dlopen("libm.so.6", RTLD_NOW | RTLD_LOCAL);
    if (!lib) { fprintf(stderr, "ERROR dlopen: %s\n", dlerror()); return 2; }
  }
  unsigned faults = 0, errors = 0;
  for (unsigned f = 0; f < count; ++f) {
    current = &list[f];
    if (lib) {
      list[f].address = dlsym(lib, list[f].name);
      if (!list[f].address) {
        printf("RESULT %s ERROR missing-symbol\n", current->name);
        ++errors; continue;
      }
    }
    pid_t pid = fork();
    if (pid == 0) _exit(child());
    if (pid < 0) { ++errors; printf("RESULT %s ERROR fork\n", current->name); continue; }
    int status;
    pid_t waited;
    do { waited = waitpid(pid, &status, 0); } while (waited < 0 && errno == EINTR);
    if (waited < 0) { ++errors; printf("RESULT %s ERROR waitpid\n", current->name); }
    else if (WIFEXITED(status) && WEXITSTATUS(status) == 128 + SIGSEGV) {
      ++faults; printf("RESULT %s FAULT signal=11\n", current->name);
    } else if (!WIFEXITED(status) || WEXITSTATUS(status)) {
      ++errors; printf("RESULT %s ERROR wait-status=%d\n", current->name, status);
    }
  }
  if (lib) dlclose(lib);
  printf("SUMMARY functions=%u faults=%u errors=%u\n", count, faults, errors);
  return errors ? 2 : faults ? 1 : 0;
}
