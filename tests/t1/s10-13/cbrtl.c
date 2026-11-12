/* S10-13: a matching declaration and the explicit builtin must both be safe.
   Nonconstant arguments prevent compile-time folding.  The T1 runner checks
   both optimization levels, the default warning, its suppression and x86. */
extern long double cbrtl (long double);

long double direct_root (long double x)
{
  return cbrtl (x);
}

long double builtin_root (long double x)
{
  return __builtin_cbrtl (x);
}
