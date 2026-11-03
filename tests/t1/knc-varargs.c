/* S2-03 / ADR-0004 point 4: AL counts registers, including overflow calls. */
#ifndef VARARGS_CALLEE
extern int var_target(int, ...);
int var_call_0(void) { return var_target(0); }
int var_call_1(void) { return var_target(1, 1.0); }
int var_call_8(void) { return var_target(8, 1., 2., 3., 4., 5., 6., 7., 8.); }
int var_call_10(void)
{ return var_target(10, 1., 2., 3., 4., 5., 6., 7., 8., 9., 10.); }
#else
/* Escape the list so all eight save slots and fp_offset remain observable. */
extern void var_consume(__builtin_va_list);
void var_save(int tag, ...)
{
  __builtin_va_list ap;
  __builtin_va_start(ap, tag);
  var_consume(ap);
  __builtin_va_end(ap);
}

double var_sum(int n, ...)
{
  double sum = 0;
  __builtin_va_list ap;
  __builtin_va_start(ap, n);
  while (n--) sum += __builtin_va_arg(ap, double);
  __builtin_va_end(ap);
  return sum;
}
#endif
