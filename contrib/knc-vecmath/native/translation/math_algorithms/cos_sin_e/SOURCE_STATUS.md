# Implemented host source boundary and measured result

The four private kernels `phi_host_sin_e8`, `phi_host_cos_e8`,
`phi_host_sinf_e16` and `phi_host_cosf_e16` are implemented. Every finite input
has a complete reduction path; there is no pending huge-argument reducer or
scalar trigonometric delegation. Small/medium reduction and the complete
Payne–Hanek body are the exact pinned musl v1.2.5 sources, compiled through
private symbol remapping. `floor` and `scalbn` are also official internal source
bodies, not imported host math functions.

The vector adaptation evaluates the tail-aware Sun sine expression uniformly,
including unreduced lanes whose low part is zero. It evaluates both sine and
cosine DP8 polynomials, then selects/signs the appropriate result by quadrant;
this is an accuracy-first source implementation with no performance claim.
SP16 uses two DP8 groups and one final SP rounding. Tiny inputs bypass
polynomial arithmetic. Sine preserves their input bits; cosine returns1.
This intentionally leaves full tiny-input inexact/underflow behavior open.

The bounded screen passed for both contraction variants:

| Function | Active / inactive lanes | Finite comparisons | Maximum ULP bound |
|---|---:|---:|---:|
| sinf |35,552 /864|35,294|0.499973970113627|
| cosf |35,552 /864|35,294|0.4999639390636545|
| sin |45,672 /240|45,414|0.7343813204820421|
| cos |45,672 /240|45,414|0.7445949890308055|

Screen receipt:
`artifacts/test-state/host-cos-sin-e/bc822707ec224c6e9cd79dc711a19106/accuracy.json`,
SHA256`b6279977170033962037b30cb60903f28bfbcbbada754563e95b0c19b194ba58`.
It covers36 SP/20 DP masks, three buffer alias modes, inactive sNaN/infinity
poison, exact signed-zero identities and invalid high masks with unchanged
output/zero FP effects.

The subsequent fresh large assay passed without changing any used source:

| Function | Active lanes | Finite comparisons | Maximum ULP bound |
|---|---:|---:|---:|
| sinf |1,049,488|1,049,230|0.4999989419321134|
| cosf |1,049,488|1,049,230|0.49999960186250003|
| sin |1,053,064|1,052,806|0.7705709129503738|
| cos |1,053,064|1,052,806|0.745124648867273|

Large receipt:
`artifacts/test-state/host-cos-sin-e/48f04bfa159d40b18524ae282a944e0e/accuracy.json`,
SHA256`63049beabc3586a5ca5e39da259591eeff606318072ef9dabf396127ff22ccd9`.
Each format has1,048,576 distinct random finite inputs plus directed/special
cases. SP has111,934 large-reduction inputs and261,076 subnormal inputs;
DP has130,760 large-reduction inputs and262,262 subnormal inputs. These are
sample counts, not exhaustive accuracy bounds. Each operation also checks258
active nonfinite inputs, including infinities returning quiet NaN.

Both use Cygwin GCC14.4, strict baselineSSE2, noAVX/FMA, nearest-even, masked
exceptions and FTZ/DAZ off. MPFR4.2.2 down/up endpoints at256/384bits agree on
binary32/binary64 rounding. Separate contraction-off/fast builds both execute;
their complete raw streams are byte-identical, so the fast result reuses the
off MPFR comparison through recorded full equality. No completed comparison
exceeds1ULP. Each complete wrong-result mutant is rejected numerically.
The candidate executables import no scalar trig/floor/scalbn symbol; generated
host assembly contains172 packed SSE arithmetic lines and no AVX/mask register.

Integration compiles `cos_sin_e.c` once and `reducer.c` once, with this directory
on the include path. A combined export adapter can macro-rename all four
`phi_host_*` names before including `cos_sin_e.c` once. The five observed
external names are DP sin e8, DP cos e8/b2, and SP sinf/cosf e16; only DP cos
needs a narrow wrapper. This source work does not define those library exports.

No host numerical blocker remains in the declared sampled profile. Complete
inexact/underflow/errno, NaN payloads, directed rounding, FMA and unmasked
exceptions remain unqualified. KNC vector ABI/mask semantics, generic FP
runtime, translated instruction forms, target accuracy and performance remain
open. All target/G5 qualification flags stay false. No card job or commit ran.
