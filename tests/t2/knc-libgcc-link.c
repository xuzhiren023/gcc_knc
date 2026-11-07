/* S7-04: force real arithmetic and unwind references through the driver.
   Host link/inspection only; the engineer does not execute this on the card. */
#include <unwind.h>
#include <stddef.h>

extern __int128 __divti3 (__int128, __int128);
/* libgcc/Makefile.in puts this helper only in LIB2FUNCS_ST.  A shared
   link therefore needs the libgcc_s linker script's libgcc.a fallback. */
extern int __gcc_bcmp (const unsigned char *, const unsigned char *, size_t);
static volatile __int128 dividend = 84, divisor = 7;

static _Unwind_Reason_Code
trace (struct _Unwind_Context *context, void *argument)
{
  unsigned int *frames = argument;
  if (_Unwind_GetIP (context))
    ++*frames;
  return _URC_NO_REASON;
}

int
knc_libgcc_link_probe (void)
{
  unsigned int frames = 0;
  _Unwind_Backtrace (trace, &frames);
  int compared = __gcc_bcmp ((const unsigned char *) "knc",
                            (const unsigned char *) "knc", 3);
  return __divti3 (dividend, divisor) != 12 || frames == 0 || compared;
}

#ifndef PROBE_DSO
int
main (void)
{
  return knc_libgcc_link_probe ();
}
#endif
