# S5-16 implementation and outstanding results

Acceptance is **not met**. The implementation builds, but the signed-word-to-float
scan and two torture cases fail. The lead's whole-zmm spill requirement also
needs clarification. No program was run on the card.

The implementation adds a separate V16QI/V16HI transport predicate, the related
mode hook, preferred QI/HI modes, ABI rejection, exact-size transport, converting
loads, combined integer-to-float loads, and AND plus unsigned saturating stores.
Byte arithmetic, comparisons and movmisalign remain disabled.

Transport instruction references checked in Intel 327364-001:

- pp.136-137: `vbroadcasti32x4` reads 16 bytes without conversion.
- pp.138-139: `vbroadcasti64x4` reads 32 bytes without conversion.
- pp.426-428: `vpackstorelq` packs selected qwords into the low line. Masks 3
  and 15 write 16 and 32 bytes. Natural alignment keeps the value in that line.
- pp.32-34 and 379-384: memory conversion alignment and VMOVAPS/VMOVDQA32 forms.

## Spill question

Register moves copy the full zmm. Ordinary pseudo spills currently use the
exact-size transport operations, preserving all sixteen value lanes.
This does **not** implement the lead's requirement that spills copy the whole zmm.

The reduced allocator case is a `reg:V16HI` pseudo with no wider subregister
references. `gcc/lra-spills.cc:132-158` derives its slot from the pseudo mode and
`biggest_mode`, producing a 32-byte slot; V16QI similarly uses 16 bytes. A 64-byte
store cannot safely replace that transfer. May ordinary pseudo spills use the
exact-size transfers, reserving XI for full-register transfers, or is an explicit
wider spill representation required?

## Validation

All commands ran through `tools/run.py`. Logs are under `.work/_state/logs/`.

| Check | Result | Log basename |
|---|---|---|
| Incremental `gcc_build.py --if-stale` | PASS, 24.4 minutes | `s5_16_build-20261106-012220.log` |
| T0 | PASS, 52 tests | `s5_16_t0-20261106-012355.log` |
| Full T1 and T2 | T1 FAIL: `f_s16` instruction scan; T2 PASS | `s5_16_t1_t2-20261106-014703.log` |
| Torture before | O0: 1942 compiled, 61 failed; O2: 1943 compiled, 60 failed | `s5_16_before-20261106-011757.log` |
| Torture after | FAIL: changed failures below | `s5_16_after-20261106-014703.log` |
| s5_ops README builds and lint | PASS, four variants; five existing width-conversion kernels checked vectorized | `s5_16_acceptance-20261106-014703.log` |
| Byte guard build, instruction checks and lint | PASS; execution pending lead | `s5_16_native-20261106-014703.log` |

Torture's changed functions, with fixed `-O0` and `-O2` options:

- O0 `pr60502.c`, `foo`: reload ICE, maximum 90 generated reload insns.
  The short existing reproducer uses a V16QI pointer, an all-ones constant,
  and `*x |= *x ^ m1`.
- O0/O2 `pr70240.c`, `foo`: newly rejected V16HI by-value ABI, as required.
- O2 `pr113089.c`, `intrapred_chroma_plane`: changed assembly.
- O2 `pr37713.c`, `add_opush`: changed assembly.
- O2 `pr60502.c`, `bar` and `foo`: changed assembly.
- O2 `pr82052.c`, `main` with inlined `fn11`: ICE in
  `ix86_vector_duplicate_value`, reached from `gen_vec_initv16qiqi`.

The complete comparison is `.work/_shared/s5-16/torture-after.txt`; retained
assembly and diagnostics are in its `before/` and `after/` directories.
The other original failures have identical diagnostics. The post-change run has
1940 identical O0 assemblies and 1938 identical O2 assemblies.

Card binaries for the lead, built but **not executed**:

- `.work/_shared/s5-16/knc-byte-guard.mic --native`
- `.work/_shared/s5-16/s5_ops/{o2v,o3,fast,neg}.mic`

## Shared i386 changes

The separate shared commit changes five hunks: two in `i386.cc` (supported-mode
dispatch and related-mode hook) and three in `sse.md` (extension/truncation
expander guards). Total: six added and four removed lines. KNC implementation
changes are confined to `i386-knc.cc`, `i386-knc.h` and `imci.md`. No x86 batch
check was run; the ticket assigns that to the next batch check.
