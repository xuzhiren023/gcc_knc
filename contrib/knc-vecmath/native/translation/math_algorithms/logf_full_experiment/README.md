# Full-input logf host experiment

This separate source extends the earlier positive-normal logf experiment to
all binary32 encodings. The five preceding successful algorithm source/report
inventories, including full-input expf, remain unchanged. Neither this private
function nor any host result defines a target `_ZGV` symbol, changes BIND or
the pipeline, or qualifies G5/card execution.

The algorithm and coefficients are adapted from official Arm optimized-routines
v26.01, commit `649ccc8411e7c4862965710f25c570d854a1483f`, selecting MIT from its
dual license. The original `math/logf.c`, `logf_data.c`, `math_config.h` and full
license remain pinned in `native/upstream/arm-optimized-routines-v26.01/`.
The already pinned `arm-optimized-routines-v26.01-expf-special/math_errf.c`
also contains the exact log pole/invalid helper arithmetic; its historical
directory name does not limit those retained upstream functions. No new
download or alteration of either lock is needed.

Positive subnormals are normalized exactly by multiplying by 2^23, then applying
the upstream unsigned exponent adjustment. Other lanes in this operation are
neutralized so normalization cannot overflow. The N16 reciprocal/log table,
ln2 constant and degree-four double-vector polynomial retain exact upstream
values. Exceptional lanes become 1 before the core. The error paths perform
the original `(x-x)/(x-x)` and barrier(-1)/0 arithmetic with safe inactive
denominators. They do not call scalar logf or replace bad lanes with a fallback.

The explicit experimental obligations are:

| Input | Required result | Standard exception flags |
|---|---|---|
| exactly 1 | exactly +0, including sign | none |
| positive finite other than 1, including subnormals | within 4 ULP | inexact |
| either zero sign | exactly -Inf | divide-by-zero |
| negative finite | host canonical negative qNaN `ffc00000` | invalid |
| -Inf | host canonical negative qNaN `ffc00000` | invalid |
| +Inf | exactly +Inf | none |
| qNaN | preserve sign/payload and quiet bit | none |
| sNaN | preserve sign/payload, set quiet bit | invalid |

The canonical invalid NaN and propagation rules are measured x86-host policy;
they are not assumed on KNC. Positive finite results cannot underflow/overflow
for binary32 inputs; divide-by-zero and invalid are allowed only as listed.
Inexact is required for positive finite inputs other than 1, whose natural log
is nonzero and transcendental. Vector flags must exactly equal the union of
lane obligations. The x86 denormal-operand status bit is separately recorded
and allowed only with an actual nonzero subnormal input.

The caller/recorder requires nearest-even, all exceptions masked and MXCSR
FTZ=DAZ=0. Upward rounding, FTZ and DAZ negative controls must reject without
output. Compiler options keep `-fmath-errno`, `-fno-fast-math`, rounding,
trapping and signaling-NaN semantics, with off/fast contraction variants.
This does not implement errno. Other rounding modes, unmasked traps, errno,
target exception/NaN/mask/ABI behavior and exhaustive input coverage remain
open. No exception-policy relaxation is applied after observing a failure.

`HostLogfFullReference.py` uses exact input bits, the preserved Decimal.ln
interval oracle at 100/160 digits and integer binary32 nearest-even rounding.
Both precision intervals must round identically and nest; no binary64
transcendental or host libm supplies reference values. Exact specials and
log(1) are classified independently of the implementation table/coefficient
source. An incorrect log(1) negative-zero sign fails even when numeric ULP
error would be zero.

One million raw inputs come from the unsigned 64-bit recurrence
`state=(state*6364136223846793005+1442695040888963407) mod2^64`, seed
`0x4c4f4746554c4c`, taking the high 32 bits after each update. Fixed recurrence
vectors are a focused test. Directed inputs include every binary32 encoding
within 65,536 steps of 1, dense smallest-subnormal/normal-boundary/largest-finite
neighborhoods, normal table-cell edges and signed q/sNaN payloads. Isolated
vectors use neutral 1 neighbors to expose missing/spurious flags; mixed vectors
also check flag unions. A separately recorded seeded permutation changes only
directed lane adjacency, not the million LCG inputs.

Each raw output record is six little-endian u32 words: four lane results,
`fetestexcept(FE_ALL_EXCEPT)` and full MXCSR. Both standard flags and the
denormal-operand bit are cleared before every call. Actual AVX2 capability,
compiler/tool/DLL/Python/reference identities, flags, assembly, undefined
symbols, warnings, command logs, inputs, outputs and source snapshots are
retained in a fresh private attempt. Source tests and host evidence do not
qualify an instruction template or target ABI.

```powershell
.tools\python\Scripts\python.exe -m unittest discover -s tests -p test_host_logf_full.py
.tools\python\Scripts\python.exe scripts/Check-HostLogfFull.py --random-count 1000000
```

Eight focused controls cover policy classification, smallest subnormals,
positive/negative output assay, exact-zero sign, NaN payloads, exception
unions/state drift, malformed comparisons, independent table/source pins,
fixed LCG words and strict compiler flags. Their synthetic records are not
native numerical evidence. Actual attempt results live under
`artifacts/test-state/host-logf-full/`, with failed attempts preserved.

The first actual result is
`artifacts/test-state/host-logf-full/8c5e4d8d78264c69a6dc8173461bc926/experiment.json`,
SHA256 `211f7b557b84b6582fce2b4274e885f39f8f6cb5e0ac565ea1fa42f6feacd95f`.
Both off/fast `-fmath-errno` builds checked 1,300,452 lanes (1,299,669 unique
inputs). Their finite-result histograms have 790,359 exact matches and 3,162
one-step differences; maximum conservative absolute error is
0.7551645736009517 ULP. All 506,931 special-value comparisons and 325,113 vector
exception checks per variant match exactly. Actual assemblies have 0/5 FMA
instructions. Compile warning logs are empty, and undefined-symbol listings
have no scalar exp/log import or target `_ZGV` export.

The corpus includes 87,371 positive subnormal inputs, 498,932 negative finite
inputs, 4,013 qNaNs, 3,977 sNaNs and 453 exact log(1) cases. All 12 actual
malformed-input/unsupported-state controls rejected without output. Source/tool
identities have no drift during the attempt. The raw input SHA256 is
`6647171ce8afe364a311cc20ddf0e77ba6300935280f2e129714d27d4fccf9f4`;
independent reference SHA256 is
`8376f2db023799d6947025ffc1246e757f382a075ebb2a6e642e0ba153a48dd9`.
This sampled host result does not establish exhaustive coverage, errno,
directed rounding, unmasked traps, target behavior or G5.

The exact seven new source/test/document paths are this README,
`logf_full.c`, `logf_full.h`, `host_driver.c` in this directory, plus
`scripts/Check-HostLogfFull.py`, `scripts/HostLogfFullReference.py` and
`tests/test_host_logf_full.py`. Existing pinned vendor/license subsets are
reused without alteration; there is no new ignored vendor tree to add.
