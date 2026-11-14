# KNC register design (S2-01)

**ABI qualification, S12-13 (2026-11-14).** R03 §§3.2.1–3 pp.15–22,
especially Fig.3.4 p.21 ([index](knc-references.md)), is the recovered K1OM
ABI authority for this historical design: all 32 ZMM and eight mask registers
are caller-clobbered; MXCSR control bits and x87 control word are callee-saved,
status is caller-clobbered. Its SSE class name does not enable SSE. Register
availability does not establish a free GPR/x87/ZMM transfer, and a call save
is not necessarily a removable allocator spill. R12 CD14 p.22 separately
requires OS mask-state handling across context switches; ABI call clobbers
do not relax that requirement.

Recommendation: reuse GCC 16's existing vector and mask hard-register numbers,
but give KNC its own mode whitelist, constraints and IMCI moves. Do not enable
SSE/AVX feature bits to obtain ABI registers. This is a source design, with no
fork changes, compiler runs or native results claimed.

Evidence notation: `G:` means `../_shared/gcc/`, `D:` means
`../_shared/gcc-donor/`; paths below are relative to those roots. Line numbers
count newline characters (GCC sources also contain form feeds). Recommendations
and test proposals are identified as such; citations give their source basis.

## Existing gates and their distinct effects

| Gate in GCC 16 | What it controls |
| --- | --- |
| `G:gcc/config/i386/i386.cc:552`, `:560` | `ix86_conditional_register_usage` removes **all** vector registers from `accessible_reg_set` without SSE, and separately removes xmm16–31 and k0–7 without AVX512F. The 32-bit REX exclusions at `:518` must remain. This is register accessibility, not instruction enablement. |
| `G:gcc/config/i386/i386.cc:21812`, `:21835`, `:21848` | `ix86_hard_regno_mode_ok` permits QI/HI masks with AVX512F, SI/DI masks with AVX512BW; paired mask modes take an earlier path. AVX512F admits XI/512-bit vectors and selected scalars in every vector register; AVX512VL admits smaller modes in extended registers; otherwise xmm16–31 are rejected. The xmm0–15 fallback at `:21852` accepts many smaller modes without testing SSE: accessibility normally protects it. |
| `G:gcc/config/i386/i386.h:1126`, `:1131`; `G:gcc/config/i386/i386-modes.def:87`, `:92`, `:106` | Mode definitions already exist; `VALID_AVX512F_*` are lists, not capability switches. The current lists include half/bfloat and byte/word modes that must not be inherited wholesale by KNC. XI is a 64-byte integer container. |
| `G:gcc/config/i386/i386.cc:25093`, `:25099`, `:25911` | `vector_mode_supported_p` advertises native vector types by ISA; preferred SIMD mode falls back to a word without SSE. Neither hook alone supplies legal move/arithmetic optabs. |
| `G:gcc/config/i386/i386.md:2384`; `G:gcc/config/i386/sse.md:287`, `:1462` | XI move expansion requires AVX512F; SSE vector move expansion requires SSE and its iterator gates 512-bit forms on AVX512F. Legal hard-register storage alone cannot supply these moves. |
| `G:gcc/config/i386/constraints.md:81`, `:84`, `:91`, `:94` | `Yk` selects k1–7 and `k` k0–7 only with AVX512F; `x` selects xmm0–15 and `v` xmm0–31 only with SSE. Class membership itself already exists (`G:gcc/config/i386/i386.h:1503`, `:1504`, `:1510`, `:1511`). |
| `G:gcc/config/i386/i386.cc:2578`, `:2584`, `:2823` | SF/DF classification produces SSESF/SSEDF classes even without SSE. `construct_container` subsequently rejects a required vector container without SSE (and has a separate SSE2 check for newer half/bfloat types, defined at `G:gcc/config/i386/i386.h:1148`). Classification is not the gate to widen. |
| `G:gcc/config/i386/i386.cc:1586`, `:1927`, `:3889` | Argument-register recognition, the cumulative vector-argument budget, and recognition of xmm0/1 as result registers each require SSE. All three need a KNC ABI exception. |
| `G:gcc/config/i386/i386.cc:3494`, `:4311`, `:4291` | SysV arguments and typed results share `construct_container`; SF/DF libcalls already select the first vector register directly. Preserve that result location rather than changing libcalls to x87 returns. |
| `G:gcc/config/i386/i386.cc:4660`, `:4900`, `:4710` | SSE gates the varargs FP save area and initial FP offset. Its generic saver uses V4SF, 16-byte slots and `%al` before saving; it needs a KNC transfer implementation, not a 64-byte overwrite of each slot. Caller count production is at `:3454`. |
| `G:gcc/config/i386/i386.h:849` | Maximum natural alignment is 512 bits only with AVX512F; full KNC register spills need a separate KNC alignment allowance. This does not establish a new incoming stack ABI. |

## Donor: retain the convention, rewrite the mechanism

The donor changes argument recognition, register budgets, container rejection,
return-register recognition and varargs gates to `SSE || KNC`
(`D:gcc/config/i386/i386.c:6271`, `:6581`, `:7345`, `:8311`, `:8785`,
`:9091`). Its 16-byte FP save slots remain (`:8786`, `:8834`, `:8840`),
and `%al` is tested before saving (`:8822`). These ABI choices fit GCC 16's
surviving hooks in the table. Retain SysV eightbyte classification and the
first-eight argument budget, including aggregates; do not widen the separate
MS ABI gates (`G:gcc/config/i386/i386.cc:3521`, `:4348`).

The donor uses broadcasts for SF/DF memory loads and full zmm register copies
(`D:gcc/config/i386/i386.md:3267`, `:3467`); stores use a mask of 1 for
32/64 bits or 3 for 128 bits (`D:gcc/config/i386/i386.c:17537`) and
`vpackstorel*` (`D:gcc/config/i386/knc.md:89`). Transfers through memory
and x87 bodies fit the required convention; keep the mechanism in `imci.md`,
as directed by the ticket's inventory. GCC 16 still has secondary reload,
secondary-memory and move-cost hooks (`G:gcc/config/i386/i386.cc:21154`,
`:21325`, `:21702`); donor C and pattern text need rewriting, not direct copying.

Two donor shortcuts are incomplete. Its usage hook preserves extended vector
registers under KNC (`D:gcc/config/i386/i386.c:4569`), but its mode hook
still requires AVX512F/VL and otherwise rejects xmm16–31 (`:42344`, `:42352`,
`:42360`): it does not demonstrate usable 32-register allocation with those
flags off. Also, `fixed_regs[MASK2_REG] = 1` is **inside** the
`!(AVX512F || KNC)` branch (`:4569`–`:4578`), so it does not reserve k2
on KNC. Neither behavior should be reproduced.

## Proposed availability and isolation

1. Under 64-bit `TARGET_KNC`, preserve all 32 existing vector registers and
   k0–7 in accessibility. Reuse `ALL_SSE_REGS` as the storage bank; its name
   must not imply SSE capability. Keep x87 available for SF/DF arithmetic.
   Add an **early KNC return** to the mask/vector mode checks so the generic
   fallback cannot silently admit other modes. Existing register ranges and
   class bits suffice (`G:gcc/config/i386/i386.h:1283`–`:1299`, `:1504`;
   mode-hook insertion points `G:gcc/config/i386/i386.cc:21812`, `:21825`).

2. For Sprint 2, permit vector-bank **SF, DF, SI, DI, TI, TF**, plus **XI**
   for full-register transport; masks hold **HI only**. SF/DF and integer
   containers cover scalar/aggregate ABI pieces (`G:gcc/config/i386/i386.cc:2987`,
   `:2995`, `:3007`, `:3013`); the donor supports the six scalar transfer
   modes (`D:gcc/config/i386/knc.md:28`). TF is transport, not hardware quad
   arithmetic. Exclude QI/HI vector scalars, half/bfloat, decimal modes,
   paired masks and SI/DI masks. Supply XI moves with 64-byte aligned storage
   in IMCI before admitting XI (`G:gcc/config/i386/i386.md:2384`;
   `G:gcc/config/i386/i386.h:849`). One vector/mask register per admitted
   noncomplex value already fits the counting hooks (`G:gcc/config/i386/i386.cc:21771`,
   `:21428`).

3. **Do not advertise packed 512-bit vector modes in Sprint 2.** XI supplies
   full-width storage; SF/DF lane zero supplies the scalar ABI. Later IMCI
   work can add V16SI/V8DI/V16SF/V8DF, complete moves and corresponding
   `vector_mode_supported_p` cases together, then arithmetic optabs and SIMD
   preference separately. Do not enable the AVX512F mode lists or SSE
   iterators to do it (`G:gcc/config/i386/i386.h:1131`;
   `G:gcc/config/i386/i386.cc:25099`, `:25911`;
   `G:gcc/config/i386/sse.md:287`).

4. Add dedicated KNC constraints for all zmm storage, all masks, and nonzero
   predicate masks, mapping to `ALL_SSE_REGS`, `ALL_MASK_REGS`, `MASK_REGS`.
   Leave existing `x/v/k/Yk` disabled for KNC. All new instruction patterns
   belong in `gcc/config/i386/imci.md`, with `TARGET_KNC` conditions and
   explicit `%g` zmm operands; the printer already supports `%g`
   (`G:gcc/config/i386/i386.cc:14035`, `:14095`). This avoids the donor's
   broad constraint widening (`D:gcc/config/i386/constraints.md:81`–`:94`).

5. Add KNC exceptions only to the SysV ABI gates above, bypassing the entire
   SSE/SSE2 diagnostic for the admitted KNC containers. Keep SF/DF in lane
   zero of zmm0–7, results in zmm0, and aggregate pieces in successive
   registers using the existing container builder (`G:gcc/config/i386/i386.cc:2880`,
   `:2987`, `:2995`, `:4311`; donor broadcasts/stores cited above).
   Route the varargs 16-byte saver through TI transport under KNC instead
   of admitting V4SF solely for that implementation (`:4710`, `:4727`;
   `D:gcc/config/i386/i386.c:17537`). Preserve `%al` and slot offsets.

6. Keep SSE, SSE2 and every AVX/AVX512 flag off, and x87 math selected;
   retain incompatible-option rejection (`G:gcc/config/i386/i386-options.cc:2177`,
   `:2743`). Shared SF/DF expanders already call `ix86_expand_move`
   (`G:gcc/config/i386/i386.md:4061`): add narrowly scoped KNC dispatch,
   dedicated IMCI recognizers and reload handling. Never widen standard
   constraints or SSE pattern conditions. In particular, unconditionally
   enabled SF move alternatives can otherwise reach `ix86_output_ssemov`
   (`G:gcc/config/i386/i386.md:4379`, `:4409`, `:4428`). Keep secondary
   memory and cost accounting visible; SSE2-off already requires memory
   across the vector/GPR boundary (`G:gcc/config/i386/i386.cc:21361`,
   `:21702`). Relax the output reload preference only for admitted KNC
   transport modes (`:21147`), unlike the donor's broad exemption
   (`D:gcc/config/i386/i386.c:41794`). No vector divide/sqrt optabs are added.

Planning estimate, not a measured diff: shared i386 edits across S2-02–05
should budget about **220 changed lines**: 35 accessibility/mode hooks,
65 ABI/varargs, 55 move/reload dispatch, 25 constraints/include/prototypes,
40 alignment/cost/special-option handling. With the ticket's 45 already
used, that is **265/300**, leaving 35. New `imci.md` patterns are separate
from this shared-file estimate. These buckets correspond to the cited hooks;
keep shared edits in separate commits and return to the lead if implementation
exceeds the remaining 255-line allowance.

## Calls and scratches

Under the donor's **64-bit SysV** convention, every zmm and every k register
is caller-saved; none is callee-saved. Vector entries of 6 include the SysV
bit 4, and k entries are 1 (`D:gcc/config/i386/i386.h:1008`, `:1020`–`:1033`;
normalization `D:gcc/config/i386/i386.c:4530`, `:4540`). GCC 16's existing
SysV entries give the same answer (`G:gcc/config/i386/i386.h:1048`,
`:1056`–`:1069`); do not add preservation obligations or inherit MS ABI rules.

Thus `%eax` (also caller-saved: `D:gcc/config/i386/i386.h:1017`) and `%k2`
are legal local scratches **only with visible definitions/clobbers and correct
liveness**. Their values cannot survive a call. Reload mask 1 after any call
before using it. An EAX definition also destroys `%al`, which must remain live
until the varargs entry test, or be established after scratch work before an
outgoing variadic call (`D:gcc/config/i386/i386.c:8822`;
`G:gcc/config/i386/i386.cc:3454`). Likewise, preserve a live RAX result.

Recommendation: allocate an earlyclobber GPR scratch and an HI mask pseudo
(nonzero-mask class for stores), with explicit mask definitions/uses. Do not
hardcode k2 or permanently reserve EAX. The donor hardcodes k2 in late reloads
(`D:gcc/config/i386/knc.md:45`–`:55`) and searches for a GPR after reload,
falling back to push/pop AX (`D:gcc/config/i386/i386.c:17475`–`:17519`);
caller-saved status does not prove that sequence safe at an arbitrary point.
If a late reload cannot allocate its scratch, redesign that reload contract;
do not hide stack changes or overwrite an allocatable k2.

## T1 risks and proposed checks (not executed here)

| Risk and source trigger | Host T1 check for the implementing tickets |
| --- | --- |
| Widened `v/x` enables legacy scalar SSE moves (`G:gcc/config/i386/i386.md:4379`, `:4409`, `:4428`). | Compile SF/DF identity, constants, ninth argument, mixed aggregates and pressure/spill cases at O0/O2/Os; require lane-zero IMCI transfers and x87 bodies. Reject xmm/ymm operands and unexpected mnemonics with an instruction allowlist. Assemble with the KNC assembler as a separate T2 check. |
| Widened `k` selects `kmovw`, `kxorw`, `kxnorw` (`G:gcc/config/i386/i386.md:3030`, `:3053`); donor spells transfers unsuffixed `kmov` (`D:gcc/config/i386/i386.md:2525`). | Force constant, register and spilled HI mask transfers; require unsuffixed `kmov` and explicit GPR constant materialization. Reject AVX512 mask suffixes/logic. |
| Flags accidentally enabled, including per-function options (`G:gcc/config/i386/i386-options.cc:2177`), or 512-bit SSE iterators exposed (`G:gcc/config/i386/sse.md:287`, `:1465`). | Check effective KNC options/macros and negative SSE/AVX option/target-attribute cases; compile an ordinary arithmetic loop and require no SSE/AVX instructions. Use an IMCI allowlist, not a blanket ban on `v*`: donor IMCI broadcasts/copies also start with `v`. |
| Hidden scratch clobbers, `%al` loss, and 16-byte varargs slot overwrite (donor scratch/save-area sources above). | Compile a variadic entry and outgoing callback plus values live across calls; inspect final RTL scratch def/use, count-before-call and count-test-before-scratch ordering, mask reinitialization, and 16-byte save strides. Runtime interoperability remains T3/T4, not a T1 claim. |
| Full-register spills misaligned; unsupported modes leak through generic fallback (`G:gcc/config/i386/i386.h:849`; `G:gcc/config/i386/i386.cc:21815`, `:21848`). | Force admitted storage through zmm16 and zmm31 and force an XI spill; check 64-byte spill alignment and legal IMCI reloads. Check rejected mask-pair/half/256-bit modes in a target-hook test. |
| Special zero-call-used-regs path assumes V4SF for vectors (`G:gcc/config/i386/i386.cc:3926`) even with SSE off. | Compile with vector/mask zeroing requested; require legal KNC zeroing through admitted modes or an explicit unsupported-option diagnostic. No ICE or accidental SSE zero idiom is acceptable. |

No T1 implementation test is required by this research ticket. The checks
above are obligations for the code tickets; native behavior remains untested.
