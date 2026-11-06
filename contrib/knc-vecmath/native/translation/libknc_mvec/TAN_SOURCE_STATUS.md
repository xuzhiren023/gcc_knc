# Tangent source exports

The two observed e-width tangent names now have real source definitions:
`_ZGVeN16v_tanf` (19 calls) and `_ZGVeN8v_tan` (15). Added to the frozen prior25
names this reaches27/36 source-defined names and2,743/2,879 calls (95.28%).
The remaining9 names/136 calls are atanf/atan2f/atan2 and six hyperbolics.
Every target/G5/production flag remains false; target-qualified count is zero.

`src/e_tan_export.c` includes the new `math_algorithms/tan_e/tan_e.c` once,
renaming its two private pointer kernels and using the unchanged unmasked
64-byte export adapter. Link the unchanged `src/cos_sin_reducer.c` exactly once
for the complete official musl v1.2.5 small/medium/Payne–Hanek reduction and
private floor/scalbn helpers. Both math directories and `include/` are required
include paths. No narrow tangent signature is invented.

The source adapts official musl/Sun `__tan.c`: degree27 GCC DP8 polynomial,
compensated reduced tail, pi/4 transformation and corrected odd-quadrant
reciprocal. SP16 uses two DP8 groups and one final SP rounding. Unused
transformation/reciprocal lanes are sanitized before arithmetic. There is no
scalar tangent/sine/cosine fallback and no change to consumed cos/sin sources.

The32K screen passes36,238 SP and46,350 DP finite comparisons per variant,
with maximum ULP bounds0.4999781379605695 and0.7922559162073284. It covers
36 SP/20 DP masks, three buffer alias modes, exact zero signs/merge bits,
inactive sNaN/infinity poison and invalid high masks without output/FP effects.
The independent fresh large assay has1,050,174 SP/1,053,750 DP finite
comparisons, with maximum bounds0.4999997288729568/0.7892023105414635.
It includes pole neighbors, reduced tails, pi/4 transform boundaries, maximum
finite inputs,112,387 SP/130,675 DP large-reduction inputs and261,222 SP/
262,259 DP subnormal inputs. These are sample counts, not exhaustive bounds.

MPFR4.2.2 down/up endpoints at256/384bits agree on rounding. Strict Cygwin
GCC14.4 baselineSSE2 contraction-off/fast builds both execute; complete raw
streams are identical. No completed comparison exceeds1ULP, and completed
wrong-result streams are rejected numerically. The candidate imports no scalar
trig/floor/scalbn symbol; host assembly has212 packed SSE arithmetic lines and
no AVX/mask-register use. All required severe/identity checks pass.

Fresh wiring, without repeating an old accuracy experiment, passes128 export
calls/1,536 lanes per variant plus128 private software-mask calls and768
inactive poison lanes. Output bits, standard flags and full MXCSR match the
independently sampled pointer kernels. Exactly the two observed export names
are defined. Missing e-kernels, missing complete reducer and forbidden
fast-math/research profiles fail explicitly.

The additive `tan-exports-v1.json` binds exact sources and these receipts:

- `artifacts/test-state/host-tan-e/a48c4c3b7a264633bb84ac9ec1203c05/accuracy.json`.
- `artifacts/test-state/host-tan-e/318991b3379446daba9eba6390aa5fc2/accuracy.json`.
- `artifacts/test-state/host-tan-exports/ce4933e4ecb44cf5867fa03cf6a01325/wiring.json`.

Full tiny-input inexact/underflow/errno, NaN payload identity, directed rounding,
FMA and unmasked exceptions stay open. KNC vector ABI/masks, generic target FP
runtime, qualified translated instruction forms and target accuracy/performance
remain concrete G5 blockers. No card/runner work or target claim occurred.
