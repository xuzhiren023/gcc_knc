# Log10 e-width algorithms and four observed export sources

The retained inventory has22 SP log10f calls (20 e/2 b) and101 DP log10 calls
(100 e/1 b). Only these four observed signatures are defined; no d-width name
is invented. Added to the prior16 source definitions, this reaches20/36 names
and2,384/2,879 calls. Target-qualified count remains zero.

SP follows official Arm optimized-routines v26.01 `math/log10f.c`, commit
`649ccc8411e7c4862965710f25c570d854a1483f`. It reuses the established16-entry
logf range reduction/table and degree-four polynomial, retains DOUBLE
intermediates, multiplies that double result by inverse-ln10, then rounds once
to SP. It does not multiply an already-rounded SP logf result. The retained
`e_logf.c` special/mask machinery was copied to a new source, not edited.
No source comment's scalar ULP number substitutes for this adaptation's tests.

DP follows the complete compensated algorithm in official musl v1.2.5
`src/math/log10.c` (Sun/FreeBSD origin). It reduces to[sqrt(2)/2,sqrt(2)],
evaluates the published log1p polynomial and combines split log and
inverse-ln10/log10(2) constants with compensated exponent addition. It does
not scale an already-rounded DP log. The permissive Sun notice is preserved
in the adaptation and exact upstream source. Arm's pinned DP vector data was
inspected as source material but is not used. The pinned Arm tree has no
scalar DP log10.c; the rejected filename probe is recorded as HTTP404.

Both use GCC vector extensions (16SP/8DP) and private raw pointer interfaces.
Integer special classification precedes all arithmetic; inactive lanes become
x=1, yielding exact+0 without exceptions. Exact input/output and merge/output
aliases and arbitrary readable inactive bits are covered. Invalid high masks
return1 unchanged/zeroFP; partial-overlap behavior is unspecified. The new
production e adapters reuse the existing unmasked adapter contract; b4-SP and
b2-DP wrappers fill other wide lanes with1.

Host checks use Cygwin GCC14.4, strict baselineSSE2, noAVX/AVX2/FMA/AVX512,
nearest-even, masked exceptions, FTZ/DAZ off, separate contraction-off/fast
builds. They are non-FMA builds. MPFR4.2.2 down/up endpoints at256/384bits
must all agree on binary32/binary64 rounding. Each large corpus contains
1,048,576 distinct positive finite inputs spanning raw exponents, subnormals,
near-one and decimal-power boundaries, plus negative/special inputs. A sample
is not exhaustive conformance. Completed numerical mutants, exact merge,
record metadata, severe FP status and MXCSR controls fail closed.

```powershell
.tools/python/Scripts/python.exe -X utf8 native/translation/math_algorithms/log10_e/check_accuracy.py --mpfr-million
.tools/python/Scripts/python.exe -X utf8 native/translation/math_algorithms/log10_e/check_exports.py
```

Actual results and source-scoped artifact hashes are recorded additively in
`libknc_mvec/LOG10_SOURCE_STATUS.md` and `log10-exports-v1.json`. G5 stays open:
target pipeline/vector ABI/mask/FP runtime and target accuracy are unqualified.
Errno, FMA, directed rounding, unmasked exceptions and complete inexact status
remain open. No card job, runtime/BIND change or unchanged WRF corpus test ran.
