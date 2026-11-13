// options: -O2 -march=knc
// scan-asm-func store_float: movl\s+\$0x3f800000,\s*\(%rdi\)
// scan-asm-func store_float: movl\s+\$0x3f800000,\s*\(%rsi\)
// scan-asm-func store_double: movq\s+\$(?:0x0+|0),\s*\(%rdi\)
// scan-asm-func store_double: movq\s+\$(?:0x0+|0),\s*\(%rsi\)
// scan-asm-not: \b(fld\w*|fst\w*)\b
// scan-asm-not: \.LC[0-9]+

/* Repeated constants become register copies before reload.  S11-23's
   floating copy pattern must still allow their immediate-store form.
   Use double zero because a nonzero double generally needs a 64-bit
   immediate that cannot be encoded in a single memory store.  */
void
store_float (float *p, float *q)
{
  *p = 1.0f;
  *q = 1.0f;
}

void
store_double (double *p, double *q)
{
  *p = 0.0;
  *q = 0.0;
}
