# B.7 final DP-exp vectorizer screen — stop rule fired

Tried: one additional `-fno-tree-vectorize` flag from the ORIGINAL DP-exp
baseline OPT argv, with unchanged22 D3BIND flags and canonical source. Neither
prior SLP-off nor loop-off screen flag was stacked. The plan and exact argv/
source/tool closure were frozen before execution.

Oracle: compiler PID70316 exited0 in0.687seconds under OwnedJob; owned active
processes after cleanup0. Source/tool identities and the actual C dependency
closure matched. There was exactly one compiler invocation, with no retry.

The falsifier fired: one whole-register byte shift remains at new assembly
line1717, `vpsrldq $8, %xmm1, %xmm2`. Gathers remain0. Full assembly changed
from374ab37e/37232bytes/1084 lexical instructions to420db999/44188bytes/1481.
The explicit `pw_core_exp` vector core remains present, but its assembly bytes
changed:24344→30160 bytes, ZMM instruction lines177→242, ZMM references323→475.
Neither the whole parent nor the core-function byte sequence is identical.

Sole result:
`artifacts/test-state/exp-vectorize-off-final-screen/exp-e02e19a60d264381aceb8eaf9c0facd5/result.json`,
SHA256 `d9a6630edd8cbb410ad3d75a3945db7bd78b4e6a2cb1440b210f024930cf1f92`.
Status is `FalsifiedByteFormsPersistStopAllDpExpFlagWork`. The directory retains
the before-execution plan, new assembly, actual dependency file, source
snapshots and compiler stdout/stderr.

What remains: ALL DP-exp flag work is stopped under the declared bound. No
new parent is selected, exact-site proof transferred, translator report
generated, source-binding migration attempted, target object linked or card
job run. Original scientific receipts and all three screen attempts remain
separate. Source-screen failure changes no registered/verified count; last
confirmed inventory46registered/45verified and G5 remains1/36.

Single next action: root records the measured failure and decides the permitted
DP-exp path while independent generic extraction/runtime work continues.
