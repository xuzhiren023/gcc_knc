# DP8/SP16 hyperbolic algorithm experiment

This new source implements the six observed e-width `sinhf/sinh/coshf/cosh/tanhf/tanh`
names (93 census call sites). It retains official musl v1.2.5 math sources and
their Sun/musl notices in `upstream/`; `source-lock.json` pins the original bytes.
No scalar math routine supplies a lane result.

The official Sun `expm1.c` split-ln2 reduction and five rational coefficients
are evaluated with GCC 64-byte vector double-double arithmetic. Compensation
uses contraction-off arithmetic even when the surrounding compilation permits
FMA. Small arguments use cancellation-safe expm1 identities for sinh/cosh, then
their compensated quotient for tanh. Large sinh/cosh use scaled exp reduction
without overflowing compensated intermediates. Tanh saturates for |x|>=20.
SP16 widens to two DP8 groups and rounds once. These choices strengthen the
upstream tanh implementation, whose own commentary permits a two-ULP interval;
the project target remains at most one ULP.

Bit classification sanitizes inactive lanes, infinities, NaNs and tiny inputs
before arithmetic. Exact signed zeros, NaN payload/sign quieting, invalid for
active signaling NaNs, required inexact/underflow/overflow and unchanged FP
controls are checked. Full 64-byte input/output or merge/output aliases are
supported. Partial overlap is unspecified. Only nearest-even with masked
exceptions and FTZ/DAZ off is admitted by this host algorithm experiment.

The declared experiment varies contraction-off/fast under strict Cygwin GCC
baseline SSE2 (no AVX/FMA). An independent MPFR 4.2.2 executable computes directed
256/384-bit bounds. Both precisions must agree on nearest rounding and enclose
the result with an error bound <=1 ULP. Any wrong zero sign, nonfinite payload,
mask merge, required/extra exception, control-bit change or over-one-ULP result
stops the assay. One fresh 32K screen is followed by 1,048,576 new unique finite
inputs per operation/precision, mixed with overflow/saturation/tiny boundaries,
subnormals, NaNs/infinities, masks, aliases and a completed wrong-output negative.
No runtime profile, KNC ISA/ABI, G5 pass or target speed claim follows.

The first screen stopped at a scale-construction boundary: SP input 0x4431bf00
widened to an argument above the true double sinh overflow threshold but below
the initial certain-overflow classifier. Its reduction attempted exponent 1025.
The stopped record remains in `host-hyperbolic-e/7bb05d01be2540c9aba7f67aee6d9bd7`.
The classifier is now |x|>710.5, above the true threshold (~710.47586), before
scale construction. The repaired 32K screen passed in
`host-hyperbolic-e/2cf60ac1c5cb4d4e89278bf1a11116a5`: worst bounds were 0.499990,
0.530941, 0.499996, 0.533171, 0.499995, 0.499992 ULP respectively. All twelve
operation/format/contraction variants had zero value/merge/severe-flag mismatches.

The fresh million-input assay also passed all twelve variants:
`host-hyperbolic-e/a9c8afc6431b42e18fc30d04c164637d/accuracy.json`. Each
operation/format used 1,048,576 new unique finite inputs, plus the boundary,
special and mask packets. Worst MPFR upper bounds were:

| Function | Worst ULP upper bound |
| --- | ---: |
| sinhf | 0.499998875 |
| sinh | 0.530940535 |
| coshf | 0.499997815 |
| cosh | 0.533171500 |
| tanhf | 0.499998883 |
| tanh | 0.499998984 |

Off/fast results agreed. Every variant passed the standard required-exception
union, FP control, value/special/merge, alias/guard and wrong-output controls.
This sampling is evidence for the stated host algorithm domain, not an
exhaustive correctly-rounded proof. The compensated sinh/cosh cases just over
0.5 ULP are retained in the histograms and were not relabeled as correct rounding.

Run the retained experiment with `check_accuracy.py --mpfr-million`. Only after
its success, `check_exports.py --accuracy <receipt>` checks exactly six new
unmasked source exports in `libknc_mvec/src/e_hyperbolic_export.c`. The software
mask entry points are also exercised with inactive signaling NaNs and infinity.
Target qualification remains zero.

That six-export wiring check passed in
`host-hyperbolic-exports/7c053dee887f45d3a4696fde87be05fd/wiring.json`.
Each off/fast build completed 384 public calls (4,608 lanes), 384 private masked
calls and 2,304 inactive poison lanes with zero bit/flag/full-MXCSR differences
from the assayed pointer implementation. Exactly the six expected public
symbols were defined, no scalar hyperbolic/exp fallback was imported, and
missing-export, fast-math and negative-control source builds were rejected.
