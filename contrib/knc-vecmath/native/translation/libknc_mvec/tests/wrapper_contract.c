/* HOST-ONLY wrapper-contract sentinels, never mathematical implementations.
 * Build both this file and wrappers with the same baseline host ABI. No KNL
 * code, target ABI, floating exception, or numerical qualification follows.
 */
#ifndef KNC_MVEC_WRAPPER_CONTRACT_TEST
#error "Test sentinel kernels must not enter a production library"
#endif
#include "knc_mvec_abi.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static uint32_t expected32[16];
static uint64_t expected64[8];
static unsigned active, family;
static uint64_t calls, errors, input_lanes, output_lanes, inactive_lanes;
static uint32_t state = UINT32_C(0x15792831);

static uint32_t random32(void) {
    state = state * UINT32_C(1664525) + UINT32_C(1013904223);
    return state;
}
static float from32(uint32_t bits) { float x; memcpy(&x, &bits, 4); return x; }
static double from64(uint64_t bits) { double x; memcpy(&x, &bits, 8); return x; }
static uint32_t bits32(float x) { uint32_t bits; memcpy(&bits, &x, 4); return bits; }
static uint64_t bits64(double x) { uint64_t bits; memcpy(&bits, &x, 8); return bits; }
static uint32_t tag32(unsigned kind, unsigned lane) { return UINT32_C(0x40000000) + 4096 * kind + lane; }
static uint64_t tag64(unsigned lane) { return UINT64_C(0x4000000000000000) + lane; }

static knc_mvec_f32x16 check32(knc_mvec_f32x16 x, unsigned kind) {
    knc_mvec_f32x16 result;
    ++calls;
    if (family != kind) ++errors;
    for (unsigned i = 0; i < 16; ++i) {
        uint32_t neutral = kind == 1 ? UINT32_C(0) : UINT32_C(0x3f800000);
#ifdef KNC_TEST_EXPECT_WRONG_NEUTRAL
        if (kind == 1) neutral = UINT32_C(0x3f800000);
#endif
        uint32_t expected = i < active ? expected32[i] : neutral;
        if (bits32(x[i]) != expected) ++errors;
        ++input_lanes;
        if (i >= active) ++inactive_lanes;
        result[i] = from32(tag32(kind, i));
    }
    return result;
}
knc_mvec_f32x16 __knc_vmath_expf_16(knc_mvec_f32x16 x) { return check32(x, 1); }
knc_mvec_f32x16 __knc_vmath_logf_16(knc_mvec_f32x16 x) { return check32(x, 2); }
knc_mvec_f64x8 __knc_vmath_exp_8(knc_mvec_f64x8 x) {
    knc_mvec_f64x8 result;
    ++calls;
    if (family != 3) ++errors;
    for (unsigned i = 0; i < 8; ++i) {
        uint64_t neutral = 0;
#ifdef KNC_TEST_EXPECT_WRONG_NEUTRAL
        neutral = UINT64_C(0x3ff0000000000000);
#endif
        uint64_t expected = i < active ? expected64[i] : neutral;
        if (bits64(x[i]) != expected) ++errors;
        ++input_lanes;
        if (i >= active) ++inactive_lanes;
        result[i] = from64(tag64(i));
    }
    return result;
}

#define TEST32(TYPE, LANES, NAME, KIND) do { \
    TYPE x; active = (LANES); family = (KIND); \
    for (unsigned i = 0; i < (LANES); ++i) { \
        expected32[i] = random32(); x[i] = from32(expected32[i]); \
    } \
    TYPE result = NAME(x); \
    for (unsigned i = 0; i < (LANES); ++i) { \
        if (bits32(result[i]) != tag32((KIND), i)) ++errors; \
        ++output_lanes; \
    } \
} while (0)

#define TEST64(TYPE, LANES, NAME) do { \
    TYPE x; active = (LANES); family = 3; \
    for (unsigned i = 0; i < (LANES); ++i) { \
        uint64_t hi = random32(); expected64[i] = (hi << 32) | random32(); \
        x[i] = from64(expected64[i]); \
    } \
    TYPE result = NAME(x); \
    for (unsigned i = 0; i < (LANES); ++i) { \
        if (bits64(result[i]) != tag64(i)) ++errors; \
        ++output_lanes; \
    } \
} while (0)

int main(void) {
    for (unsigned n = 0; n < 2048; ++n) {
        TEST32(knc_mvec_f32x4, 4, __knc_vmath_expf_4, 1);
        TEST32(knc_mvec_f32x8, 8, __knc_vmath_expf_8, 1);
        TEST32(knc_mvec_f32x4, 4, __knc_vmath_logf_4, 2);
        TEST32(knc_mvec_f32x8, 8, __knc_vmath_logf_8, 2);
        TEST64(knc_mvec_f64x2, 2, __knc_vmath_exp_2);
        TEST64(knc_mvec_f64x4, 4, __knc_vmath_exp_4);
    }
    if (calls != 12288 || input_lanes != 163840 || output_lanes != 61440 || inactive_lanes != 102400)
        ++errors;
    printf("WRAPPER_CONTRACT calls=%" PRIu64 " input=%" PRIu64
           " output=%" PRIu64 " inactive=%" PRIu64 " errors=%" PRIu64 "\n",
           calls, input_lanes, output_lanes, inactive_lanes, errors);
    return errors ? 1 : 0;
}
