# Arctangent and atan2 source exports

The three observed e-width names now have real source definitions:
`_ZGVeN16v_atanf` (6 calls), `_ZGVeN16vv_atan2f` (22), and `_ZGVeN8vv_atan2`
(15). Adding these43 calls to the frozen prior27-name checkpoint reaches
30/36 source-defined names and2,786/2,879 calls (96.77%). At this additive
checkpoint the remaining6 names/93 calls are sinhf/sinh/coshf/cosh/tanhf/tanh.
Target-qualified count remains zero and every target/G5/production flag false.

`src/e_atan_export.c` includes `math_algorithms/atan_e/atan_e_v2.c` once,
renaming the three private pointer kernels. Unary atan uses the unchanged
64-byte adapter; binary atan2 adapters copy both raw vector operands in y,x
order and supply the full software mask. Only this one new production TU is
required, with `include/` and `math_algorithms/atan_e/` on the include path.
There is no scalar atan/atan2 fallback or narrow signature invention.

The official pinned musl v1.2.5 Sun atan reduction, high/low constants and
polynomial provide the mathematical starting point. Complete atan2 special
classification precedes arithmetic; guarded ratios and compensated quadrants
preserve signed-zero/infinity behavior. GCC DP8 vectors perform rational
reductions/polynomials; SP16 uses two DP8 groups and one final SP rounding.

The first direct rounded-ratio→atan composition failed honestly at
y=`6cf75f52a6cfd6a4`, x=`6d0193790d703a98`, with1.0078621130864913ULP. Its
`atan_e.c`, original assay and receipt remain unchanged. The new V2 source
uses exact common-power normalization, Dekker product residuals, an internal
division-tail angle correction and a FastTwoSum low part through quadrant
reconstruction. It fixes that retained input to the MPFR nearest result
`3fe2c6d7759e6287`; V1 returned `3fe2c6d7759e6288`. No tolerance was relaxed.

The fresh V2 screen passes34,173 atanf,34,329 atan2f and33,497 DPatan2 finite
comparisons per contraction variant; maximum ULP bounds are0.4999894192806507,
0.4999994616921789 and0.770186330046773. It checks36 SP/20 DP masks, four
output alias modes, exact merge/zero bits, inactive sNaN poison and invalid
high masks without output/FP effects. Atan2 includes the complete retained
zero/sign/infinity/NaN cross product and the original failed pair.

The subsequent fresh large assay passes1,048,829 atanf and1,048,985 each of
atan2f/atan2 finite comparisons per variant. Maxima are0.49999999097574294,
0.49999911656755214 and0.9180821653690734ULP. Each operation has1,048,576
distinct random finite inputs or pairs plus directed boundaries and specials.
Subnormal first-operand counts are261,624/264,249/262,456 respectively. This
is sampled host evidence, not an exhaustive bound or target numerical proof.

MPFR4.2.2 down/up endpoints at256/384bits agree on rounding. Separate strict
Cygwin GCC14.4 baselineSSE2 contraction-off/fast builds both execute and have
identical complete raw streams. None exceeds1ULP; completed wrong-result
mutants are rejected numerically. Host assembly has240 packed SSE arithmetic
lines and no AVX/mask-register use. No scalar math import is present.

Fresh three-export wiring passes192 calls/2,560 lanes per variant plus192
private software-mask calls and1,280 inactive poison lanes. Output bits,
standard flags and full MXCSR match the independently sampled pointer sources;
exactly these three export symbols are defined. Missing kernels and forbidden
fast-math/research profiles fail explicitly. No prior accuracy suite is rerun.

`atan-exports-v1.json` binds exact source and receipt identities for preserved
V1 failure, V2 screen/large assay and fresh wiring:

- `artifacts/test-state/host-atan-e/d74e20c29d954bc092beb2486bab29d5/accuracy.json`.
- `artifacts/test-state/host-atan-e/15158e3fc26949118273f136707bff64/accuracy.json`.
- `artifacts/test-state/host-atan-e/85b19d6b2add4ece9ec66a330ec0df17/accuracy.json`.
- `artifacts/test-state/host-atan-exports/7c550d3f7f034461bdf6934699bba286/wiring.json`.

Complete inexact/underflow/errno, NaN payload identity, directed rounding,
FMA and unmasked exceptions stay open. Qualified translation/vector widths,
target ABI/masks, generic target FP runtime and actual target numerical tests
remain G5 blockers. Consumed sin/cos/tan sources are unchanged; no card work,
KNC library, target performance or gate pass is claimed.
