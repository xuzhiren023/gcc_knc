# Double-precision pow source extension

`src/e_pow_export.c` and `src/pow_wrappers.c` now define `_ZGVeN8vv_pow`,
`_ZGVdN4vv_pow` and `_ZGVbN2vv_pow`. They cover291/33/4 retained calls.
Combined with the prior13 exp/log/powf definitions,16 of36 names have real
source definitions, covering2,261 of2,879 calls (78.53%).20 names remain
declaration-only. This is additive source coverage; every target/G5 flag is
false. Original scaffold/header and prior receipt-bound algorithms are unchanged.

The new8-DP GCC-vector kernel adapts the pinned official Arm v26.01 pow
algorithm/data, preserving compensated log/product, exp tail and signed
subnormal correction. Its exact sources, coefficients/configuration and
transformation are in `math_algorithms/pow_e8/`. It has no scalar math fallback.
The binary source adapter and two narrow wrappers preserve low arguments and
fill other wide lanes with1/0.

Both host variants use Cygwin GCC14.4 with strict baselineSSE2, noAVX/FMA,
nearest-even, masked exceptions and FTZ/DAZ off. Contraction-off/fast are
separate builds, with identical numerical output; neither is FMA evidence.

| New test | Actual outcome per variant |
|---|---|
| Screening |39,624 active/320 inactive lanes;33,484 finite comparisons; max0.5035292014842014ULP;20 masks, four aliases, exact-identity inactive poison, special values, compensated cancellation and parity boundaries. |
| Fresh MPFR assay |1,312,488 active inputs;1,072,628 finite ULP comparisons including167,869 rounded zeros;68,820 NaNs;171,040 infinities. |
| ULP histogram |1,071,863≤0.5;765 in(0.5,0.75]; none above0.75; max0.5068320211096088ULP. |
| Coverage |394,059 negative bases;629,667 negative exponents;572 subnormal bases;52,870 subnormal exponents;125,405 finite inputs with abs(y)>2^53. Directed screen adds subnormal/range and near-one/huge-exponent boundaries. |
| Source wiring |192 calls/896 lanes, all three e/b/d symbols defined, zero bit/standard-flag/full-MXCSR differences against the independently sampled pointer kernel; no scalar imports; missing/forbidden source profiles rejected. |

MPFR4.2.2 supplies independent down/up pow endpoints at256 and384 bits, all
agreeing on binary64 rounding. Completed wrong-result streams fail numerically.
The sample is broad, not exhaustive. NaN checks establish quiet classification,
not payload identity; the numerical oracle checks invalid/divzero and mandatory
overflow effects, not complete inexact/underflow/errno conformance. The
screen's identity vectors prove that inactive poison creates no FP status.

The exact source-scoped records are under `artifacts/test-state/host-pow-e8/`:
screen`a84a2698ffb142dfbffb4927cd654812/accuracy.json`, large
`51aa2ba8c9e544279d08e0c8dc406ea3/accuracy.json`; wiring is
`artifacts/test-state/host-pow-exports/413b4c4ccbb74334a8c0fd5f71303c91/wiring.json`.
Their SHA256 values are retained in additive `pow-exports-v1.json`.

The concrete G5 blocker remains pipeline/target integration: qualified vector
arithmetic/width rules, measured KNC binary vector ABI and entry-mask behavior,
generic target FP runtime, then actual target1e6-input/special/ULP validation.
No target compilation, card execution, mask exemption or G5 receipt is created
by these host sources. FMA, directed rounding, errno and unmasked exceptions
remain open. No baseline/BIND change or unchanged corpus rerun occurred.
