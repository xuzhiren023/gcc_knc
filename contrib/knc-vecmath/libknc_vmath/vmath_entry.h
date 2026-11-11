/* libknc_vmath: the by-value entry point of a member, defined after its copied core (ADR-0014
   point 3). All lanes are active, so the merge operand is never read into the result. */
#ifndef KNC_VMATH_ENTRY_H
#define KNC_VMATH_ENTRY_H
#include "knc_vmath.h"

#define KNC_VMATH_ENTRY1(name, lanes, vector, word) \
  vector __knc_vmath_##name##_##lanes(vector x) \
  { \
    union { vector v; word w[lanes]; } in = { x }, out; \
    __knc_vmath_core_##name##_##lanes(in.w, (1u << lanes) - 1, in.w, out.w); \
    return out.v; \
  }

#define KNC_VMATH_ENTRY2(name, lanes, vector, word) \
  vector __knc_vmath_##name##_##lanes(vector x, vector y) \
  { \
    union { vector v; word w[lanes]; } in = { x }, in2 = { y }, out; \
    __knc_vmath_core_##name##_##lanes(in.w, in2.w, (1u << lanes) - 1, in.w, out.w); \
    return out.v; \
  }

/* v1a members: the entry point and its masked form (knc_vmath.h). An inactive lane takes the
   first argument's bits through the core's merge operand; mask bits above the lanes are dropped,
   as a caller need not clear them. */
#define KNC_VMATH_ENTRIES1(name, lanes, vector, word) \
  KNC_VMATH_ENTRY1(name, lanes, vector, word) \
  vector __knc_vmath_##name##_##lanes##_m(vector x, unsigned mask) \
  { \
    union { vector v; word w[lanes]; } in = { x }, out; \
    __knc_vmath_core_##name##_##lanes(in.w, mask & ((1u << lanes) - 1), in.w, out.w); \
    return out.v; \
  }

#define KNC_VMATH_ENTRIES2(name, lanes, vector, word) \
  KNC_VMATH_ENTRY2(name, lanes, vector, word) \
  vector __knc_vmath_##name##_##lanes##_m(vector x, vector y, unsigned mask) \
  { \
    union { vector v; word w[lanes]; } in = { x }, in2 = { y }, out; \
    __knc_vmath_core_##name##_##lanes(in.w, in2.w, mask & ((1u << lanes) - 1), in.w, out.w); \
    return out.v; \
  }
#endif
