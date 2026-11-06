# Arctangent and atan2 source experiment

New sources adapt official musl v1.2.5 Sun atan/atan2 algorithms. Exact official
source bytes, source locks and permissive notices are in `upstream/`. DP8 uses
GCC-vector rational region reduction, compensated atan high/low constants and
the published polynomial. Atan2 classifies signed zeros, infinities and NaNs
before arithmetic, guards extreme ratios and applies the compensated quadrant
formula. SP16 widens two DP8 groups and rounds once. There is no scalar math
fallback. No consumed tangent/cosine/sine source changes.

Full64-byte raw pointer interfaces admit software masks, arbitrary readable
inactive bits, exact output/argument or output/merge aliases, nearest-even,
masked exceptions and FTZ/DAZ off. Invalid high masks return1 unchanged with
zero FP effects. Inactive atan2 lanes become y=0,x=1 before arithmetic. Tiny
atan preserves its argument bits; complete inexact/underflow/errno status,
NaN payload identity, FMA and other rounding/exception profiles remain open.

Before execution the bounded experiment is declared: vary contraction-off/fast
under strict Cygwin GCC14.4 baselineSSE2 without AVX/FMA; compare atan/atan2
with independent MPFR256/384-bit down/up endpoints at≤1ULP. Metrics include
quadrants, signed zero, infinities/NaNs, extreme/scaled ratios, polynomial
regions, subnormals, masks/aliases, ULP histogram/worst input and MXCSR/required
severe status. Over1ULP, bad zero/merge bits, spurious divide-by-zero/overflow,
required-invalid mismatch or changed runtime controls falsifies the result.
Bound effort to one32K screen and focused repairs, then one fresh≥1M corpus
per observed precision/operation after passage. Preserve failed receipts and
never relax the1ULP threshold. Only a passing numerical source permits compact
three-export wiring; target/G5/ABI/ISA/runtime qualification remains false.
