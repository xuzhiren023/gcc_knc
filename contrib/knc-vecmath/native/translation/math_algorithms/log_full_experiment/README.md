# Full-input binary64 log host experiment

This fresh source keeps all previous source/report inventories unchanged.
It admits every binary64 encoding under nearest-even, masked exceptions,
MXCSR FTZ=DAZ=0. The active sampled numerical bound is **<=1 ULP**, enforced
directly using exact Fraction comparisons by `Check-HostLogFull.py`; there is
no four-ULP acceptance path. Eight focused controls include an actual assay
case that rejects a two-ULP error that would fit the older four-ULP bar.
No target `_ZGV` symbol, BIND/pipeline change, card action or G5 claim follows.

The algorithm uses official Arm optimized-routines v26.01 commit
`649ccc8411e7c4862965710f25c570d854a1483f`, selecting MIT with full retained
license. Unmodified `log.c`, `log_data.c` and `math_config.h` are pinned in the
existing DP subset. The already pinned DP `math_err.c` supplement supplies
pole and invalid helper arithmetic. No new vendor files or fitted constants
are required. No scalar log/exp function supplies results.

Positive subnormals normalize exactly by 2^52 with the original unsigned
exponent adjustment. Near-one inputs use the official compensated degree12
polynomial; other positive inputs use the N128 split-c table reduction and
degree6 polynomial with the exact data. Both contraction variants use
`HAVE_FAST_FMA=0` data configuration, while fast contraction may emit actual
FMA arithmetic. The near-one and general computations have separate safe
inactive lanes. In particular, the general table path is skipped entirely
when no real far input exists, preventing discarded inexact work for log(1)
or quiet-NaN-only vectors. When needed, inactive table lanes copy a real far
input whose mathematical inexact flag is already required.

| Input | Required result | Standard exceptions |
|---|---|---|
| exactly 1 | exactly +0, including sign | none |
| other positive finite, including subnormals | <=1 ULP | inexact |
| either zero sign | exactly -Inf | divide-by-zero |
| negative finite / -Inf | canonical host negative qNaN `fff8000000000000` | invalid |
| +Inf | exactly +Inf | none |
| qNaN | preserve sign/payload/quiet bit | none |
| sNaN | preserve sign/payload, set quiet bit | invalid |

Standard vector flags must equal the union of lane obligations. No positive
finite logarithm can overflow or underflow for binary64 inputs; unexpected
flags fail the assessment. The x86 denormal-operand flag is separately recorded
and permitted only with a nonzero subnormal input. Canonical/propagated NaN
bits are an explicit x86-host policy requiring later target measurement.
Runtime helper arithmetic uses safe inactive denominators, not scalar libm.
Errno, other rounding modes, unmasked traps, exhaustive coverage and target
ABI/mask/exception behavior remain open. Compiler flags retain `-fmath-errno`,
strict rounding/trapping/signaling behavior and no fast-math. The original
data object's unsupported ELF visibility annotation may produce a retained
Cygwin PE attribute warning; only that warning is demoted from error.

The independent oracle decodes bits exactly, computes Decimal.ln intervals
at 100/160 digits and rounds rational endpoints to binary64 using integers.
Both endpoint roundings must agree and precision intervals nest. Special
results and log(1) are classified independently of implementation tables.
The nearest non-one binary64 inputs differ from 1 by at least 2^-53; their
nonzero logarithms are normal results, so no near-zero transcendental-result
underflow workaround is needed. An incorrect log(1) negative-zero sign fails
even if its numerical error would be zero.

The planned corpus contains one million unsigned64 LCG updated-state words,
seed`0x4c4f4746554c4c`, multiplier6364136223846793005 and
increment1442695040888963407. Directed cases cover dense near-one values,
near-one branch edges, smallest subnormals, the subnormal/normal boundary,
largest finite inputs, powers of two, selected-exponent table boundaries,
negative domains and q/sNaN payloads. Neutral-one isolated vectors expose
missing/spurious flags, including quiet NaNs and log(1). Input bits/order and
the reference/results are retained in each fresh attempt.

Raw records are40 little-endian bytes/vector: four result u64 values, a
standard-exception u32 mask and full MXCSR u32. The recorder clears standard
and denormal-operand flags before each call. Actual host AVX2/compiler/tool/
DLL/Python identities, all flags/warnings/undefineds, assembly, command logs,
malformed/state rejection controls and exact source snapshots are retained.
Failed attempts stay in `artifacts/test-state/host-log-full/`; there is one
private result per attempt and no public gate creation.

```powershell
.tools\python\Scripts\python.exe -m unittest discover -s tests -p test_host_log_full.py
.tools\python\Scripts\python.exe scripts/Check-HostLogFull.py --random-count 1000000
```

The actual private result is
`artifacts/test-state/host-log-full/5abad2fefd2c464b9a6f9990e987c89e/experiment.json`,
SHA256 `ae4efb5931507013d14d2326ca0b7b31ea9ed0261fbe7b70b7c4c27e745454df`.
Both strict off/fast variants checked 1,364,460 lanes (1,363,855 unique inputs).
Their finite-result histograms have 859,798 exact matches and 102 one-step
differences. The maximum conservative absolute error is0.510228845583582 ULP,
below the actively enforced 1-ULP limit. All 504,560 special comparisons and
341,115 vector exception checks per variant match. The corpus includes85,892
positive subnormals, 499,877 negative finite values, 2,318 qNaNs, 2,356 sNaNs and
456 exact log(1) cases. No value, special or exception mismatch occurred.

Off/fast assemblies contain 0/21 FMA instructions; undefined-symbol and assembly
checks show no scalar log/exp fallback or `_ZGV` export. The one expected
unsupported-visibility warning from unchanged official log_data.c is retained.
All 12 actual malformed/state controls and eight focused tests passed, and
source/tool identities show no drift. The actual input SHA256 is
`89adb2fd4d25e18081bc94275bda7c33f104ffcabf7b6b5c5d5584ed15199a25`;
independent reference SHA256 is
`462b3494e6b14200813d3f27c5f88a5043ca2e581eca1cd231d8fd6dc8fcfbce`.
The declared sampled-domain and target/errno/directed-rounding limits stand.

Exact seven new files: this README, `log_full.c`, `log_full.h`, `host_driver.c`,
plus `scripts/Check-HostLogFull.py`, `scripts/HostLogFullReference.py`,
`tests/test_host_log_full.py`. Existing vendor/license subsets are reused
unchanged; no new ignored upstream files are added for this algorithm.
