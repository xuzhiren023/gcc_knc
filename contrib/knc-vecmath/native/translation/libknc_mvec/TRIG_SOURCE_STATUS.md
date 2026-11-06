# Sine and cosine source exports

Five observed names now have real source definitions: DP sin e8 (78 calls),
DP cos e8/b2 (110/1), SP sinf e16 (67), and SP cosf e16 (69). These325 retained
calls bring additive source coverage to25/36 names and2,709/2,879 calls
(94.10%).11 names/170 calls remain declaration-only. Target-qualified count
remains zero; every target ABI/numerical/mask/production/G5 flag is false.
The historical scaffold, header, earlier manifests and measured sources remain
unchanged. The additive manifest is `trig-exports-v1.json`.

`src/e_cos_sin_export.c` macro-renames the four pointer kernels and includes
the unchanged `math_algorithms/cos_sin_e/cos_sin_e.c` once. The same64-byte
unmasked adapter copies raw bits and supplies the full software mask.
`src/cos_sin_reducer.c` includes the shared reducer once; its exact official
musl v1.2.5 bodies provide complete small/medium/Payne–Hanek reduction plus
private internal floor/scalbn. `src/cos_wrappers.c` adds only b2 DP cosine,
filling the other six wide lanes with exact zero. Compile those three source
files with `include/` and `math_algorithms/cos_sin_e/` on the include path.
There is no scalar trig delegation or imported floor/scalbn helper.

The four algorithm implementations already passed a bounded screen and a fresh large
MPFR4.2.2 assay before integration. Neither was rerun for source wiring.
The large assay has1,049,230 SP and1,052,806 DP finite comparisons per operation
and contraction variant; maximum ULP bounds are sinf0.4999989419321134,
cosf0.49999960186250003, sin0.7705709129503738 and cos0.745124648867273.
All256/384-bit directed endpoints agree on rounding; none exceeds1ULP.
These are broad sampled host results, not exhaustive or target bounds.

The fresh wiring result is
`artifacts/test-state/host-trig-exports/785b3790347d476fa90ec39aba023191/wiring.json`.
Both strict baselineSSE2 contraction variants pass320 calls/3,200 lanes,
384 inactive sNaN poison lanes, exact output/standard-flag/full-MXCSR equality
against the sampled pointer kernels, and signed-zero cosine identities.
It defines exactly the five names above and imports no scalar math fallback.
Missing e-kernels, missing complete reducer and forbidden fast-math/research
profiles are explicitly rejected. The result authenticates the unchanged
large-assay source bytes; it does not repeat their numerical experiment.

The two algorithm receipts and this wiring receipt, with exact source-scoped
hashes, are recorded in `trig-exports-v1.json`. Complete inexact/underflow/errno,
NaN payload propagation, directed rounding, FMA and unmasked exceptions remain
open. The concrete G5 blockers are qualified translation forms/vector widths,
measured target vector ABI/masks, generic target FP runtime and actual target
accuracy. No KNC library, target run, performance result or gate pass is claimed.

The remaining source work is:

| Observed name | Calls | Mathematical work |
|---|---:|---|
| `_ZGVeN16v_tanf` |19|Full-domain tangent, using retained reduction with pole-safe kernel.|
| `_ZGVeN8v_tan` |15|DP tangent, with compensated reduced tail and reciprocal branches.|
| `_ZGVeN16v_atanf` |6|Argument-region reduction and compensated arctangent polynomial.|
| `_ZGVeN16vv_atan2f` |22|Quadrants, signed zeros/infinities and ratio scaling plus atan.|
| `_ZGVeN8vv_atan2` |15|DP quadrant/ratio-safe atan2.|
| `_ZGVeN16v_sinhf` |15|Small-argument cancellation and signed overflow-safe hyperbolic sine.|
| `_ZGVeN8v_sinh` |15|DP sinh with compensated exp/expm1 boundaries.|
| `_ZGVeN16v_coshf` |15|Overflow-safe positive hyperbolic cosine.|
| `_ZGVeN8v_cosh` |15|DP cosh including the exp-square overflow boundary.|
| `_ZGVeN16v_tanhf` |18|Small-argument cancellation and saturation-safe hyperbolic tangent.|
| `_ZGVeN8v_tanh` |15|DP tanh with compensated expm1 and exact signed zero.|

The direct next source family is tangent, reusing the complete reducer while
adding its own pinned polynomial/pole handling and fresh independent assay;
then the atan/atan2 family and hyperbolics. Each needs actual algorithms and
its own measured source evidence; existing exp/log and trig results do not
qualify these remaining names.
