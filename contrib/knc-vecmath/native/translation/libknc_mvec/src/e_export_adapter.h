/* Source integration only: no target ABI, mask, numerical or G5 qualification.
 * The included algorithms and their Arm notices remain byte-exact upstream
 * project inputs. See ../EXPORTS_STATUS.md for the dependency and test contract.
 */
#ifndef KNC_MVEC_E_EXPORT_ADAPTER_H
#define KNC_MVEC_E_EXPORT_ADAPTER_H

#ifdef PW_ENABLE_NEGATIVE_CONTROL
#error "Research negative controls must not enter libknc_mvec export sources"
#endif
#ifdef __FAST_MATH__
#error "libknc_mvec exports forbid fast-math"
#endif

#include "knc_mvec_abi.h"
#include <stdint.h>
#include <string.h>

/* These N exports are unmasked. Passing the full active mask into the preserved
 * pointer implementation keeps its all-active numerical path unchanged.
 * Integer memcpy copies preserve NaN/signaling encodings without conversion.
 */
#define KNC_MVEC_E_EXPORT(NAME, VECTOR, WORD, LANES, ALGORITHM) \
VECTOR NAME(VECTOR x) { \
    WORD input[LANES], output[LANES]; \
    VECTOR result; \
    _Static_assert(sizeof x == sizeof input && sizeof result == sizeof output, \
                   "Full-width export/algorithm size mismatch"); \
    memcpy(input, &x, sizeof input); \
    if (ALGORITHM(input, (1u << (LANES)) - 1u, input, output)) \
        __builtin_trap(); \
    memcpy(&result, output, sizeof result); \
    return result; \
}

#endif
