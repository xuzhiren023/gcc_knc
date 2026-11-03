/* S2-04 T1: ADR-0004 point 6. Keep 14 allocatable GPRs live across scalar
   transfers in both directions. Empty matching asms preserve the bits while
   requiring LRA to cross the GPR/zmm boundary, rather than expansion doing it.
   The host reference uses the same integer bits without a register-bank move.
   Leave r15 free for both bits and the allocated mask scratch; transfer
   addresses must use rsp under this pressure. Define PRESSURE_MAIN for the
   eventual tools/card_run comparison, or PRESSURE_MODE=1..4 to isolate a mode. */
typedef unsigned int u32;
typedef unsigned long long u64;

#define LIVE \
  __asm__ volatile ("# pressure-live %0 %1 %2 %3 %4 %5 %6 %7 %8 %9 %10 %11 %12 %13" \
    : "+r"(a), "+r"(b), "+r"(c), "+r"(d), "+r"(e), "+r"(f), "+r"(g), \
      "+r"(h), "+r"(i), "+r"(j), "+r"(k), "+r"(l), "+r"(m), "+r"(n))

#ifdef __KNC__
#define TRANSFER(TYPE, UTYPE) \
  TYPE value; \
  __asm__ volatile ("# pressure-to-zmm" : "=YJ"(value) : "0"((UTYPE)seed)); \
  __asm__ volatile ("# pressure-to-gpr" : "=r"(bits) : "0"(value))
#else
#define TRANSFER(TYPE, UTYPE) bits = (UTYPE)seed
#endif

#define PROBE(NAME, TYPE, UTYPE) \
__attribute__((noinline, noclone)) u64 NAME(u64 seed) \
{ \
  register u64 a __asm__("rax") = seed + 1; \
  register u64 b __asm__("rbx") = seed + 2; \
  register u64 c __asm__("rcx") = seed + 3; \
  register u64 d __asm__("rdx") = seed + 4; \
  register u64 e __asm__("rsi") = seed + 5; \
  register u64 f __asm__("rdi") = seed + 6; \
  register u64 g __asm__("rbp") = seed + 7; \
  register u64 h __asm__("r8") = seed + 8; \
  register u64 i __asm__("r9") = seed + 9; \
  register u64 j __asm__("r10") = seed + 10; \
  register u64 k __asm__("r11") = seed + 11; \
  register u64 l __asm__("r12") = seed + 12; \
  register u64 m __asm__("r13") = seed + 13; \
  register u64 n __asm__("r14") = seed + 14; \
  UTYPE bits; \
  LIVE; \
  TRANSFER(TYPE, UTYPE); \
  LIVE; \
  return bits + a + b + c + d + e + f + g + h + i + j + k + l + m + n; \
}

#if !defined(PRESSURE_MODE) || PRESSURE_MODE == 1
PROBE(pressure_si, u32, u32)
#endif
#if !defined(PRESSURE_MODE) || PRESSURE_MODE == 2
PROBE(pressure_di, u64, u64)
#endif
#if !defined(PRESSURE_MODE) || PRESSURE_MODE == 3
PROBE(pressure_sf, float, u32)
#endif
#if !defined(PRESSURE_MODE) || PRESSURE_MODE == 4
PROBE(pressure_df, double, u64)
#endif

#ifdef PRESSURE_MAIN
#include <stdio.h>
int main(void)
{
  static const u64 seeds[] = {0, 1, 0x3f800000, 0x80000000,
    0x3ff0000000000000ULL, 0x8000000000000000ULL, ~0ULL};
  unsigned t;
  for (t = 0; t < sizeof seeds / sizeof seeds[0]; ++t)
    {
      u64 s = seeds[t], base = 14 * s + 105;
      u64 si = pressure_si(s), di = pressure_di(s);
      u64 sf = pressure_sf(s), df = pressure_df(s);
      printf("%016llx %016llx %016llx %016llx\n", si, di, sf, df);
      if (si != base + (u32)s || sf != si || di != base + s || df != di)
        return 1;
    }
  return 0;
}
#endif
