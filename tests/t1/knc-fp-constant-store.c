// options: -O2 -march=knc
// scan-asm-func store_float: movl\s+\$0x3f800000,\s*\(%rdi\)
// scan-asm-func store_float: movl\s+\$0x3f800000,\s*\(%rsi\)
// scan-asm-func store_double: movq\s+\$(?:0x0+|0),\s*\(%rdi\)
// scan-asm-func store_double: movq\s+\$(?:0x0+|0),\s*\(%rsi\)
// scan-asm-func store_float: (?s)\A(?!.*\b(?:fld\w*|fst\w*)\b)
// scan-asm-func store_double: (?s)\A(?!.*\b(?:fld\w*|fst\w*)\b)
// scan-asm-func store_complex: movl\s+\$0x3f800000,\s*-?\d*\(%rsp\)
// scan-asm-func store_complex: (?s)\A(?!.*\b(?:fld1|fldz)\b)
// scan-asm-func pass_varargs: movl\s+\$0x40000000,\s*-?\d*\(%rsp\)
// scan-asm-func pass_varargs: (?s)\A(?!.*\b(?:fld\w*|fst\w*)\b)
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

/* The division helper receives scalar SF constants in vector argument
   registers.  Its reload bridges must store their bits as immediates.  */
void
store_complex (_Complex float *p)
{
  *p = 1.0f / *p;
}

extern void float_args (float, ...);

void
pass_varargs (void)
{
  float_args (2.0f, 0.0);
}
