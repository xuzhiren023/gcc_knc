/* S2-05 / ADR-0004 point 2: local 512-bit storage lowers to XI without
   advertising a vector ABI or arithmetic. An ordinary call forces a real
   full-width spill; no aligned local or stackrealign attribute supplies the
   answer to the backend. HIGH_REG selects both halves of the register file. */
typedef unsigned long long storage __attribute__((vector_size(64)));
extern void spill_clobber(void);
#ifndef HIGH_REG
#define HIGH_REG "zmm16"
#endif
void xi_spill(const storage *input, storage *output)
{
  register storage high __asm__(HIGH_REG);
  storage saved;
  __asm__ volatile("# xi-high %0" : "=YJ"(high) : "0"(*input));
  saved = high;
  spill_clobber();
  __asm__ volatile("# xi-reloaded %0" : "+YJ"(saved));
  *output = saved;
}
