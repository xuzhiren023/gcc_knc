/* libknc_vmath v0: pointer-form cores of the copied vector math (ADR-0011, ADR-0014 point 3).

   Each core reads LANES input words (bit patterns of float or double), computes the active lanes
   (bit i of ACTIVE), copies the inactive lanes from MERGE, and writes OUT. It returns nonzero only
   for an ACTIVE bit above LANES. Round to nearest, IEEE special values; errno is never set. The
   by-value entry points __knc_vmath_<name>_<lanes> wrap these cores (S10-03). */
#ifndef KNC_VMATH_H
#define KNC_VMATH_H
#include <stdint.h>

#ifdef __FAST_MATH__
#error "libknc_vmath is built without fast-math (ADR-0014 point 4)"
#endif

int __knc_vmath_core_expf_16(const uint32_t in[16], unsigned active, const uint32_t merge[16],
                             uint32_t out[16]);
int __knc_vmath_core_logf_16(const uint32_t in[16], unsigned active, const uint32_t merge[16],
                             uint32_t out[16]);
int __knc_vmath_core_powf_16(const uint32_t x[16], const uint32_t y[16], unsigned active,
                             const uint32_t merge[16], uint32_t out[16]);
int __knc_vmath_core_exp_8(const uint64_t in[8], unsigned active, const uint64_t merge[8],
                           uint64_t out[8]);
int __knc_vmath_core_log_8(const uint64_t in[8], unsigned active, const uint64_t merge[8],
                           uint64_t out[8]);
int __knc_vmath_core_pow_8(const uint64_t x[8], const uint64_t y[8], unsigned active,
                           const uint64_t merge[8], uint64_t out[8]);
#endif
