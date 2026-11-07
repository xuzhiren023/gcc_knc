/* Runtime C logic, actual x87, simulated KNC MXCSR storage.
   Candidate low-six flag map is provisional until card evidence.
   KNC controls are never loaded into the host's hardware MXCSR. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "constants.h"
#define GFC_FPE_ALL 63
static struct { int fpe; } options;
static unsigned int model_mxcsr;
static int failures, writes;
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
#include "backend.h"

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
  check(((cw >> 10) & 3) == expected_rc && ((model_mxcsr >> 13) & 3) == expected_rc,
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
  model_mxcsr = 0x308040; /* bit 20/21, FTZ and DAZ: opaque controls. */
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
      check(((cw >> 10) & 3) == i && ((model_mxcsr >> 13) & 3) == i,
            "rounding agrees across x87 and IMCI");
      check((cw & ~0xc00) == (before & ~0xc00), "rounding preserves x87 precision/masks");
      check(get_fpu_rounding_mode() == modes[i], "rounding getter");
      check(support_fpu_rounding_mode(modes[i]), "four binary rounding capabilities");
    }
  check(!support_fpu_rounding_mode(GFC_FPE_AWAY), "ties-away unsupported");
  for (i = 1; i <= 32; i <<= 1)
    {
      reset();
      if (support_fpu_flag(i))
        {
          model_mxcsr |= i;
          check(get_fpu_except_flags() & i, "candidate vector flag visible in union");
          set_fpu_except_flags(0, i);
          check(!(model_mxcsr & i) && !(get_fpu_except_flags() & i), "flag cleared in both domains");
          set_fpu_except_flags(i, 0);
          check(get_fpu_except_flags() & i, "raised x87 flag visible in union");
          set_fpu_except_flags(0, i);
          check(!(get_fpu_except_flags() & i), "raised flag clear");
        }
      check(!support_fpu_trap(i), "no unproven mixed-domain halting claim");
    }
  reset();
  model_mxcsr |= 0x4001;
  set_fpu_rounding_mode(GFC_FPE_UPWARD);
  get_fpu_state(original);
  model_mxcsr = (model_mxcsr & ~0x603fu) | 0x2020;
  set_fpu_rounding_mode(GFC_FPE_DOWNWARD);
  set_fpu_state(original);
  check((model_mxcsr & 0x603f) == 0x4001, "save/restore vector rounding and sticky flags");
  check(get_fpu_rounding_mode() == GFC_FPE_UPWARD, "save/restore x87 rounding");
  reset();
  set_fpu_except_flags(GFC_FPE_INVALID, 0);
  ieee_procedure_entry(outer);
  check(!get_fpu_except_flags(), "outer entry clears flags");
  model_mxcsr |= GFC_FPE_OVERFLOW;
  ieee_procedure_entry(inner);
  check(!get_fpu_except_flags() && !(model_mxcsr & 63), "nested entry clears both domains");
  model_mxcsr |= GFC_FPE_INEXACT;
  ieee_procedure_exit(inner);
  ieee_procedure_exit(outer);
  check((get_fpu_except_flags() & 41) == 41, "nested IEEE procedures merge both domains");
  reset();
  set_fpu_trap_exceptions(0, GFC_FPE_ALL);
  check(model_mxcsr == 0x308040, "halting disable preserves KNC controls");
  for (i = 4; i <= 16; i += 2)
    check(!support_fpu_underflow_control(i), "mixed-domain underflow control unsupported");
  set_fpu_underflow_mode(0);
  set_fpu_underflow_mode(1);
  check(model_mxcsr == 0x308040, "unsupported underflow setters preserve DAZ/FTZ");
  for (i = 0; i < 2; ++i)
    {
      unit u = {GFC_FPE_DOWNWARD};
      st_parameter_dt dt = {0, {{&u}}};
      double value;
      reset();
      model_mxcsr |= 0x4000;
      set_fpu_rounding_mode(GFC_FPE_UPWARD);
      expected_rc = 1;
      check(convert_real(&dt, &value, i ? "invalid" : "1.25", 8) == i,
            "formatted input success/error result");
      check(get_fpu_rounding_mode() == GFC_FPE_UPWARD
            && ((model_mxcsr >> 13) & 3) == 2, "formatted input restores both domains");
    }
  check(io_errors == 1, "formatted input invalid-data branch exercised");
  check(writes > 0, "backend actually manages KNC MXCSR without SSE");
  __asm__ volatile("fninit");
  printf("Host state logic: %d failures, %d instrumented MXCSR writes; native pending\n", failures, writes);
  return failures != 0;
}
