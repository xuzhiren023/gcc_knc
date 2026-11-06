# Log10f/log10 source extension

Four observed names now have real sources: `_ZGVeN16v_log10f`,
`_ZGVbN4v_log10f`, `_ZGVeN8v_log10` and `_ZGVbN2v_log10`.
Their retained calls are20/2/100/1 (123 total). With the previous16
definitions,20 of36 names now have source definitions, covering2,384 of2,879
calls (82.81%);16 names remain declaration-only. Target-qualified count is0.
The original header/scaffold and earlier receipt-bound sources remain intact;
`log10-exports-v1.json` is additive and keeps every target/G5 flag false.

SP follows pinned Arm v26.01 log10f: the double reduction/polynomial is scaled
before its single final SP rounding, rather than scaling a rounded logf output.
DP follows the complete compensated official musl v1.2.5 Sun/FreeBSD log10
algorithm, including split constants and exponent correction. Both are genuine
GCC-vector adaptations with inactive x=1, arbitrary inactive bits, exact private
buffer aliases and no scalar log/log10 fallback. The official sources/licenses
and transformations are retained under `math_algorithms/log10_e/`.

Host evidence: strict Cygwin GCC14.4 baselineSSE2, noAVX/FMA, nearest-even,
masked exceptions and FTZ/DAZ off. Both contraction variants execute; raw outputs
agree, but these non-FMA builds do not establish FMA behavior.

| Actual fresh test | SP16 | DP8 |
|---|---:|---:|
| Distinct positive finite inputs |1,048,576|1,048,576|
| Total active inputs, each contraction |1,050,128|1,050,128|
| Finite ULP comparisons |1,048,587|1,048,587|
| NaN / infinity comparisons |1,538 /3|1,538 /3|
| Subnormal positive inputs |267,429|267,152|
| Maximum ULP bound |0.818855574549359|0.5155432490838623|
| Histogram≤0.5 |1,027,876|1,048,555|
| Histogram(0.5,0.75] |20,128|32|
| Histogram(0.75,1] |583|0|
| Above1ULP |0|0|

MPFR4.2.2 independently evaluates log10 down/up at256 and384 bits; every
endpoint agrees on final binary rounding. ULP units use spacing at the
correctly rounded binary reference, matching the existing project helper.
Completed wrong-result streams reject numerically. Screening separately checks
36 SP/20 DP masks, three alias modes, invalid-high-mask rejection, exact-identity
inactive poison, metadata, canaries and input preservation. The numeric oracle
checks invalid/divzero, forbids spurious overflow/underflow and checks full
MXCSR control bits; NaN payload identity, complete inexact behavior and errno
remain open. This deterministic sample is not exhaustive conformance.

Fresh source wiring completes256 calls/1,920 lanes per contraction through all
four separately compiled definitions, with zero bit/standard-flag/full-MXCSR
differences against the independently sampled pointer kernels. All four names
are defined, no scalar imports appear, and missing kernels/forbidden profiles
reject. This boundary equality is separate from MPFR accuracy.

Source-scoped records:

- Screening`artifacts/test-state/host-log10-e/06a76e01d49843928f774a5abad7a759/accuracy.json`.
- Large`artifacts/test-state/host-log10-e/6fed1f5b90324d948f1cb83d352a9069/accuracy.json`.
- Wiring`artifacts/test-state/host-log10-exports/c3627925a24343c9bfc979ace37513ae/wiring.json`.

Exact hashes are in the additive manifest. No card work or target compilation
occurred. G5 still requires the remaining16 real implementations, the qualified
pipeline/vector ABI/mask/FP runtime and actual target accuracy/special runs.
FMA, directed rounding and unmasked exceptions remain unqualified. DP's vector
division additionally depends on the later qualified division expansion. No
baseline tuning, BIND change, manual WRF assembly or unchanged corpus rerun ran.
