/* S7-04: force real arithmetic and unwind references through the driver.
   Host link/inspection only; the engineer does not execute this on the card. */
#include <unwind.h>

extern __int128 __divti3 (__int128, __int128);
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
  return __divti3 (dividend, divisor) != 12 || frames == 0;
}

#ifndef PROBE_DSO
int
main (void)
{
  return knc_libgcc_link_probe ();
}
#endif
