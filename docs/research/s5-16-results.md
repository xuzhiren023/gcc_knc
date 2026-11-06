# S5-16 implementation and outstanding results

Acceptance is **not yet met**. The first implementation's signed-word-to-float
scan and two torture ICEs are being corrected after the lead approved exact-size
spills. No program was run on the card.

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

## Spill representation and follow-up fixes

Register moves copy the full zmm. Ordinary pseudo spills currently use the
exact-size transport operations, preserving all sixteen value lanes.
The lead approved these exact-size spills in the ticket answer at 01:52.

The reduced allocator case is a `reg:V16HI` pseudo with no wider subregister
references. `gcc/lra-spills.cc:132-158` derives its slot from the pseudo mode and
`biggest_mode`, producing a 32-byte slot; V16QI similarly uses 16 bytes. A 64-byte
store cannot safely replace that transfer. XI remains the full-register transfer
representation.

Follow-up commits:

- Project `e9d6873`: reduced T1 cases for the reload and constructor ICE classes.
  Both reproduced their expected ICEs before the fixes. The diagnostic wrapper
  exited zero after collecting results; the two compiler invocations exited 1.
  Log: `s5_16_reduced_red-20261106-015544.log`.
- Shared GCC `3cc3a958ba1`: dispatch narrow constructors to KNC initialization,
  including V16HI in the constructor expander.
- KNC GCC `e1112842e87`: make register/load/store alternatives share one move
  pattern so LRA can spill a narrow pseudo without generating endless reloads;
  build narrow constructors through scalar stores and one exact-size load;
  recognize `FLOAT (mem:V16QI/V16HI)`, the canonical form produced by
  `simplify-rtx.cc` from `FLOAT (SIGN_EXTEND mem)`.

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

The separate shared commits change seven hunks: two in `i386.cc` (supported-mode
dispatch and related-mode hook), four in `sse.md` (extension/truncation and
constructor expander guards), and one in `i386-expand.cc` (constructor dispatch).
Total: nine added and six removed lines. KNC implementation
changes are confined to `i386-knc.cc`, `i386-knc.h` and `imci.md`. No x86 batch
check was run; the ticket assigns that to the next batch check.
