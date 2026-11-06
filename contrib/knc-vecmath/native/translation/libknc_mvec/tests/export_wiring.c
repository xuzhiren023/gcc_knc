/* Compact HOST-ONLY exported-call wiring check, not a new accuracy oracle. */
#include "knc_mvec_abi.h"
#include "e_algorithms.h"
#include <fenv.h>
#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef union { uint32_t w[16]; uint64_t q[8]; unsigned char bytes[64]; } Words;
static uint64_t random_state = UINT64_C(0x6578706f72742d31);
static uint64_t next_word(void) {
    random_state = random_state * UINT64_C(6364136223846793005)
                 + UINT64_C(1442695040888963407);
    return random_state;
}
static const uint32_t directed32[16] = {
    0, 0x80000000, 1, 0x807fffff, 0x00800000, 0x3f800000, 0xbf800000,
    0x7f7fffff, 0xff7fffff, 0x7f800000, 0xff800000, 0x7fc01234,
    0xff801234, 0x3f7fffff, 0x3f800001, 0x42b17218
};
static const uint64_t directed64[16] = {
    0, UINT64_C(0x8000000000000000), 1, UINT64_C(0x800fffffffffffff),
    UINT64_C(0x0010000000000000), UINT64_C(0x3ff0000000000000),
    UINT64_C(0xbff0000000000000), UINT64_C(0x7fefffffffffffff),
    UINT64_C(0xffefffffffffffff), UINT64_C(0x7ff0000000000000),
    UINT64_C(0xfff0000000000000), UINT64_C(0x7ff8000000001234),
    UINT64_C(0xfff0000000001234), UINT64_C(0x3fefffffffffffff),
    UINT64_C(0x3ff0000000000001), UINT64_C(0x40862e42fefa39f0)
};
static const unsigned operations[10] = {0, 1, 2, 3, 0, 0, 1, 1, 2, 2};
static const unsigned lane_counts[10] = {16, 16, 8, 8, 4, 8, 4, 8, 2, 4};

#define CALL32(NAME, TYPE) do { \
    TYPE x, y; memcpy(&x, input->bytes, sizeof x); \
    y = NAME(x); memcpy(output->bytes, &y, sizeof y); \
} while (0)
static void exported_call(unsigned which, const Words *input, Words *output) {
    switch (which) {
    case 0: CALL32(__knc_vmath_expf_16, knc_mvec_f32x16); break;
    case 1: CALL32(__knc_vmath_logf_16, knc_mvec_f32x16); break;
    case 2: CALL32(__knc_vmath_exp_8, knc_mvec_f64x8); break;
    case 3: CALL32(__knc_vmath_log_8, knc_mvec_f64x8); break;
    case 4: CALL32(__knc_vmath_expf_4, knc_mvec_f32x4); break;
    case 5: CALL32(__knc_vmath_expf_8, knc_mvec_f32x8); break;
    case 6: CALL32(__knc_vmath_logf_4, knc_mvec_f32x4); break;
    case 7: CALL32(__knc_vmath_logf_8, knc_mvec_f32x8); break;
    case 8: CALL32(__knc_vmath_exp_2, knc_mvec_f64x2); break;
    case 9: CALL32(__knc_vmath_exp_4, knc_mvec_f64x4); break;
    }
}
#undef CALL32

static void reset_flags(void) {
    feclearexcept(FE_ALL_EXCEPT);
    _mm_setcsr(0x1f80);
}
static int reference_call(unsigned op, const Words *input, Words *output) {
    switch (op) {
    case 0: return phi_host_expf_e16(input->w, 0xffff, input->w, output->w);
    case 1: return phi_host_logf_e16(input->w, 0xffff, input->w, output->w);
    case 2: return phi_host_exp_e8(input->q, 0xff, input->q, output->q);
    case 3: return phi_host_log_e8(input->q, 0xff, input->q, output->q);
    }
    return 1;
}

int main(int argc, char **argv) {
    const int corrupt = argc == 2 && !strcmp(argv[1], "--wrong-result");
    if (argc != 1 && !corrupt) return 2;
    __builtin_cpu_init();
    if (!__builtin_cpu_supports("avx2") || !__builtin_cpu_supports("fma"))
        return 3;
    if (fesetenv(FE_DFL_ENV) || fegetround() != FE_TONEAREST) return 4;
    unsigned calls = 0, lanes = 0, identities = 0;
    unsigned bit_errors = 0, flag_errors = 0, input_errors = 0, identity_errors = 0;
    for (unsigned which = 0; which < 10; ++which) {
        const unsigned op = operations[which], n = lane_counts[which];
        const unsigned width = op < 2 ? 4 : 8, full = op < 2 ? 16 : 8;
        for (unsigned row = 0; row < 33; ++row) {
            Words input, saved, wide, expected, actual;
            for (unsigned i = 0; i < full; ++i) {
                if (width == 4) {
                    const uint32_t neutral = op == 1 ? UINT32_C(0x3f800000) : 0;
                    wide.w[i] = neutral;
                    input.w[i] = row == 32 ? neutral : row < 16
                        ? directed32[(i + row) & 15] : (uint32_t)(next_word() >> 32);
                    if (row == 32 && op == 0 && (i & 1)) input.w[i] = 0x80000000;
                } else {
                    const uint64_t neutral = op == 3 ? UINT64_C(0x3ff0000000000000) : 0;
                    wide.q[i] = neutral;
                    input.q[i] = row == 32 ? neutral : row < 16
                        ? directed64[(i + row) & 15] : next_word();
                    if (row == 32 && op == 2 && (i & 1)) input.q[i] = UINT64_C(0x8000000000000000);
                }
            }
            saved = input;
            memcpy(wide.bytes, input.bytes, n * width);
            reset_flags();
            if (reference_call(op, &wide, &expected)) return 5;
            const unsigned ref_flags = (unsigned)fetestexcept(FE_ALL_EXCEPT);
            const unsigned ref_csr = _mm_getcsr();
            reset_flags();
            memset(&actual, 0xa5, sizeof actual);
            exported_call(which, &input, &actual);
            const unsigned got_flags = (unsigned)fetestexcept(FE_ALL_EXCEPT);
            const unsigned got_csr = _mm_getcsr();
            if (corrupt && which == 0 && row == 0) expected.w[0] ^= 1;
            for (unsigned i = 0; i < n; ++i) {
                if (width == 4 ? actual.w[i] != expected.w[i] : actual.q[i] != expected.q[i])
                    ++bit_errors;
                if (row == 32) {
                    const uint64_t identity = op == 0 ? UINT64_C(0x3f800000)
                        : op == 2 ? UINT64_C(0x3ff0000000000000) : 0;
                    if (width == 4 ? actual.w[i] != (uint32_t)identity : actual.q[i] != identity)
                        ++identity_errors;
                }
            }
            if (got_flags != ref_flags || got_csr != ref_csr) ++flag_errors;
            if (memcmp(input.bytes, saved.bytes, sizeof input)) ++input_errors;
            if (row == 32) {
                ++identities;
                if (got_flags || (got_csr & 0x3f)) ++identity_errors;
            }
            ++calls; lanes += n;
        }
    }
    printf("{\"hostOnly\":true,\"calls\":%u,\"lanes\":%u,\"identities\":%u,"
           "\"bitErrors\":%u,\"flagErrors\":%u,\"inputErrors\":%u,\"identityErrors\":%u}\n",
           calls, lanes, identities, bit_errors, flag_errors, input_errors, identity_errors);
    return bit_errors || flag_errors || input_errors || identity_errors ? 1 : 0;
}
