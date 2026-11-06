# DP8/SP16 complete-domain tangent source experiment

This adapts the exact pinned official musl v1.2.5 Sun `__tan.c` polynomial,
pi/4 transform and compensated reciprocal. It reuses the frozen complete
small/medium/Payne–Hanek reducer in `../cos_sin_e/reducer.c` unchanged. The
original source, dispatch references and license/source lock are in `upstream/`.
No scalar tangent/sine/cosine function supplies a lane result.

DP8 uses genuine GCC vector arithmetic; SP16 uses two DP8 groups and rounds
once. Per-lane classification precedes arithmetic. Inactive/nonfinite/tiny
inputs are sanitized to zero. Unused transform lanes subtract exact matching
constants; unused reciprocal lanes divide by1. This prevents inactive poison
or unused even-quadrant reciprocals from raising FP exceptions. Tiny tangent
preserves the input bits, including signed zero; full tiny inexact/underflow
status remains unqualified. Active sNaN/infinity uses a vector x−x path.

The full64-byte raw pointer/software-mask ABI supports exact input/output and
merge/output aliases. Invalid high masks return1 unchanged with no FP effects.
Partial overlap is unspecified. Only nearest-even, masked exceptions and
FTZ/DAZ off are admitted. No target ABI/ISA, runtime, G5 or performance claim
follows from this source work.

Before execution the bounded experiment is declared: vary contraction-off/fast
under strict Cygwin GCC14.4 baselineSSE2 without AVX/FMA; expect≤1ULP against
independent MPFR256/384-bit directed endpoints, exact merge/zero identities and
required invalid effects without spurious divide-by-zero/overflow. Metrics
include ULP histogram/worst input, poles and their neighbors, pi/4 transform,
large reductions, subnormals, masks, aliases and full MXCSR control. Any wrong
zero sign, over1ULP value, inactive poison effect, required-flag mismatch or
profile/packet mismatch falsifies the experiment. Effort is one32K screen plus
focused repairs; only after passage, one fresh1M corpus per format. Preserve
failed records; do not relax the1ULP threshold. A passed assay permits only
compact source export wiring; target qualification stays open.
