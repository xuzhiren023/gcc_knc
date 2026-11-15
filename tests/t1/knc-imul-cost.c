// S12-21: the three-cycle scalar multiply estimate makes IMUL attractive
// for 123*x.  A shift/add/sub sequence is cheaper than the serial multiply
// path described by R02 p.56 and measured in the phase-one card diagnostic
// (docs/research/s12-21-phase1.md).  This tests the optimizer's decision,
// not the spelling or numeric value of the processor-cost initializer.
// Unsigned arithmetic makes every input valid, including modular overflow.
// Keep default density four and do not enable fast math or PhiNix.
// options: -O2 -march=knc
// scan-asm-not: ^[ \t]+imul[lq]?[ \t]
// scan-asm-func multiply32: \b(?:sal|shl|lea|add|sub)l\b
// scan-asm-func multiply64: \b(?:sal|shl|lea|add|sub)q\b

unsigned int
multiply32 (unsigned int x)
{
  return x * 123U;
}

unsigned long long
multiply64 (unsigned long long x)
{
  return x * 123ULL;
}
