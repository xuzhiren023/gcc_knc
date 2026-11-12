/* S10-11: card qualification's worst lanes, checked against MPFR at 256 bits.
   Keep this driver on SSE so only the library's scalar evaluation changes. */
#define _GNU_SOURCE
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "knc_vmath.h"
#ifdef KNC_CBRT_DIAGNOSTIC
#include <signal.h>
#include <unistd.h>
#include <ucontext.h>

/* Async-signal-safe output, including when the failing path exhausts its stack. */
static void hexline(const char *label, size_t length, uintptr_t value)
{
  char digits[] = "0x0000000000000000\n";
  for (int i = 17; i >= 2; --i) {
    digits[i] = "0123456789abcdef"[value & 15]; value >>= 4;
  }
  (void)write(2, label, length);
  (void)write(2, digits, sizeof digits - 1);
}

static void fault(int sig, siginfo_t *info, void *context)
{
  ucontext_t *uc = context;
  hexline("si_addr=", 8, (uintptr_t)info->si_addr);
  hexline("RIP=", 4, (uintptr_t)uc->uc_mcontext.gregs[REG_RIP]);
  hexline("RSP=", 4, (uintptr_t)uc->uc_mcontext.gregs[REG_RSP]);
  _exit(128 + sig);
}

int main(int argc, char **argv)
{
  static char signal_stack[65536];
  stack_t stack = { .ss_sp = signal_stack, .ss_size = sizeof signal_stack };
  struct sigaction action = { .sa_sigaction = fault,
                             .sa_flags = SA_SIGINFO | SA_ONSTACK };
  sigemptyset(&action.sa_mask);
  if (sigaltstack(&stack, NULL) || sigaction(SIGSEGV, &action, NULL)) return 2;
  if (argc != 2 || (strcmp(argv[1], "cbrt") && strcmp(argv[1], "cbrtf"))) return 2;
  /* qualify_v1 compare sweep block zero: lane i has raw bits i. */
  if (!strcmp(argv[1], "cbrtf")) {
    __knc_vmath_v16sf x, y;
    for (uint32_t i = 0; i < 16; ++i) {
      float lane; memcpy(&lane, &i, sizeof i); x[i] = lane;
    }
    (void)write(2, "calling cbrtf\n", 14);
    y = __knc_vmath_cbrtf_16(x);
    for (int i = 0; i < 16; ++i) {
      uint32_t bits; float lane = y[i];
      memcpy(&bits, &lane, sizeof bits); hexline("out=", 4, bits);
    }
  } else {
    __knc_vmath_v8df x, y;
    for (uint64_t i = 0; i < 8; ++i) {
      double lane; memcpy(&lane, &i, sizeof i); x[i] = lane;
    }
    (void)write(2, "calling cbrt\n", 13);
    y = __knc_vmath_cbrt_8(x);
    for (int i = 0; i < 8; ++i) {
      uint64_t bits; double lane = y[i];
      memcpy(&bits, &lane, sizeof bits); hexline("out=", 4, bits);
    }
  }
  return 0;
}
#else
#include <mpfr.h>

int main(void)
{
  static const struct {
    const char *name;
    uint64_t x, y;
  } cases[] = {
    {"sin", UINT64_C(0x7f13000000000003), 0},
    {"cos", UINT64_C(0x7a31000000000004), 0},
    {"tan", UINT64_C(0x5f54000000000002), 0},
    /* qualify_v1's first argument is atan2's numerator. */
    {"atan2", UINT64_C(0x41cfb07cd81b8f16), UINT64_C(0xc1b536c582cd6336)}
  };
  mpfr_t a, b, exact, error;
  mpfr_inits2(256, a, b, exact, error, (mpfr_ptr)0);
  int failed = 0;
  for (unsigned c = 0; c < sizeof cases / sizeof cases[0]; ++c) {
    double x, y;
    memcpy(&x, &cases[c].x, 8);
    memcpy(&y, &cases[c].y, 8);
    __knc_vmath_v8df vx, vy, result;
    for (int lane = 0; lane < 8; ++lane) { vx[lane] = x; vy[lane] = y; }
    mpfr_set_d(a, x, MPFR_RNDN);
    mpfr_set_d(b, y, MPFR_RNDN);
    switch (c) {
      case 0: result = __knc_vmath_sin_8(vx); mpfr_sin(exact, a, MPFR_RNDN); break;
      case 1: result = __knc_vmath_cos_8(vx); mpfr_cos(exact, a, MPFR_RNDN); break;
      case 2: result = __knc_vmath_tan_8(vx); mpfr_tan(exact, a, MPFR_RNDN); break;
      default: result = __knc_vmath_atan2_8(vx, vy); mpfr_atan2(exact, a, b, MPFR_RNDN);
    }
    double ulp = ldexp(1.0, (int)mpfr_get_exp(exact) - 53);
    for (int lane = 0; lane < 8; ++lane) {
      mpfr_sub_d(error, exact, result[lane], MPFR_RNDN);
      mpfr_abs(error, error, MPFR_RNDN);
      double distance = mpfr_get_d(error, MPFR_RNDU) / ulp;
      if (!isfinite(result[lane]) || distance > 1.0) failed = 1;
      if (lane == 0) {
        uint64_t bits;
        memcpy(&bits, &result[lane], 8);
        printf("%s out=0x%016llx ulp=%.9f %s\n", cases[c].name,
               (unsigned long long)bits, distance, distance <= 1.0 ? "PASS" : "FAIL");
      }
    }
  }
  mpfr_clears(a, b, exact, error, (mpfr_ptr)0);
  return failed;
}
#endif
