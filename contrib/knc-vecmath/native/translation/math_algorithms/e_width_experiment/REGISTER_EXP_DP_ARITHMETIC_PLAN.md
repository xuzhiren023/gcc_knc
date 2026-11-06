# Exact17 DP exp arithmetic prototype

This source-only step uses the root's one retained zero-gather emission
`677ed99fa8a54090815a91bf1b7fd086`, raw SHA256
`374ab37e8ca38bb9d584970ecdeeac1b9ab62febe72ad14f20cf25268a792010`.
The17 exact held DP sites are the10 FMA forms plus4 memory MUL and3 memory
ADD forms listed in `REGISTER_EXP_EMITTED_FORMS.json`. Existing translated
register ADD/MUL/SUB sites are outside this slice. The separate32 masked
VPERMD sites remain root-owned.

The single varying factor is staging each source memory operand as unchanged
bits into reserved ZMM31 before its original full-eight-lane DP operation.
Three register-only FMA forms need only their exact new register tuples.
Eight-byte readonly broadcasts use MOVQ into reserved R11, an8B store at
RSP-8 and VBROADCASTSD into ZMM31. Full64B stack operands use VMOVAPD into
ZMM31 only under the concrete GCC-aligned frame premise. The original AT&T
FMA132/213/231 order and binary64 fused single rounding are preserved.

The expected signature is agreement between literal recipe interpretation and
an independently decoded binary64 source equation for all6464 state bytes,
including exact ZMM31/R11/private-stack effects, masks, flags and FP status.
Metrics are exact form count, candidate/full-state mismatches, old sticky
status retention, four rounding modes and completed wrong-operation and
wrong-result signatures. Falsify on any unexpected changed byte, staged-word
mutation, FMA order/rounding discrepancy or accepted outside-domain source.
Bound one source prototype and64 synthetic epochs per each17 literal form,
using existing exact rational binary64 lane references, then stop. No host FP
instruction, assembler, compiler, card or old numerical corpus is executed.

The source reference imports no candidate/parser/target interpreter. It reads
the original operand from the captured operand page using its explicit actual
address, combines binary64 ADD/MUL/FMA lane equations and predicts scratch
effects separately. Literal recipe interpretation is a development model,
not KNC execution or a new ISA correctness proof. Both use the already
independently calibrated rational lane helpers rather than Python/host floats;
new memory/tuple/physical-state qualification remains mandatory.

The6464 development state retains the existing observer layout:2240 bytes of
architecture,4096-byte operand page and128 bytes of private RSP scratch. The
operand page and private scratch must be disjoint; source RSP and standing
K5/K6/K7 must match their explicit values. These are fixture premises, not an
automatic source/ELF alignment proof. Native admission must bind actual
addresses, code, readonly scalar8B spans and GCC-aligned positive stack slots,
and measure the complete source-expanded state. No general alignment engine,
native runner, gate receipt, automatic registration or verified flag is added.
