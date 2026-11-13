// options: -O2 -march=knc
// scan-asm-func store_complex: movl\s+\$0x3f800000,\s*-?\d*\(%rsp\)
// scan-asm-func store_complex: movl\s+\$(?:0x0+|0),\s*-?\d*\(%rsp\)
// scan-asm-func pass_varargs: movl\s+\$0x40000000,\s*-?\d*\(%rsp\)
// scan-asm-func pass_varargs: movl\s+\$0x40c00000,\s*-?\d*\(%rsp\)

/* Reduced from gcc.c-torture/execute/complex-5.c and va-arg-26.c.
   LRA can re-recognize SF constant stores as *knc_copysf.  Keep the
   immediate alternatives used by the pre-S11-23 compiler for these
   argument transfers.  Other stores may legitimately use x87 CSE,
   and the double argument may still come from a constant pool.  */
extern void abort (void);
extern void exit (int);
extern _Complex float x, y, z, w;
void
store_complex (void)
{
  z = x + y;
  y = x + 1.0f / z;
  /* Keep both components of z live across the division helper.  */
  if (z != w)
    abort ();
  exit (0);
}

extern double float_args (float, float, float, float, float, float, ...);

void
pass_varargs (void)
{
  if (float_args (1.0f, 2.0f, 3.0f, 4.0f, 5.0f, 6.0f, 7.0) != 7.0)
    abort ();
  exit (0);
}
