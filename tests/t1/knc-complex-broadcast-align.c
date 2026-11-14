/* S12-29: exercise SCmode constant, argument and result transport.
   The assembly check follows each broadcast's memory operand, so aligning
   the constant or using an aligned temporary are both acceptable fixes. */
// options: -O2 -march=knc
// scan-asm: ^pass_complex:
// scan-asm: ^relay_complex:
// scan-broadcast-alignment:

__attribute__((noinline, noclone))
_Complex float pass_complex (_Complex float value)
{
  return value;
}

__attribute__((noinline, noclone))
_Complex float relay_complex (_Complex float value)
{
  return pass_complex (value);
}

int main (void)
{
  _Complex float value = relay_complex (13.0f + 27.0fi);
  return __real__ value != 13.0f || __imag__ value != 27.0f;
}
