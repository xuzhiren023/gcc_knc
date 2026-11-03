/* S2-04 T1: ADR-0004 point 6. Keep 14 allocatable GPRs live across scalar
   transfers in both directions. Empty matching asms preserve the bits while
   requiring LRA to cross the GPR/zmm boundary, rather than expansion doing it.
   The host reference uses the same integer bits without a register-bank move.
   Leave r15 free for both bits and the allocated mask scratch; transfer
   addresses must use rsp under this pressure. Define PRESSURE_MAIN for the
   eventual tools/card_run comparison, or PRESSURE_MODE=1..10 to isolate a case.
   TI/TF need two GPRs and therefore use separate, unconstrained probes. */
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

/* Unlike matching operands of different modes, these unions leave a SUBREG
   on the bank-crossing move presented to TARGET_SECONDARY_RELOAD. */
#define FROM_FP(TYPE, UTYPE) \
  union { TYPE fp; UTYPE integer; } view; \
  __asm__ volatile ("# bitcast-fp-input" : "=YJ"(view.fp) : "0"((UTYPE)seed)); \
  bits = view.integer; \
  __asm__ volatile ("# bitcast-gpr-output" : "+r"(bits))
#define TO_FP(TYPE, UTYPE) \
  union { TYPE fp; UTYPE integer; } view; \
  view.integer = (UTYPE)seed; \
  __asm__ volatile ("# bitcast-gpr-input" : "+r"(view.integer)); \
  __asm__ volatile ("# bitcast-fp-output" : "+YJ"(view.fp)); \
  bits = view.integer
#else
#define TRANSFER(TYPE, UTYPE) bits = (UTYPE)seed
#define FROM_FP(TYPE, UTYPE) bits = (UTYPE)seed
#define TO_FP(TYPE, UTYPE) bits = (UTYPE)seed
#endif

#define PROBE(NAME, TYPE, UTYPE, MOVE) \
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
  MOVE(TYPE, UTYPE); \
  LIVE; \
  return bits + a + b + c + d + e + f + g + h + i + j + k + l + m + n; \
}

#if !defined(PRESSURE_MODE) || PRESSURE_MODE == 1
PROBE(pressure_si, u32, u32, TRANSFER)
#endif
#if !defined(PRESSURE_MODE) || PRESSURE_MODE == 2
PROBE(pressure_di, u64, u64, TRANSFER)
#endif
#if !defined(PRESSURE_MODE) || PRESSURE_MODE == 3
PROBE(pressure_sf, float, u32, TRANSFER)
#endif
#if !defined(PRESSURE_MODE) || PRESSURE_MODE == 4
PROBE(pressure_df, double, u64, TRANSFER)
#endif

#if !defined(PRESSURE_MODE) || PRESSURE_MODE == 5
PROBE(pressure_sf_u32, float, u32, FROM_FP)
#endif
#if !defined(PRESSURE_MODE) || PRESSURE_MODE == 6
PROBE(pressure_u32_sf, float, u32, TO_FP)
#endif
#if !defined(PRESSURE_MODE) || PRESSURE_MODE == 7
PROBE(pressure_df_u64, double, u64, FROM_FP)
#endif
#if !defined(PRESSURE_MODE) || PRESSURE_MODE == 8
PROBE(pressure_u64_df, double, u64, TO_FP)
#endif

typedef unsigned __int128 u128;
#if !defined(PRESSURE_MODE) || PRESSURE_MODE == 9
__attribute__((noinline, noclone)) u128 pressure_ti(u128 bits)
{
  __asm__ volatile ("# pair-gpr-input" : "+r"(bits));
#ifdef __KNC__
  __asm__ volatile ("# pair-zmm" : "+YJ"(bits));
#endif
  __asm__ volatile ("# pair-gpr-output" : "+r"(bits));
  return bits;
}
#endif
#if !defined(PRESSURE_MODE) || PRESSURE_MODE == 10
__attribute__((noinline, noclone)) u128 pressure_tf(u128 bits)
{
  union { __float128 fp; u128 integer; } view;
  view.integer = bits;
  __asm__ volatile ("# pair-gpr-input" : "+r"(view.integer));
#ifdef __KNC__
  __asm__ volatile ("# pair-zmm" : "+YJ"(view.fp));
#endif
  __asm__ volatile ("# pair-gpr-output" : "+r"(view.integer));
  return view.integer;
}
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
