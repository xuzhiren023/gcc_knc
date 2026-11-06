/* Additive source-only lookup representation for atan_e_v3_scalar_bookkeeping.c.
 * Exact retained musl/Sun atanhi/atanlo binary64 words, low dword first.
 * Four coefficients occupy words0..7; words8..15 are positive-zero pairs.
 * This source preparation claims no generated ISA, target ABI or G5 result.
 */
#ifndef PHI_ATAN_E_V3_REGISTER_TABLES_H
#define PHI_ATAN_E_V3_REGISTER_TABLES_H
#if !defined(__BYTE_ORDER__) || __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "atan paired-dword tables require little-endian x86"
#endif
typedef uint32_t pw_atan_u32v __attribute__((vector_size(64)));
static const pw_atan_u32v pw_atan_hi_words __attribute__((aligned(64))) = {
  UINT32_C(0x0561bb4f), UINT32_C(0x3fddac67),
  UINT32_C(0x54442d18), UINT32_C(0x3fe921fb),
  UINT32_C(0xd281f69b), UINT32_C(0x3fef730b),
  UINT32_C(0x54442d18), UINT32_C(0x3ff921fb),
  0, 0, 0, 0, 0, 0, 0, 0
};
static const pw_atan_u32v pw_atan_lo_words __attribute__((aligned(64))) = {
  UINT32_C(0x222f65e2), UINT32_C(0x3c7a2b7f),
  UINT32_C(0x33145c07), UINT32_C(0x3c81a626),
  UINT32_C(0x7af0cbbd), UINT32_C(0x3c700788),
  UINT32_C(0x33145c07), UINT32_C(0x3c91a626),
  0, 0, 0, 0, 0, 0, 0, 0
};
_Static_assert(sizeof(pw_atan_hi_words)==64 && sizeof(pw_atan_lo_words)==64,
               "atan register tables must be complete64B vectors");
static PW_ATAN_SCALAR_HELPER void pw_atan_selector_scalar(const int id[8],uint32_t selector[16]) {
  for(unsigned i=0;i<8;++i) {
    const unsigned first=id[i]<0?8u:2u*(unsigned)id[i];
    selector[2*i]=first;selector[2*i+1]=first+1u;
  }
}
static __attribute__((always_inline)) inline void
pw_atan_register_lookup(const int id[8],dv *high,dv *low) {
  pw_atan_u32v selector;uint32_t selector_words[16];
  pw_atan_selector_scalar(id,selector_words);memcpy(&selector,selector_words,64);
  const pw_atan_u32v high_words=__builtin_shuffle(pw_atan_hi_words,selector);
  const pw_atan_u32v low_words=__builtin_shuffle(pw_atan_lo_words,selector);
  memcpy(high,&high_words,64);memcpy(low,&low_words,64);
}
#endif
