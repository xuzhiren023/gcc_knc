// options: -O2
// scan-asm: ret
// scan-asm-func smoke: movl[ \t]+\$7,[ \t]*%eax
// scan-asm-not: %zmm
int smoke(void)
{
  return 7;
}
