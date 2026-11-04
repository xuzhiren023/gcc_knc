/* S3-20: gcc.c-torture/execute/pr85169.c's XI constant-pool copy,
   byte element update and copy back.  Keep the value observable.  */
typedef char V __attribute__((vector_size (64)));

static void __attribute__((noipa))
foo (V *p)
{
  V v = *p;
  v[63] = 1;
  *p = v;
}

int
main (void)
{
  V v = (V) { };
  foo (&v);
  for (unsigned i = 0; i < 64; ++i)
    if (v[i] != (i == 63))
      __builtin_abort ();
  return 0;
}
