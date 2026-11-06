# Exact signed dword-to-qword extension source slice

This Windows-only source slice consumes only the retained first DP exp assembly
SHA256 `374ab37e8ca38bb9d584970ecdeeac1b9ab62febe72ad14f20cf25268a792010`
and its existing unsupported-form inventory. Its20 VPMOVSXDQ occurrences are
all XMM-to-YMM, with18 distinct register pairs and no source/destination alias.
YMM-to-ZMM and alias pairs are outside the candidate and are rejection controls
only. No extra positive width/alias domain is implemented.

The single varying factor is replacing each exact signed widening instruction
with fixed static-data selection and DWORD bit operations. Load a64B selector
`{0,0,1,1,...,7,7}` into ZMM30 and permute source DWORDs into ZMM31. Arithmetic
DWORD shift31 produces sign words in ZMM29. A64B `{0xffffffff,0,...}` constant
keeps original low halves, while ANDNOT keeps sign words in high halves. OR
combines the widened pairs. Clear the original destination, then copy only
its low8 DWORDs under standing K7=255. This preserves signed widening of the
original low4 DWORDs and zeros destination bits256..511.

Expected signature: exact signed uint64 bit patterns in all4 destination
qwords, upper256 zero, and agreement across every6464 state byte with a source
equation independent of the candidate/interpreter. Only ZMM29-31 are scratch;
their final contents are predicted explicitly from the original register
snapshot. No GPR, mask, flags, VCSR/MXCSR, page or private-stack byte changes.
Both aligned readonly64B constants must be bound as complete static objects
before any later native use. This supplies no generic alignment proof.

Metrics are20 retained line anchors,18 exact candidate literals,5120 bounded
cases per variant (256 epochs per retained site), candidate full-state mismatch
count, completed zero-extension/wrong-width mismatch signatures, upper-source
poison independence, four RC fields,64 prior sticky images and exact scratch
fingerprints. Inputs include sign boundaries, zero, allones, walking bits and
deterministic raw encodings. Falsify on any changed signed bit, nonzero upper
destination bit, incorrect scratch value, altered unmentioned state, admitted
outside-domain source or ineffective negative program. Bound one new source
implementation plus these new controls; stop at first failure and retain it.

No source in the existing49-form native batch, old tests, receipts, compiler
or card is touched or executed. The expf zero-extension/permutation structure
is prior source material only; its native receipt does not qualify signed
widening, these constants, registers or this parent assembly. Production
access always rejects and verified/native flags remain false. A future actual
syntax probe and independent full-state native qualification of these exact
forms and constants remain required. Counts stay39 registered/38 verified and
G5 stays1/36 during this source step.
