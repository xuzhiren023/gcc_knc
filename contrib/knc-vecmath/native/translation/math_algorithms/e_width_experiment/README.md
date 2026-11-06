# Private host e-width algorithm experiment

These fresh sources adapt the four preserved full-input Arm-based host
experiments to16 binary32 lanes (`expf`, `logf`) and8 binary64 lanes (`exp`,
`log`). `scripts/HostEWidthSources.py` authenticates the original source hashes
and describes the mechanical width, table-gather and uniform-initializer
changes. The originals are unchanged. Each core uses actual GCC vector
arithmetic. On the measured AVX2 host GCC decomposes the64-byte vectors (and
128-byte binary64 intermediates in the binary32 algorithms) into YMM operations.
The pointer interfaces avoid passing wide vectors through a host vector ABI.

This path defines private `phi_host_*` symbols only. It does not define `_ZGV`
exports, alter the canonical36-symbol scaffold, implement a GNU masked-vector
ABI or qualify KNC execution/G5. The observed e `N` exports are unmasked;
all-active arithmetic remains the principal algorithm path. Software masks are
an additional test contract, not an assertion about e-export mask semantics.

## Exact software-mask contract

Each call takes a full readable64-byte input buffer, a mask restricted to the
low16/8 bits, a full readable64-byte merge buffer and a writable64-byte output.
Inactive input encodings may be arbitrary, including signaling NaNs. Before
any kernel FP arithmetic, inactive lanes are replaced with0 for exponentials
and1 for logarithms. A zero mask copies merge bits without entering the core.
After arithmetic, inactive output bits exactly equal the merge buffer, without
interpreting its encodings as floating point. Invalid high mask bits return1
and leave output unchanged without FP effects. Other valid calls return0.

The implementation snapshots both source buffers before writing output. Exact
input/output aliasing and exact merge/output aliasing are tested separately.
Partial overlap is outside this interface. All64 bytes must be readable even
for inactive lanes; memory fault suppression is not provided or tested.

The declared state is nearest-even, all exceptions masked, FTZ/DAZ off. Active
lane special-value, NaN sign/payload, exact identity and standard exception
policies are inherited from the independent full-input oracles. The fenv flags
are the union of active lane obligations. Empty masks require zero FP status;
inactive signaling NaNs must neither be quieted in merge bits nor raise
invalid. The x86 denormal-operand status bit is allowed only when an active
input actually is subnormal. Errno, other rounding modes, unmasked traps and
target state/NaN behavior remain unqualified.

## Test and evidence entry points

Use bundled Python with `scripts/Check-HostEWidth.py`. Each attempt creates a
fresh private `artifacts/test-state/host-e-width/UUID/` folder, snapshots used
sources, records exact tools/dependencies/flags/commands and writes one
`experiment.json`. `--smoke` is a bounded development check and cannot represent
the full sample. Earlier failed attempts remain in place.

The full corpus uses one million fresh deterministic unsigned64 LCG draws per
operation (high32 bits for binary32), the authenticated directed tail from the
prior full-input corpus, every16SP/8DP mask pattern, random masks, narrow width
masks and explicit alias cases. Merge bits and inactive inputs are arbitrary
integer encodings. Both `-ffp-contract=off` and `fast` retain `-fno-fast-math`,
`-fmath-errno`, rounding/trapping/signaling-NaN semantics. Only the known
unmodified Arm data-file PE visibility warning is demoted; raw compiler logs
retain it. There is no scalar `exp*`/`log*` delegation.

`scripts/HostEWidthReference.py` independently evaluates active lanes using the
preserved100/160-digit Decimal intervals and exact integer IEEE rounding,
including exact rational tiny-input bounds. It enforces an exact rational
error upper bound of1ULP, exact specials/identities, merge bits and exception
unions. Random draws and dense edges are sampled evidence, not an exhaustive
proof over binary32/binary64 inputs. Unit tests include intentional2ULP,
identity-sign, merge, metadata and inactive-FP failures. Actual host controls reject
malformed input and unsupported states. A test-only unsafe variant deliberately
evaluates inactive poisonous inputs; the assessor must detect its FP effects
even when output bits are merged correctly. Crashes or incomplete outputs do
not count as a successful negative control.

Arm optimized-routines v26.01 commit
`649ccc8411e7c4862965710f25c570d854a1483f` supplies the algorithms/data/helpers.
The exact selected MIT notices, upstream files and locks are retained in the
four `native/upstream/arm-optimized-routines-v26.01*` subsets. No upstream file
is modified here. Actual KNC arithmetic templates, reserved-mask epochs,
register/call ABI, subnormal/special behavior, pipeline linkage and per-export
card conformance are still prerequisites to target use.

## Retained sampled result

The completed host attempt is
`artifacts/test-state/host-e-width/b595df3d71fb4a8cb8b0c7b82f9b746b/experiment.json`,
SHA256 `03681944dd7d66185a51343b85e6901af7c04b725e22e4c1225de63ae9cc4f25`,
status `HostEWidthSampleChecked`. It ran from 15:38:26 to 16:03:10 UTC on
2026-10-21 with Cygwin GCC14.4.0, actual AVX2/FMA support and no AVX512F. The
project's GCC14.3 Linux-target generator was not used.

| Function | Vectors per variant | Active lanes | Inactive lanes | Maximum ULP bound off / fast |
|---|---:|---:|---:|---:|
| expf16SP |147,633|1,791,084|571,044|0.501584174251554 / same|
| logf16SP |152,639|1,871,180|571,044|0.7753994128742986 / same|
| exp8DP |177,312|1,397,157|21,339|0.505430639581543 /0.5043706063521957|
| log8DP |175,870|1,385,603|21,357|0.510228845583582 / same|

Both variants have zero active-value, special, inactive-merge, standard
exception and empty-mask FP mismatches. Each SP function covers all 65,536 mask
patterns and each DP function all 256. There are 576 input/output and 576
merge/output exact-alias vectors per SP function, 320 of each per DP function.
Every buffer guard check passed. All 72 malformed/state execution controls,
the high-mask API controls and eight unsafe-inactive execution variants passed
their expected outcomes; the latter were detected through exception effects
while keeping inactive output bits intact. Seven focused unit tests passed.
No scalar math delegation, target export or source drift occurred. Assembly
contains YMM arithmetic and zero ZMM mentions; fast variants contain 20/20/18/42
FMA instructions for expf/logf/exp/log respectively (off variants contain 0).
The unmodified Arm exp/log data files retain their known Cygwin PE visibility
warnings. Two failed development attempts and the successful smoke attempt are
preserved separately. The earlier successful algorithms/reports are unchanged.

These are sampled host algorithm and software-mask results. Full input-domain
proof, errno, directed rounding, target vector calling convention, target
inactive-lane behavior and G5 remain open. No target exports or production
emission are enabled.
