# Gather-free DP8 exp source plan

This additive source step prepares `_ZGVeN8v_exp` after the separately owned
first expf target run. It authorizes no compiler execution, image linkage,
card contact, receipt modification or change to the frozen expf pipeline.
The existing exp/logf/log algorithms, adapters and evidence remain unchanged.

The varying factor is only selection of the existing Arm N128 exp table.
Replace its two input-indexed uint64 loads with sixteen fixed eight-entry
shards for each of tail and scale. Each shard is one static, 64-byte-aligned
vector of sixteen uint32 halves. A paired `{2*j,2*j+1}` dword selector copies
both halves of the selected uint64 without FP conversion; duplicated dword
group masks combine exactly one shard in each lane. There are 32 explicit
source shuffles and 2,048 table bytes. The N128 range reduction, degree-five
polynomial, coefficients, FP expression order, tiny-input treatment,
compensated large/subnormal paths, specials and software-mask logic stay
identical. No new approximation or scalar exp call is introduced.

The expected source signature is exact reconstruction of all 256 upstream
uint64 words, 32 fixed named shuffles, no data-indexed table access and no
arithmetic change outside the table-selection replacement. Source metrics
are the word/lane comparison counts, exact source-difference scope and the
number/size/alignment of fixed constants. The source falsifier is any bit
mismatch, changed arithmetic/special path, mutable upstream file, dynamic
table subscript or missed corruption control. The bounded effort is one new
source implementation and one source-only exhaustive selection check; stop
at the first failure and preserve its output. This source check executes no
FP algorithm and supplies no ULP, compiler, native or G5 result.

Before a later new-source experiment, retain this same single varying factor.
One Linux-target GCC14.3 assembly emission may measure gathers, unknown and
unverified exact forms, aligned fixed loads, shuffle lowering, spill/stack
accesses and scalar imports. Stop if a gather survives, an indexed table load
returns, a source prerequisite drifts or the actual instruction census is
incomplete. The emitted instruction domain must be frozen from those actual
bytes; no source spelling or expf receipt licenses a new register tuple.
No such emission is performed by this source step.

The retained e-width host result is
`artifacts/test-state/host-e-width/b595df3d71fb4a8cb8b0c7b82f9b746b/experiment.json`
(SHA256 `03681944dd7d66185a51343b85e6901af7c04b725e22e4c1225de63ae9cc4f25`).
Its exp8DP variants checked 1,397,157 active lanes and 21,339 inactive lanes,
with maximum sampled bounds 0.505430639581543 ULP off and
0.5043706063521957 ULP fast. This is motivation for retaining the arithmetic,
not accuracy evidence for the new source. A future new-source numerical
assay must enforce <=1 ULP with independent intervals, exact specials,
exception unions, tiny/subnormal boundaries and inactive-lane controls.
Do not replay the unchanged old algorithms. Cygwin AVX2 shuffle-spill alignment
has already failed for expf; a future host diagnostic must use its independently
declared working ISA/stack profile and cannot qualify Linux/KNC ABI or FMA.

The Arm source is optimized-routines v26.01 commit
`649ccc8411e7c4862965710f25c570d854a1483f`, MIT selection. The immutable DP
subset's `exp_data.c`, `math_config.h`, lock and full license remain inputs.
The existing exp adapter still selects the historical source. The new
`e_exp_register_export.c` is an alternative translation unit and must not be
linked together with that adapter, since both define `_ZGVeN8v_exp`.

Still required before target admission:

- Actual new Linux-target emission and a complete exact-form census, including
  both halves of every DP arithmetic/FMA operation, qword shifts, dword
  comparison/mask selection, VPERMD operand order, loads/stores, spills and
  scalar/control-flow/exception paths. No missing tuple is guessed before
  emission. Current expf exact56 registration is parent-source-bound and
  rejects this source; the preliminary generic permutation source is not a
  registered native-qualified rule.
- Probe plus independent physical-state target qualification for every newly
  emitted form. K5/K6/K7=1/15/255, reserved R11/ZMM29-31, upper-zero behavior,
  scratch effects and live EFLAGS/masks must obey D1/D2/D3 at every boundary.
  Typed DP arithmetic must use the KNC FP state rather than generic MXCSR.
- An authenticated new source contract binding all 32 table spans and any
  generated selector constants to actual readonly aligned bytes, then automatic
  translation with zero unknown/unverified forms and zero gathers, actual
  EM_K1OM assembly/linkage and full object/image disassembly bindings.
- The actual `_ZGVeN8v_exp` full-width argument/return boundary, nested pointer
  calls, stack alignment, preserved integer/vector state and D2 mask constants.
  The expf argument/result type is SP16; it does not establish this DP8 export.
- Independent new-source host accuracy followed by card per-export conformance
  over at least one million inputs, directed specials and ULP histogram under
  the owner's <=1 ULP target. Nearest-even, masked exceptions and FTZ/DAZ off
  remain the declared domain; errno, directed rounding and traps remain open.

`logf` has two 16-entry binary64 fields but includes division-based exceptional
paths. DP `log` has four 128-entry fields and compensated near-one arithmetic,
also with division-based exceptional paths. Preserve both unchanged while this
smaller exp change establishes its actual emitted prerequisites. No performance
gain is claimed for the 32-shuffle lookup.
