# Complete source coverage; host policy checked, NaN payload unqualified

All 36 observed GNU vector symbols now have source definitions: 23 full-width
e symbols and 13 b/d wrappers covering the unchanged 2,879 census calls.
`complete-source-coverage-v1.json` binds the exact names, source paths, call
counts, prior source inputs and current integration evidence. Target-qualified
count remains 0; G5 and production readiness remain open.

The new explicitly labeled aggregate comparison completed all 36 exports after
the strict historical failure described below. Every finite, subnormal,
signed-zero and infinity output remains bit-exact. NaNs must be quiet NaNs;
standard exception flags, full MXCSR and input preservation remain exact.
NaN payload/sign differences against a separately compiled algorithm are
reported as `UNQUALIFIEDPAYLOAD`, consistent with the existing atan contract.
This is not a full-byte-equality pass against that separate reference.

The complete result is
`artifacts/test-state/host-mvec-complete-policy/c3b55c81c60540a08fd454ae5d62b456/integration.json`:

| Check | Result |
| --- | ---: |
| Public exports / calls | 36 /1,152 |
| Output lanes per comparison relation | 10,752 |
| Separate reference calls / actual library pointer calls | 1,152 /1,152 |
| Bit-exact non-NaN lanes per relation | 8,894 |
| Quiet-NaN lanes per relation | 1,858 |
| Separate-reference NaN payload/sign differences | 1, explicitly unqualified |
| Actual library pointer versus public export differences | 0, including every NaN bit |
| Non-NaN bit / flag / full-MXCSR / input mismatches | 0 |

The public export and its actual library pointer matched every output bit on
all 10,752 observed lanes. A completed one-bit non-NaN wrong-result control
rejected. Exactly all 36 expected definitions remain in the new executable,
with no duplicate, unresolved library definition or scalar math import.
The completed archive, reference objects and all scientific source bytes were
reused unchanged; only this new test driver was compiled and linked. No million
accuracy rerun, source approximation change, ULP threshold change or card work
was performed.

One new complete-library host integration built all production translation units
and the five pinned data objects into `libknc_mvec-host.a`. The archive and final
executable both contain every expected `_ZGV` symbol exactly once. Linking
succeeded with no unresolved library definition or imported scalar math fallback.
Unchanged assayed pointer algorithms were separately compiled for the compact
wiring reference. The profile was strict baseline SSE2, contraction-off,
nearest-even/masked exceptions and FTZ/DAZ off. No accuracy corpus was rerun.

The initial build stopped before any object was produced: the shared musl
reducer's included floor source needed its established `cos_sin_e` include
directory. Attempt `3466c6cea37646189b791fcd3ad08138` retains the original tool
source snapshot and compiler diagnostic. A fresh attempt added that include
directory only; no assayed numerical or export source changed. All warnings
remain recorded, including the preexisting Cygwin visibility-attribute warnings.

The strict attempt `0eb5c8ee95b14c5c8f7b733571960abf` compiled and linked, then
stopped at `_ZGVeN16vv_atan2f`, batch8. The bounded diagnosis established:

| Value | Bits |
| --- | --- |
| Input y | 0x7f800001 (signaling NaN) |
| Input x | 0xffc00023 (negative quiet NaN) |
| Separately compiled original pointer result | 0xffc00023 |
| Actual library pointer result | 0x7fc00001 |
| Public export result | 0x7fc00001 |

All three executions reported standard exception flags33 and full MXCSR0x1fa3.
All other 15 SP lanes in that packet matched bitwise; its finite, infinity and
signed-zero outputs showed no mismatch. The equivalent DP dual-NaN pair matched
in all three routes. The public export therefore matches its actual library
pointer for the failing case. The source uses `va+vb` for NaNs; the separate and
included compilations select different input NaN payloads. The existing atan
README explicitly leaves NaN payload identity open. The strict comparison and
its stopped receipt remain unchanged; the subsequent policy comparison is a
new source and record with the explicit distinction stated above.

The diagnosis source, reused objects, command, exact outputs and flags are in
`artifacts/test-state/host-mvec-library-diagnosis/atan2-nan-priority-20261022/`.
The stopped strict aggregate run remains intact. NaN payload/sign identity
remains unqualified; future target qualification must state its actual policy.
Target ISA/ABI/mask, independent target numerical and runtime/IP-1 obligations
remain unchanged. Source coverage and host integration are not G5.
