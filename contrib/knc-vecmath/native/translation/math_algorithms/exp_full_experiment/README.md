# Full-input binary64 exp host experiment

This fresh experiment preserves every previous source/report. It admits all
binary64 encodings only under nearest-even, masked exceptions and FTZ/DAZ off.
There is no target `_ZGV` export, BIND/pipeline/card action or G5 qualification.

The algorithm is adapted from official Arm optimized-routines v26.01 commit
`649ccc8411e7c4862965710f25c570d854a1483f`, selecting MIT. The unchanged original
`math/exp.c`, `exp_data.c`, `math_config.h` and full license remain pinned in
the DP subset. A new isolated `arm-optimized-routines-v26.01-exp-special/`
subset pins exact `math/math_err.c` and the full license. No coefficients were
invented or fitted, and there is no scalar exp delegation.

The N128 table, split-ln2 reduction and degree-five polynomial retain the
official data. Tiny |x|<2^-54 lanes are removed before every core multiply and
use only1+x; inactive lanes of this expression are neutralized. This prevents
spurious underflow from intermediate operations on subnormal/tiny inputs when
the result is near1. Large positive results use the original1009 exponent
adjustment. Large negative results use the1022 adjustment and hi/lo correction
before scaling into the subnormal range; the original explicit underflow effect
is preserved through runtime volatile-factor arithmetic. Inactive scale lanes
are neutralized before multiplying to avoid discarded-lane exceptions.

| Input | Required result | Standard exceptions |
|---|---|---|
| either zero | exactly +1 | none |
| finite nonzero, normal result | sampled accuracy target <=1 ULP | inexact |
| nonzero tiny/subnormal input with result near1 | exactly nearest-even +1 | inexact, no underflow |
| finite with subnormal/rounded-zero result | sampled accuracy target <=1 ULP, positive zero | underflow and inexact |
| finite overflow | exactly +Inf | overflow and inexact |
| +Inf / -Inf | exactly +Inf / +0 | none |
| qNaN | preserve sign/payload and quiet bit | none |
| sNaN | preserve sign/payload, set quiet bit | invalid |

Per-vector standard flags must equal the union of lane obligations; no
divide-by-zero is allowed. The x86 denormal-operand status flag is recorded
separately and permitted only with a genuine nonzero subnormal input. NaN
payload rules and tininess-after-rounding are explicit host policies requiring
later target measurements. Errno, other rounding modes, unmasked traps,
exhaustive binary64 coverage and target ABI/mask/exception behavior remain open.

`HostExpFullReference.py` reads no kernel data or coefficients. Very tiny
inputs use exact rational bounds1+x <=exp(x)<=1+x+x^2, valid for |x|<1/2, with
a narrower independent cutoff2^-60. Both endpoints must round identically by
integer binary64 nearest-even conversion. Other finite active inputs use
Decimal.exp at100/160 digits; endpoint rounding must agree and intervals nest.
For |x|>2048, e>2 proves overflow or a result below the half-minsubnormal
threshold without overflowing Decimal. Special results are classified by bits.

The first actual private result is
`artifacts/test-state/host-exp-full/85ff40f7a26b4f99b48f5a3b28c57a8f/experiment.json`,
SHA256 `cc3869c8a61387c9c5f53ed1456fee000f4a5154c4fd8870efc9d154326f606d`.
Both `-fmath-errno` native AVX2 off/fast builds checked1,375,996 lanes, including
one million deterministic64-bit LCG draws. There are1,107,108 finite-result
comparisons and268,888 exact-special comparisons. Off has1,107,047 exact and61
one-step finite differences; fast has1,107,063 exact and45 one-step differences.
Conservative absolute error maxima are0.505430639581543 and0.5043706063521957 ULP.
These measured bounds satisfy the new <=1 ULP sampled target. The frozen
assay's inherited `checked4UlpAndSpecialPolicyPassed` field records its earlier
kit guard; it is not used to relax the new target or rewrite the receipt.

Each variant has zero special/value mismatches and zero exception mismatches
across343,999 vectors. The corpus includes66,268 subnormal inputs,507,851 tiny
normal inputs,85,095 subnormal results,264,837 finite rounded zeros,264,208
finite overflows and4,677 q/sNaNs. All12 actual malformed/state controls and
seven focused oracle/assay tests passed. Source/tool identities show no drift.
Off/fast kernel assemblies contain0/10 FMA instructions. Undefined-symbol
listings and assembly checks show no scalar exp/log fallback or `_ZGV` export.

The strict flags retain compiler errno semantics, rounding, trapping and
signaling-NaN support with no fast-math. `HAVE_FAST_FMA=0` retains the pinned
data configuration in both variants; contraction still produces actual FMA.
The unmodified upstream data's ELF hidden-visibility attribute is unsupported
by Cygwin PE. Its real warning is retained; only `-Wno-error=attributes` demotes
that diagnostic, with other enabled warnings treated as errors. No upstream
source or production build policy is altered.

Inputs use unsigned64 LCG recurrence with multiplier6364136223846793005,
increment1442695040888963407, seed`0x45585046554c4c`, taking each full updated
state. Directed cases cover dense tiny/subnormal input boundaries, all input
powers of two, result overflow/minnormal/minsubnormal/zero thresholds, sampled
table/reduction edges, q/sNaN payloads and214 isolated exception vectors.
Raw records are40 little-endian bytes/vector: four binary64 output words, a
u32 standard-exception mask and u32 full MXCSR. The data count fails closed.

Input SHA256 is
`32494f8c8778b466bbd80c7eeed0b6b82f55f305ddf5a2c2ebca0a27653fe96c`;
reference SHA256 is
`c4fa09563dd6e9c86af1eedd02063cb7540f1d48ae490f805c49fcbb40b4ca7c`.
The exact seven new component files are this README, `exp_full.c`,
`exp_full.h`, `host_driver.c`, plus `scripts/Check-HostExpFull.py`,
`scripts/HostExpFullReference.py`, `tests/test_host_exp_full.py`.
The ignored vendor whitelist is exactly
`native/upstream/arm-optimized-routines-v26.01-exp-special/` followed by
`.gitattributes`, `README.phiweather.md`, `LICENSE`, `math_err.c`,
`upstream.lock.json`. Never add the whole ignored upstream/toolchain tree.

```powershell
.tools\python\Scripts\python.exe -m unittest discover -s tests -p test_host_exp_full.py
.tools\python\Scripts\python.exe scripts/Check-HostExpFull.py --random-count 1000000
```
