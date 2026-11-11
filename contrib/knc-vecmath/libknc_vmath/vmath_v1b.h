/* libknc_vmath v1b (S10-08): what the members written for this library share. A kernel computes
   8 doubles in GCC's generic vectors, with lane selection in place of branches; the 16-float
   function runs the same kernel on its lanes widened to double and rounds each result once,
   which keeps it within 0.5 ULP plus the double kernel's error scaled by 2^-29.

   No contraction: the exact products below (Veltkamp's split, Dekker's product) need every
   operation rounded by itself, and the host and the card then compute the same results. The
   members that take square roots are built with -fno-math-errno (tools/knc_vmath.py), which
   this pragma cannot set, so that sqrt never calls libm. */
#ifndef KNC_VMATH_V1B_H
#define KNC_VMATH_V1B_H
#pragma GCC optimize ("fp-contract=off")
#include <string.h>
#include "knc_vmath.h"
#include "vmath_entry.h"

typedef __knc_vmath_v8df vd;
typedef uint64_t vu __attribute__((vector_size(64)));
typedef int64_t vi __attribute__((vector_size(64)));
#define VD(c) ((vd){ c, c, c, c, c, c, c, c })
#define VU(c) ((vu){ c, c, c, c, c, c, c, c })
#define VABS 0x7fffffffffffffffULL
#define VINF __builtin_inf()
/* Lane i of A where lane i of the comparison M holds, else of B. */
#define VSEL(m, a, b) ((__typeof__(a))(((vu)(a) & (vu)(m)) | ((vu)(b) & ~(vu)(m))))
/* EXPR for each lane l_, as a vector of TYPE: a table read by a vector of indexes. */
#define VGATHER(type, expr) \
  ({ type gathered_; for (int l_ = 0; l_ < 8; ++l_) gathered_[l_] = (expr); gathered_; })

static inline vd vfabs(vd x) { return (vd)((vu)x & VABS); }
static inline vd vcopysign(vd x, vd sign) { return (vd)(((vu)x & VABS) | ((vu)sign & ~VABS)); }
static inline vd vsqrt(vd x) { return VGATHER(vd, __builtin_sqrt(x[l_])); }
/* 2^k for k in [-1022, 1023]. */
static inline vd vpow2(vi k) { return (vd)((vu)(k + 1023) << 52); }
/* y 2^k, rounded once, for y in [1, 2] and k in [-2044, 2046]. */
static inline vd vscale(vd y, vi k) { vi half = k >> 1; return y * vpow2(half) * vpow2(k - half); }
/* k as a double, for |k| < 2^51. */
static inline vd vfromint(vi k) { return (vd)((vu)k + 0x4338000000000000ULL) - 0x1.8p52; }

/* a + b = s + *e exactly. */
static inline vd two_sum(vd a, vd b, vd *e)
{
  vd s = a + b, bb = s - a;
  *e = (a - (s - bb)) + (b - bb);
  return s;
}

/* a b = p + *e exactly, for |a| and |b| below 2^995 and a product that does not underflow. */
static inline vd two_prod(vd a, vd b, vd *e)
{
  vd ca = a * 134217729.0, cb = b * 134217729.0;
  vd ah = ca - (ca - a), al = a - ah, bh = cb - (cb - b), bl = b - bh, p = a * b;
  *e = ((ah * bh - p) + ah * bl + al * bh) + al * bl;
  return p;
}

/* The pointer-form cores of a function of 8 doubles and of 16 floats around the kernels
   DKERNEL and FKERNEL, both on 8 doubles, and their entry points. An inactive lane computes
   on 1.0, which raises no exception in any of these functions. */
#define KNC_VMATH_V1B_MERGE(lanes, word) \
  for (int l = 0; l < lanes; ++l) if (!(active >> l & 1)) y[l] = pass[l]; \
  memcpy(out, y, 64); \
  return 0;
#define KNC_VMATH_V1B_WIDEN(lo, hi, from) \
  for (int l = 0; l < 8; ++l) { \
    lo[l] = active >> l & 1 ? from[l] : 1.0f; hi[l] = active >> (l + 8) & 1 ? from[l + 8] : 1.0f; }
#define KNC_VMATH_V1B_NARROW \
  for (int l = 0; l < 8; ++l) { r[l] = (float)lo[l]; r[l + 8] = (float)hi[l]; } \
  memcpy(y, r, 64);

#define KNC_VMATH_V1B1(name, dkernel, fkernel) \
  static int __knc_vmath_core_##name##_8(const uint64_t in[8], unsigned active, \
                                         const uint64_t merge[8], uint64_t out[8]) \
  { \
    uint64_t pass[8], y[8]; vu x; vd r; \
    if (active & ~0xffu) return 1; \
    memcpy(&x, in, 64); memcpy(pass, merge, 64); \
    for (int l = 0; l < 8; ++l) if (!(active >> l & 1)) x[l] = 0x3ff0000000000000ULL; \
    r = dkernel((vd)x); memcpy(y, &r, 64); \
    KNC_VMATH_V1B_MERGE(8, uint64_t) \
  } \
  static int __knc_vmath_core_##name##f_16(const uint32_t in[16], unsigned active, \
                                           const uint32_t merge[16], uint32_t out[16]) \
  { \
    uint32_t pass[16], y[16]; float x[16], r[16]; vd lo, hi; \
    if (active & ~0xffffu) return 1; \
    memcpy(x, in, 64); memcpy(pass, merge, 64); \
    KNC_VMATH_V1B_WIDEN(lo, hi, x) \
    lo = fkernel(lo); hi = fkernel(hi); \
    KNC_VMATH_V1B_NARROW \
    KNC_VMATH_V1B_MERGE(16, uint32_t) \
  } \
  KNC_VMATH_ENTRIES1(name, 8, vd, uint64_t) \
  KNC_VMATH_ENTRIES1(name##f, 16, __knc_vmath_v16sf, uint32_t)

#define KNC_VMATH_V1B2(name, dkernel, fkernel) \
  static int __knc_vmath_core_##name##_8(const uint64_t in[8], const uint64_t in2[8], unsigned active, \
                                         const uint64_t merge[8], uint64_t out[8]) \
  { \
    uint64_t pass[8], y[8]; vu x, x2; vd r; \
    if (active & ~0xffu) return 1; \
    memcpy(&x, in, 64); memcpy(&x2, in2, 64); memcpy(pass, merge, 64); \
    for (int l = 0; l < 8; ++l) if (!(active >> l & 1)) x[l] = x2[l] = 0x3ff0000000000000ULL; \
    r = dkernel((vd)x, (vd)x2); memcpy(y, &r, 64); \
    KNC_VMATH_V1B_MERGE(8, uint64_t) \
  } \
  static int __knc_vmath_core_##name##f_16(const uint32_t in[16], const uint32_t in2[16], unsigned active, \
                                           const uint32_t merge[16], uint32_t out[16]) \
  { \
    uint32_t pass[16], y[16]; float x[16], x2[16], r[16]; vd lo, hi, lo2, hi2; \
    if (active & ~0xffffu) return 1; \
    memcpy(x, in, 64); memcpy(x2, in2, 64); memcpy(pass, merge, 64); \
    KNC_VMATH_V1B_WIDEN(lo, hi, x) \
    KNC_VMATH_V1B_WIDEN(lo2, hi2, x2) \
    lo = fkernel(lo, lo2); hi = fkernel(hi, hi2); \
    KNC_VMATH_V1B_NARROW \
    KNC_VMATH_V1B_MERGE(16, uint32_t) \
  } \
  KNC_VMATH_ENTRIES2(name, 8, vd, uint64_t) \
  KNC_VMATH_ENTRIES2(name##f, 16, __knc_vmath_v16sf, uint32_t)
#endif
