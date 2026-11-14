/* Runtime C logic, actual x87, modeled or native KNC MXCSR storage.
   Six flag positions proven by the lead card run, 2026-11-07 22:53Z.
   KNC controls are never loaded into the host's hardware MXCSR. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "constants.h"
#define GFC_FPE_ALL 63
static struct { int fpe; } options;
static unsigned int model_mxcsr;
static int failures, writes, warnings;
static unsigned int controls;
static void estr_write(const char *message) { ++warnings; }
#ifdef S7_07_NATIVE
#define main discovery_main
#include "fp-probe.c"
#undef main
static unsigned int read_mx(void) { return mx(); }
static void write_mx(unsigned int v) { put_mx(v); }
#else
static unsigned int read_mx(void) { return model_mxcsr; }
static void write_mx(unsigned int v) { model_mxcsr = v; }
#endif
static void check(int ok, const char *name)
{
  if (!ok) { printf("FAIL %s\n", name); ++failures; }
}
static void model_write(unsigned int value)
{
  ++writes;
  check(!(value & 0x1f80), "setter writes reserved MXCSR bits 7-12");
  check((value & ~0x603fu) == (model_mxcsr & ~0x603fu),
        "setter preserves bit 21 and all unsupported controls");
  model_mxcsr = value;
}
#ifdef S7_07_NATIVE
#include "fpu-knc.h"
#else
#include "backend.h"
#endif

/* convert_real is extracted unchanged from read.c. Only the surrounding
   types, conversion wrapper and error callbacks are supplied here. */
typedef float GFC_REAL_4;
typedef double GFC_REAL_8;
enum { ROUND_NEAREST=GFC_FPE_TONEAREST, ROUND_COMPATIBLE=10,
       ROUND_UNSPECIFIED=11, ROUND_PROCDEFINED=12, LIBERROR_READ_VALUE=1 };
typedef struct { int round_status; } unit;
typedef struct { int common; struct { struct { unit *current_unit; } p; } u; } st_parameter_dt;
static int io_errors, expected_rc;
static double gfc_strtod(const char *s, char **end)
{
  unsigned short cw;
  __asm__ volatile("fnstcw %0" : "=m"(cw));
  check(((cw >> 10) & 3) == expected_rc && ((read_mx() >> 13) & 3) == expected_rc,
        "formatted input synchronizes rounding during conversion");
  return strtod(s, end);
}
static void internal_error(void *p, const char *s) { abort(); }
static void generate_error(void *p, int n, const char *s) { ++io_errors; }
static void next_record(st_parameter_dt *p, int n) {}
#include "callers.h"

static void reset(void)
{
  __asm__ volatile("fninit");
#ifdef S7_07_NATIVE
  write_mx(read_mx() & ~0x603fu);
#else
  model_mxcsr = 0x308040; /* bit 20/21, FTZ and DAZ: opaque controls. */
#endif
  controls = read_mx() & ~0x603fu;
  /* R27 Table 2.15 p.39 (verified, early KNC specification): bit 20
     is reserved too.  A synthetic fixture must obey the legal bit map. */
  check(!(read_mx() & 0x101f80u), "fixture sets reserved MXCSR bits 7-12 or 20");
}

int main(void)
{
  const int modes[] = {GFC_FPE_TONEAREST, GFC_FPE_DOWNWARD,
                       GFC_FPE_UPWARD, GFC_FPE_TOWARDZERO};
  unsigned char original[32], outer[32], inner[32];
  unsigned short cw, before;
  int i;
  for (i = 0; i < 4; ++i)
    {
      reset();
      __asm__ volatile("fnstcw %0" : "=m"(before));
      set_fpu_rounding_mode(modes[i]);
      __asm__ volatile("fnstcw %0" : "=m"(cw));
      check(((cw >> 10) & 3) == i && ((read_mx() >> 13) & 3) == i,
            "rounding agrees across x87 and IMCI");
      check((cw & ~0xc00) == (before & ~0xc00), "rounding preserves x87 precision/masks");
      check(get_fpu_rounding_mode() == modes[i], "rounding getter");
      check(support_fpu_rounding_mode(modes[i]), "four binary rounding capabilities");
    }
  check(!support_fpu_rounding_mode(GFC_FPE_AWAY), "ties-away unsupported");
  for (i = 1; i <= 32; i <<= 1)
    {
      reset();
      check(support_fpu_flag(i), "all six proven flags must be supported");
        {
          write_mx(read_mx() | i);
          check(get_fpu_except_flags() & i, "proven vector flag visible in union");
          set_fpu_except_flags(0, i);
          check(!(read_mx() & i) && !(get_fpu_except_flags() & i), "flag cleared in both domains");
          set_fpu_except_flags(i, 0);
          __asm__ volatile("fnstsw %0" : "=am"(cw));
          check(cw & i, "setter raises x87 sticky flag");
          write_mx(read_mx() & ~63u);
          check(get_fpu_except_flags() & i, "x87-only flag visible in union");
          set_fpu_except_flags(0, i);
          check(!(get_fpu_except_flags() & i), "raised flag clear");
        }
      check(!support_fpu_trap(i), "no unproven mixed-domain halting claim");
    }
  reset();
  write_mx(read_mx() | 0x4001);
  set_fpu_rounding_mode(GFC_FPE_UPWARD);
  get_fpu_state(original);
  write_mx((read_mx() & ~0x603fu) | 0x2020);
  set_fpu_rounding_mode(GFC_FPE_DOWNWARD);
  set_fpu_state(original);
  check((read_mx() & 0x603f) == 0x4001, "save/restore vector rounding and sticky flags");
  check(get_fpu_rounding_mode() == GFC_FPE_UPWARD, "save/restore x87 rounding");
  reset();
  set_fpu_except_flags(GFC_FPE_INVALID, 0);
  ieee_procedure_entry(outer);
  check(!get_fpu_except_flags(), "outer entry clears flags");
  write_mx(read_mx() | GFC_FPE_OVERFLOW);
  ieee_procedure_entry(inner);
  check(!get_fpu_except_flags() && !(read_mx() & 63), "nested entry clears both domains");
  write_mx(read_mx() | GFC_FPE_INEXACT);
  ieee_procedure_exit(inner);
  ieee_procedure_exit(outer);
  check((get_fpu_except_flags() & 41) == 41, "nested IEEE procedures merge both domains");
  reset();
  set_fpu_trap_exceptions(GFC_FPE_ALL, 0);
  check(warnings == 1 && !get_fpu_trap_exceptions(), "halting enable warns and stays unsupported");
  __asm__ volatile("fnstcw %0" : "=m"(cw));
  check((cw & 63) == 63, "unsupported halting does not unmask x87");
  set_fpu_trap_exceptions(0, GFC_FPE_ALL);
  check(read_mx() == controls, "halting disable preserves KNC controls");
  for (i = 4; i <= 16; i += 2)
    check(!support_fpu_underflow_control(i), "mixed-domain underflow control unsupported");
  set_fpu_underflow_mode(0);
  set_fpu_underflow_mode(1);
  check(read_mx() == controls, "unsupported underflow setters preserve DAZ/FTZ");
  check(warnings == 3 && !get_fpu_underflow_mode(), "underflow requests warn without claiming gradual mode");
  for (i = 0; i < 2; ++i)
    {
      unit u = {GFC_FPE_DOWNWARD};
      st_parameter_dt dt = {0, {{&u}}};
      double value;
      reset();
      write_mx(read_mx() | 0x4000);
      set_fpu_rounding_mode(GFC_FPE_UPWARD);
      expected_rc = 1;
      check(convert_real(&dt, &value, i ? "invalid" : "1.25", 8) == i,
            "formatted input success/error result");
      check(get_fpu_rounding_mode() == GFC_FPE_UPWARD
            && ((read_mx() >> 13) & 3) == 2, "formatted input restores both domains");
    }
  check(io_errors == 1, "formatted input invalid-data branch exercised");
#ifndef S7_07_NATIVE
  /* Restore a saved foreign word: reserved/opaque fields must never leak. */
  get_fpu_state(original);
  ((struct fenv *)original)->__mxcsr ^= 0xffff9fc0u;
  set_fpu_state(original);
  check(writes > 0, "backend actually manages KNC MXCSR without SSE");
#else
  for (i = 0; i < 4; ++i)
    for (int negative = 0; negative < 2; ++negative)
      {
        const unsigned int pos[] = {0x3f800000,0x3f800000,0x3f800001,0x3f800000};
        const unsigned int neg[] = {0xbf800000,0xbf800001,0xbf800000,0xbf800000};
        reset();
        set_fpu_rounding_mode(modes[i]);
        inputs(negative ? 0xbf800000 : 0x3f800000, negative ? 0xb3800000 : 0x33800000);
        operation(0, 0);
        check(result.u[0] == (negative ? neg[i] : pos[i]), "native x87 rounding result");
        operation(1, 0);
        for (int lane = 0; lane < 16; ++lane)
          check(result.u[lane] == (negative ? neg[i] : pos[i]), "native IMCI rounding result");
        check((read_mx() & ~0x603fu) == controls, "native rounding preserves controls");
      }
  for (i = 0; i < 6; ++i)
    for (int vector = 0; vector < 2; ++vector)
      {
        const struct flag_case *c = cases + i;
        reset();
        inputs(vector && c->op == 2 ? 0 : c->a, c->b);
        operation(vector, c->op);
        check(get_fpu_except_flags() & c->bit, "native arithmetic flag visible");
        set_fpu_except_flags(0, GFC_FPE_ALL);
        check(!get_fpu_except_flags(), "native arithmetic flags cleared in both domains");
        check((read_mx() & ~0x603fu) == controls, "native flag clear preserves controls");
      }
#endif
  __asm__ volatile("fninit");
  printf("State logic: %d failures, %d instrumented MXCSR writes\n", failures, writes);
  return failures != 0;
}
