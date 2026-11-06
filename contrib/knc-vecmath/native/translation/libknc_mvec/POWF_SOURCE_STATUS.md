# Powf source extension and independent host accuracy

The new powf family adds `_ZGVeN16vv_powf`, `_ZGVdN8vv_powf` and
`_ZGVbN4vv_powf`:609 of the retained2,879 calls (593/7/9 respectively).
Together with the prior ten definitions, this gives13 source-defined names
and23 declaration-only names. All target ABI/numerical/mask/runtime/G5
qualification flags remain false. `powf-exports-v1.json` is additive; the
receipt-bound original header/scaffold/exports manifest and four earlier math
families remain unchanged.

The kernel is a16-lane GCC-vector adaptation of the pinned Arm v26.01 scalar
powf reduction/polynomials/data. It uses16-DP intermediates and special-lane
sanitization, not scalar pow or a composition of approximate expf/logf. The e
adapter supplies both vector operands to its private bit-preserving pointer
interface. The b4/d8 wrappers fill other wide lanes with1/0 before calling e16.
The exact official sources/license and transformation are recorded in
`math_algorithms/powf_e16/README.md`.

New host evidence, Cygwin GCC14.4, strict baselineSSE2, noAVX/FMA, nearest-even,
masked exceptions, FTZ/DAZ off:

| Assay | Evidence |
|---|---|
| Directed/masks/aliases screening |35,072 active and1,152 merge lanes per variant; max0.502629691554737ULP;36 masks, four alias modes, specials; invalid high mask unchanged/zero FP; complete wrong-result stream rejected. |
| Fresh large MPFR assay |1,314,816 inputs per variant;1,150,467 finite ULP comparisons,77,677 NaNs,86,672 infinities; finite count includes82,461 rounded zeros. MPFR4.2.2 down/up at256/384bits agrees on rounding. |
| ULP histogram, both variants |1,149,824≤0.5;643 in(0.5,0.75]; zero above0.75; max0.505089905719066ULP. |
| Domain coverage |395,256 negative bases;631,220 negative exponents;4,673 subnormal bases;54,174 subnormal exponents;107,482 inputs with finite abs(y)>2^24. This is a deterministic sample, not exhaustive binary32 coverage. |
| New source wiring |192 calls/1,792 lanes per variant through separately compiled e/b/d definitions; zero bit/standard-flag/full-MXCSR differences against the independently sampled pointer algorithm. All three names defined; no scalar math import; missing e kernel and forbidden profiles rejected. |

Contraction-off and contraction-fast are separate builds but both disable FMA;
their raw output hashes agree. The numeric oracle checks quiet-NaN
classification (not payload identity), exact special signs, invalid/divzero and
mandatory overflow effects. It does not establish complete inexact/underflow,
errno, directed-rounding or unmasked-exception conformance. The screening also
checks that inactive poison cannot raise FP effects. Wiring equality checks the
boundary against that algorithm, not an independent second approximation.

The actual source-scoped records are:

- Screening `artifacts/test-state/host-powf-e16/9275dbbcb2ed45809f670e7821118e6d/accuracy.json`, SHA256`bf79977b48c6ba195442eaab12a8cedd6c49c362e5a079400ff9c8188e7978e0`.
- Large assay `artifacts/test-state/host-powf-e16/4afa5507f47849ccae051e0bc42816da/accuracy.json`, SHA256`d444937a07e797a7b10abba89a59c22fcca091443e13dee8740e66175ee0a374`.
- Wiring `artifacts/test-state/host-powf-exports/7a6098ecf4114e6fa5febe8db4b9e493/wiring.json`, SHA256`10a6b64b893b55b6fa9d5895cdb15a732592d82a201e6aecfcc74940df27b12e`.

The first AVX2 host attempt stopped before numeric validation with exit2816.
Its source snapshots and scoped spill/layout diagnosis are preserved under
`host-powf-e16/5d4e2aa785044694967cf2801c94bd9c`. A strace-altered normal exit
was diagnostic only. BaselineSSE2 supplies honest host algorithm evidence;
it does not repair or qualify that AVX2 ABI concern.

Concrete next G5 boundary: translate/link/run these C sources with the measured
KNC vector ABI, D1 entry masks and target FP runtime, then repeat the target
accuracy/mask/special checks. Earlier exp/log source generation already exposes
unqualified vpgatherqq/vpmaskmovq/vpsraq. This extension neither qualifies those
nor compiles a KNC library. There was no card contact or public G5 gate.
