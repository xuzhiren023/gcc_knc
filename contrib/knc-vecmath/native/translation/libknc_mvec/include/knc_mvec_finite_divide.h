/* Scoped finite DP division for the atan implementation. Numerators may be
 * signed zero; denominators are finite nonzero by atan's range classification.
 * No FP environment normalization. Generic DIV flags remain unqualified. */
#ifndef KNC_MVEC_FINITE_DIVIDE_H
#define KNC_MVEC_FINITE_DIVIDE_H
#include <stdint.h>
#include <string.h>
typedef double pw_div8 __attribute__((vector_size(64)));
extern pw_div8 knc_mvec_divide_finite_nonzero_e8(pw_div8,pw_div8);
static __attribute__((noinline,noipa,optimize("no-tree-vectorize","no-tree-slp-vectorize")))
pw_div8 pw_mvec_divide_finite(pw_div8 numerator,pw_div8 denominator) {
  union words {pw_div8 vector;uint64_t lane[8];};
  volatile union words n,d,safe,result;
  n.vector=numerator;d.vector=denominator;
  for(unsigned i=0;i<8;++i)
    safe.lane[i]=(n.lane[i]&UINT64_C(0x7fffffffffffffff))?n.lane[i]:UINT64_C(0x3ff0000000000000);
  result.vector=knc_mvec_divide_finite_nonzero_e8(safe.vector,denominator);
  for(unsigned i=0;i<8;++i)
    if(!(n.lane[i]&UINT64_C(0x7fffffffffffffff)))
      result.lane[i]=(n.lane[i]^d.lane[i])&UINT64_C(0x8000000000000000);
  return result.vector;
}
#endif
