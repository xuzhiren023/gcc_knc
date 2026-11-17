// S12-38: preserve the main/local-assignment/return shape of
// gcc/testsuite/gcc.dg/vect/vect-pr123221.c.  Compilation must succeed
// without an ICE in SLP reduction analysis.
// As in the upstream test, disable PRE to retain the triggering form.
// options: -O3 -march=knc -fno-tree-pre

int a, d;
struct {
  char b;
} c;

int main()
{
  int f;
  for (; d; d++)
    c.b = f = a ? c.b : 0;
  return 0;
}
