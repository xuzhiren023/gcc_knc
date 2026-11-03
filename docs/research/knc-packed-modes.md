# KNC packed modes: S3-01 source audit

Source snapshot: fork `knc` = `bdcb9b5c10d67c77d9202e40cc890ab61d3749cb`;
donor `donor` = `93871d75a24c80b24b1cbe9cf25c204383e76136`.
All GCC reads used `git show`/`git grep`, never checkout files. Below, bare
`sse.md`, `i386.cc`, etc. mean `gcc/config/i386/` in that fork; `gcc/...`
means a fork path from its root; donor references are explicitly prefixed.
Line intervals include their endpoints. Proposed changes and line estimates
are design judgments, not implemented or compiled results.

## Decisions needed for ADR-0005

* Use an **expander-only move iterator**: widening `VMOVE` enables
  `*vmov<mode>_constm1_pternlog_false_dep` even without AVX-512
  (`sse.md:1536-1546`). Use an expander-only integer-logic iterator too:
  `VI` exposes ternary-logic insns and splits (`sse.md:19036-19064`,
  `19350-19440`). Register constraints are not a substitute for false insn
  conditions (`constraints.md:81-101`).
* Register broadcasts exist for both FP modes: `vpermf32x4 $0` followed by
  a swizzled `vmovaps` or `vmovapd`; the latter uses 256-bit swizzle groups,
  correctly (327364-001, section 2.2.1, tables 2.2/2.3, printed pp. 29-30;
  chapter 6, VMOVAPD pp. 376-377, VMOVAPS p. 379, VPERMF32X4 p. 482).
* The driver's arrays have **matching**, not different, offsets. Cheap
  still needs unaligned moves: it disables alignment peeling/versioning,
  and the separately compiled loops know only scalar alignment
  (fixture `driver.c:75-86,99-107`, `loops.c:1-18`;
  `gcc/tree-vect-data-refs.cc:2858-2864,2953-2965`).
* Extending only the existing vector-mode ABI test misses large aggregates:
  classification returns before visiting their fields. Reject contained
  vector types before that return (`i386.cc:2271-2278,2297-2306,2382-2388`).

## Standard names and their owners

The modes already exist (`i386-modes.def:83-93`); this is target legality,
not creation of modes. In this table `m` expands separately to `v16sf`,
`v8df`, `v16si`, `v8di`; scalar suffix `s` is respectively `sf`, `df`,
`si`, `di`. `A` means `TARGET_AVX512F`, `S` means `TARGET_SSE`, `S2`
means `TARGET_SSE2`. Iterator and expander conditions are conjunctive.
Mask/round substitutions are `1` for the ordinary standard names
(`subst.md:64,204-212`). Each row describes the current source, before KNC.

| Modes and concrete standard names | Owner, iterator entry | Expander condition; body |
|---|---|---|
| All four: `movm` | `sse.md:1462-1469`; `VMOVE`, all four entries `A` at `289-295` | `S`; `ix86_expand_vector_move(mode, operands)`, `DONE` |
| All four: `movmisalignm` | `sse.md:1950-1957`; same `VMOVE` entries | `S`; `ix86_expand_vector_move_misalign`, `DONE` |
| All four: `vec_initms` (`vec_initv16sfsf`, `vec_initv8dfdf`, `vec_initv16sisi`, `vec_initv8didi`) | `sse.md:29756-29763`; `VEC_INIT_MODE`, four entries `A` at `29735-29740` | `S`; `ix86_expand_vector_init(false, dst, vals)`, `DONE` |
| FP: `vec_duplicatev16sf`, `vec_duplicatev8df` | Nowhere: the standard duplicate expander is integer-only (`sse.md:32363-32384`); `mmx.md:49-70` has only small vectors | Free standard names for `imci.md`; vector initialization currently reaches duplication through `i386-expand.cc:18720-18724`, not a named FP expander |
| Integer: `vec_duplicatev16si`, `vec_duplicatev8di` | `sse.md:32372-32384`; `INT_BROADCAST_MODE`, V16SI `A`, V8DI `A && TARGET_64BIT` at `32366-32368` | `S2 && TARGET_INTER_UNIT_MOVES_TO_VEC`; `ix86_expand_vector_init_duplicate(false, mode, dst, src)`, assert success, `DONE` |
| FP: `addv16sf3`, `subv16sf3`, `addv8df3`, `subv8df3` | `sse.md:2667-2673`; `VF_BHSD`, FP entries `A` at `404-406` | `S && mask-condition && round-condition`; `ix86_fixup_binary_operands_no_copy(PLUS/MINUS, mode, operands)` |
| FP: `mulv16sf3`, `mulv8df3` | `sse.md:2756-2762`; same `VF_BHSD` entries | Same condition; same fixup with `MULT` |
| FP: `fmav16sf4`, `fmav8df4`, also `fmsm4`, `fnmam4`, `fnmsm4` | `sse.md:6200-6226`; `FMAMODEM`, FP entries `A` at `6195` | No explicit condition or C helper: emit FMA RTL, with the negations shown at `6212,6217,6224-6226` |
| V16SI: `addv16si3`, `subv16si3` | `sse.md:16585-16591`; `VI_AVX2`, V16SI `A` at `574` | `S2`; binary fixup with PLUS/MINUS |
| V16SI: `mulv16si3` | `sse.md:17245-17265`; `VI4_AVX512F`, V16SI `A` at `660-661` | `S2 && mask-condition`; SSE4.1 path forces vector operands and fixes up; otherwise calls `ix86_expand_sse2_mulv4si3` and `DONE` |
| V16SI/V8DI: `andm3`, `iorm3`, `xorm3` | `sse.md:19082-19091`; `VI`, both entries `A` at `555-560` | `S`; `ix86_expand_vector_logical_operator`, `DONE` |

These standard names are instantiated once, in `sse.md`, except the free FP
duplicate names. `i386.md`'s relevant arithmetic/move iterators contain scalars
(`i386.md:1148-1207,1355-1369`); `movxi` is scalar transport, not `movv16sf`
(`i386.md:2394-2404`). `mmx.md:49-70` supplies only smaller vector iterators.
Current `imci.md:7-9,147-194` supplies scalar moves and XI transport.

V8DI add/sub are already named by `VI_AVX2` (`sse.md:575,16585-16591`), and
multiply by `VI8_AVX2_AVX512F` (V8DI entry `A` at `sse.md:695-696`,
expander at `17286-17294`); leave them unavailable
on KNC in S3. Widen **only V16SI** in the add/sub iterator, or gate the
expander by a supported-operation predicate. Legal V8DI storage does not
justify advertising arithmetic without an implementation. FP affine requires
load/store, construction of `a`/`b`, multiply/add or contracted FMA, and scalar
remainders; recurrence is a dependency, not a request for vector subtraction
(fixture `loops.c:6-28`; `gcc/tree-vect-loop.cc:2127-2129`).

KNC dispatch must precede the existing bodies: the move helper can select SSE
constant broadcasts and unaligned moves (`i386-expand.cc:672-725,740-760`);
64-byte misalignment merely emits a SET today (`949-960`); integer multiply
otherwise invokes a V4SI SSE emulation (`sse.md:17252-17263`); logical expansion
can reinterpret integer operands as FP vector logic (`i386-expand.cc:1413-1452`).
`vec_init` must support identical scalars, constants, and general initialization
without constructing illegal half vectors: its existing concat/duplicate/pool
paths are `i386-expand.cc:18668-18695,18713-18729`. A visible scalar-store/packed-load
fallback can live in `i386-knc.cc`; do not silently reuse SSE concat helpers.

## Complete consumer audit of the candidate widened iterators

All RTL consumers of these eight iterators are in `sse.md`. The tables list
every consumer, including unnamed splits. Evaluate with KNC true, SSE/AVX
features false, size 64, and **only the selected mode entry widened**;
expander conditions have not yet been edited. `F` is false, `T` true, `P`
true when the stated ordinary operand predicate holds. This distinguishes
condition truth from whether a constrained alternative could allocate.

| Iterator | Consumer (`sse.md:line`) | Whole condition under KNC |
|---|---|---|
| VMOVE | `mov<mode>`:1462 | F: `S` |
| VMOVE | `mov<mode>_internal`:1471 | F: `S && (reg0 \|\| reg1) && hardreg_mov_ok` |
| VMOVE | all-ones split:1524 | F: `A && reload_completed && (size64 \|\| extended-reg) && speed` |
| VMOVE | `*vmov<mode>_constm1_pternlog_false_dep`:1536 | **T**: `TARGET_AVX512VL \|\| size64`; emits `vpternlogd` |
| VMOVE | `movmisalign<mode>`:1950 | F: `S` |
| VF_BHSD | add/sub, including mask/round substitutions:2667 | F: `S && mask-condition && round-condition` |
| VF_BHSD | multiply, including substitutions:2756 | F: same |
| FMAMODEM | `fma<mode>4`:6200 | **T**, implicit condition; direct RTL |
| FMAMODEM | `fms<mode>4`:6207 | **T**, implicit condition; direct RTL |
| FMAMODEM | `fnma<mode>4`:6214 | **T**, implicit condition; direct RTL |
| FMAMODEM | `fnms<mode>4`:6221 | **T**, implicit condition; direct RTL |
| VEC_INIT_MODE | `vec_init<mode><ssescalarmodelower>`:29756 | F: `S` |
| INT_BROADCAST_MODE | `vec_duplicate<mode>`:32372 | F: `S2 && TARGET_INTER_UNIT_MOVES_TO_VEC` |
| VI_AVX2 | `neg<mode>2`:16577 | F: `S2` |
| VI_AVX2 | add/sub expander:16585 | F: `S2` |
| VI_AVX2 | `*<insn><mode>3`:16633 | F: `S2 && binary_operator_ok` |
| VI_AVX2 | `<sse2_avx2>_andnot<mode>3`:18852 | F: `S2` |
| VI_AVX2 | scalar-not/broadcast/and split:19021 | F: `TARGET_AVX2` |
| VI_AVX2 | `abs<mode>2`:23856 | F: `S2` |
| VI4_AVX512F | `mul<mode>3<mask_name>`:17245 | F: `S2 && mask-condition` |
| VI4_AVX512F | `*<sse4_1_avx2>_mul<mode>3<mask_name>`:17267 | F: `TARGET_SSE4_1 && binary_operator_ok && mask-condition` |
| VI4_AVX512F | `vec_widen_<s>mult_odd_<mode>`:17334 | F: `S2` |
| VI | `one_cmpl<mode>2`:18738 | F: `S` |
| VI | `<mask_codefor>one_cmpl<mode>2<mask_name>` insn/split:18750 | F: `A && (!mask_applied \|\| innerSI \|\| innerDI)` |
| VI | `*one_cmpl<mode>2_pternlog_false_dep`:18815 | F: `A` |
| VI | `andn<mode>3`:18859 | F: `S2` |
| VI | `*andnot<mode>3`:18877 | F: `S && (reg1 \|\| reg2)` |
| VI | scalar-not/broadcast/ior split:19036 | **T**: `size64 \|\| AVX512VL \|\| (A && !prefer256)` |
| VI | scalar-not/broadcast/xor split:19051 | **T**: same |
| VI | `<code><mode>3` logic expander:19082 | F: `S` |
| VI | `*iornot<mode>3`:19350 | **P**: `(size64 \|\| AVX512VL \|\| (A && !prefer256)) && (reg1 \|\| reg2)` |
| VI | `*xnor<mode>3`:19383 | **P**: same |
| VI | `*nor<mode>3`, `*nand<mode>3`:19415 | **P**: same; `andor`/`nlogic` at `19411-19413` |

Thus the newly true **insns** are the VMOVE all-ones pattern and VI iornot,
xnor, nor, nand; the newly true **expanders** are all four FMA forms; the
newly true **splits** are VI's two broadcast/not splits. Do not widen VMOVE
or VI globally. Clone their original membership into expander-only iterators,
then add KNC solely to the intended entries and expanders. VF_BHSD,
FMAMODEM, VEC_INIT_MODE, INT_BROADCAST_MODE, VI_AVX2 and VI4_AVX512F have
no newly enabled SSE insn from entry widening alone (consumer table above).
`VEC_INIT_HALF_MODE` is separate and stays disabled (`sse.md:29745-29771`).

FMA widening must implement or explicitly exclude `fms`, `fnma`, `fnms`, not
just `fma`. FP arithmetic mask/round variants also need deliberate gating;
their size-based attributes are not ISA guards (`subst.md:64,208-212`).

## Duplicate standard names: generator proof, no build

**A second named definition fails in generated C++, even with disjoint target
conditions.** `gcc/gencodes.cc:32-45` emits a `CODE_FOR_name` enumerator for
every nonempty, non-`*` name; even a compile-time-false condition emits that
same enumerator as `CODE_FOR_nothing`. Insn elision is disabled at `54-56`,
and both DEFINE_INSN and DEFINE_EXPAND use that emitter at `73-79`.
Two `movv16sf` definitions therefore redeclare the same enumerator.

Independently, `gcc/genemit.cc:417-426,488-512` emits `gen_name(...)` for
each expander, without using its runtime target condition as a C++ function
namespace. `gcc/genopinit.cc:42-46` appends each matching optab pattern;
`364-367` writes each entry using `CODE_FOR_name`. These are not mechanisms
for choosing between duplicate definitions. Keep the existing standard
expander, and emit uniquely named or `*knc_` insns, as the existing `movxi`
dispatch illustrates (`i386.md:2394-2404`). No compiler build was performed.

## Hooks, predicates and allocation paths

Each row gives behavior after the four modes are admitted, with all SSE/AVX
flags still false, and the required adjustment or reason to leave it alone.

| Entry point | Behavior and disposition, with source |
|---|---|
| `preferred_simd_mode` | Still returns `word_mode` immediately (`i386.cc:26038-26041`). Add a KNC-first call mapping SF/DF/SI/DI to the four 64-byte modes and all others to word mode. |
| `vector_mode_supported_p`; related mode | Still rejects the four modes through feature gates (`i386.cc:25214-25236`). Add an exact four-mode, 64-bit KNC predicate. Default related-mode selection calls this hook (`gcc/targhooks.cc:1611-1623`); no separate widening needed. |
| `autovectorize_vector_modes` | Adds nothing with SSE/AVX/MMX off (`i386.cc:26126-26159`); keep it, so no smaller illegal vector size is offered. |
| `hard_regno_mode_ok` | KNC SSE-bank early return admits only SF/DF/SI/DI/TI/TF/XI (`i386.cc:21932-21937`). Extend that return with the exact predicate; masks remain HI-only. GP whitelist excludes these vectors (`21994-22012`; `i386.h:1183-1200`); do not extend it. |
| `hard_regno_nregs`, `class_max_nregs`, natural size | SSE bank uses one register (`i386.cc:21891-21907,21548-21564`); no new feature gate. Natural-size hook returns word size (`21912-21916`); it does not legalize modes. No change for these packed moves. |
| `modes_tieable_p`; `can_change_mode_class` | Equal modes tie; 64-byte vector/XI ties and permitted smaller scalar-FP ties follow `hard_regno_mode_ok` (`i386.cc:22114-22146`). QI/HI mode changes remain excluded without SSE2 (`21571-21599`). No extra mode widening needed. |
| `get_mask_mode` | Without AVX-512 returns V16SI for 16 lanes or V8DI for eight, not HI/QI (`i386.cc:26165-26191`). Leave unchanged in S3; do not advertise compares, masked operations or tails. Partial-vector usage defaults to zero (`i386-options.cc:3189`); eight-bit masks in HI require later design. |
| Misalignment, alignment reachability | i386 installs no override for the default misalignment hook (hook registrations `i386.cc:28731-28748`; default `gcc/target.def:1933-1936`). Default asks for `movmisalign` optab (`gcc/targhooks.cc:1570-1580`); legal modes alone still return false. Enable that optab only after the pair fault probe. Default alignment reachability accepts nonpacked elements (`1558-1563`). |
| `standard_sse_constant_p`; move predicates | Returns zero immediately without SSE (`i386.cc:5514-5519`), so even zero fails `nonimmediate_or_sse_const_operand` (`predicates.md:1350-1352`). Add a KNC-first constant helper accepting only supported-mode zero; put other constants in a 64-byte aligned pool. Do not use `standard_sse_constant_opcode`, which asserts SSE (`i386.cc:5568-5574`). `preferred_reload_class` already keeps zero and sends nonzero constants to memory (`21145-21159`). |
| Other operand predicates | `sse_reg_operand` tests register numbering, not SSE availability (`predicates.md:65-67`). `vector_memory_operand` allows memory only with AVX or natural alignment (`1273-1277`); `vector_operand` inherits it (`1280-1282`). Keep aligned arithmetic operands or force registers through the KNC move helper. `bcst_mem_operand` requires AVX512F (`1299-1307`); create KNC predicates for folded broadcasts instead of widening it. Generic constant-vector predicates do not validate the ISA (`1316-1318,2127-2129`). |
| Expand move/init/duplicate | Dispatch before SSE helpers described above. Duplication's generic recognizer retries a scalar register then asserts success (`i386-expand.cc:17377-17407`); implement KNC memory/register broadcasts and visible x87/GPR bridges. General init must not require SSE half-vector assembly (`18668-18695`). |
| `type_natural_mode`, `classify_argument` | Natural mode's AVX512 warning applies when a vector type lacks a vector mode (`i386.cc:2063-2108`); legal packed types bypass that branch. Existing XI-only diagnostic (`2274-2278`) must cover the four modes. To enforce the ADR's contained-member ban, walk by-value aggregate/array/union types before size/stack early exits (`2285-2306`), not just recursively classified fields (`2382-2388,2403-2407`). Stop the walk at pointer types. |
| Function values; container | SysV typed return goes through `ix86_function_value` -> `function_value_64` -> `construct_container` -> classification (`i386.cc:4453-4459,4439-4448,4362-4369,2835-2837`). The existing container guard rejects vector modes only when SSE regs were requested (`2846-2857`), so it does not replace the early type guard. Untyped vector libcalls fall through to AX (`4318-4345`); do not introduce packed libcalls, or diagnose those explicitly if ever added. |
| Preferred/output reload classes | Input preserves the requested class for packed nonconstants when SSE math is off (`i386.cc:21182-21214`); output falls through to that class (`21226-21237`). Existing scalar/XI KNC exception need not grow merely for these packed modes. `YJ` supplies the KNC bank; x/v/k/Yk remain feature-gated (`constraints.md:81-101`). |
| Secondary reload/memory | KNC cross-bank reload switch handles scalars, not packed modes (`i386.cc:21247-21268`). Packed values live only in zmm; spills are memory moves, so no packed GPR bridge is needed. Cross-bank scalar subregs retain the visible S2 bridge. `secondary_memory_needed`'s exception is scalar-only (`21516-21525`); default cross-bank memory cost remains present without SSE2 (`21475-21479,21818-21827`). Secondary memory mode leaves 512 bits unchanged (`21535-21539`). |
| Spill slots/frame | `spill_slot_alignment` uses mode alignment (`gcc/function.cc:275-277`), through `STACK_SLOT_ALIGNMENT` -> `ix86_local_alignment` (`i386.h:933-934`), which preserves it for a typeless packed slot (`i386.cc:18852-18859`). LRA accumulates that alignment (`gcc/lra-spills.cc:333-334`). BIGGEST_ALIGNMENT already is 512 on KNC (`i386.h:851-853`); frame scanning uses MEM_ALIGN, not SSE availability (`i386.cc:8907-8923,9103-9110`). No new alignment hook is needed; emit aligned spill MEMs. Alternate register spilling is disabled unconditionally (`26204-26213`). |
| Register/memory and RTL costs | SSE-bank memory costs index by size, with 64 bytes at index 4 (`i386.cc:21605-21624,21673-21682`); cross-bank copies retain memory costs (`21818-21844`). `ix86_set_reg_reg_cost` incorrectly treats KNC packed moves as eight word pieces (`22202-22215`): include the exact KNC predicate, without enabling AVX. |
| Vectorizer costs | KNC architecture selects PROCESSOR_GENERIC (`gcc/common/config/i386/i386-common.cc:2221`), whose table is `generic_cost` (`i386-options.cc:765`); speed selects tune costs, size selects size costs (`2558-2561`). Fallback builtin costs use SSE-named scalar/load/store/vector fields (`i386.cc:25755-25861,25873-25879`); keep their provisional nature explicit. The actual `create_costs` object overrides scalar FP add with x87 `fadd` when SSE math is off (`26338-26340,26384-26398`), so the ADR's claim that all scalar statements use SSE costs is too broad. `vec_construct` fallback assumes SSE inserts/half vectors (`25841-25861`); price a KNC memory fallback by its real transfers when enabled. |
| Cost finalization/pressure | `finish_cost` calls the pressure estimate (`i386.cc:27063`), which assumes 16 vector registers without AVX512F and entirely skips vector pressure when SSE is false (`26985-26996`). Include KNC, count 32, and use packed spill cost when estimating packed pressure. Existing x87 construction transfers are partly costed at `26868-26877`; KNC-specific broadcast/init costs must retain any extra transfers. Generic numeric tuning can wait, but these operations must remain visible. |

The donor has no KNC mode-selection shortcut to port: its mode support is
SSE/AVX-only (donor `i386.c:46004-46018`), preferred mode returns word without
SSE (donor `i386.c:51757-51760`), and its KNC move iterators are scalar
(donor `knc.md:21-30`). The corresponding mechanisms still exist in the
fork at the hook locations above; no donor backend modification is proposed.

## Register-only broadcasts: semantics and assembler result

Input: scalar bits in low SF/DF lane of zmm0; upper lanes may be arbitrary.
Use two ordinary instructions, with scratch zmm1 and result zmm2:

```asm
vpermf32x4 $0, %zmm0, %zmm1
vmovaps %zmm1{aaaa}, %zmm2       # V16SF
# or, for V8DF:
vmovapd %zmm1{aaaa}, %zmm2
```

VPERMF32X4 repeats the low 128 bits four times and does not itself permit
swizzling (327364-001, chapter 6, VPERMF32X4, p. 482). For SF, each 128-bit
group then has the desired scalar in its first element; `{aaaa}` replicates
it within each group (section 2.2.1/table 2.2, p. 29). For DF, after the
permute the eight qwords are `[a,b,a,b,a,b,a,b]`; each **256-bit** group
begins with `a`, so the 64-bit `{aaaa}` produces eight `a` values
(table 2.3, p. 30). VMOVAPS/VMOVAPD register-source operations explicitly
use SwizzUpConvLoadf32/f64 (chapter 6, pp. 379 and 376-377). There is no FP
arithmetic or rounding, including for signed zero and NaN bit patterns.
Source and result may alias when allocator constraints permit; the RTL must
expose the intermediate value/scratch, not an opaque instruction sequence.

Each of those three instruction lines was assembled once, separately, by
shared `toolchain/cross/bin/k1om-mpss-linux-as --march=k1om`; all exited 0.
Run: `tools/run.py --name s3-01-broadcast`, Cygwin Python 3.12 probe driver.
Log: `.work/_state/logs/s3_01_broadcast-20261103-152320.log`.
This checks syntax/architecture acceptance only; no native execution occurred.
An initial shell invocation did not start the runner because PATH resolved
`python` to a Cygwin symlink; the successful invocation selected its executable
explicitly. No GCC build or card test was attempted.

## Optimization levels and the actual arrays

`-O2` selects **very-cheap** (`gcc/opts.cc:676-677`);
`-O2 -ftree-vectorize` selects **cheap** (`1440-1446`);
`-O3` selects **dynamic** (`714`). These describe vectorizer policy, distinct
from the generic target cost tables above.

The fixture compiles loops separately with runtime `n` and restrict pointers
(`loops.c:1-18`). Driver storage bases are aligned to 64, but both arguments
receive the same element offset (`driver.c:75-86`). Both guard cases end
at a page boundary with the same length (`driver.c:42-54,99-107`), hence
also have matching offsets modulo 64. This is a caller fact, not an alignment
promise visible in the loop compilation. Unknown `n` also requires handling
`n % 16` or `n % 8`; the vectorizer's remainder test is
`gcc/tree-vect-loop.cc:959-991,2127-2129`.

| Flags | Alignment peeling/versioning and `movmisalign` requirement |
|---|---|
| `-O2` | Positive alignment peeling is disabled for models <= cheap (`gcc/tree-vect-data-refs.cc:2861-2864`); alignment versioning requires > cheap (`2962-2965`). Thus unaligned full-vector load/store support is necessary to vectorize these unknown-alignment loops. Partial vectors stay off, so arbitrary runtime lengths also need scalar remainder handling. Very-cheap rejects alignment/gap peeling and profitability above one vector iteration (`gcc/tree-vect-loop.cc:1844-1853,1915-1926`); mode legality alone does not guarantee vectorization. |
| `-O2 -ftree-vectorize` | Same alignment restrictions: `movmisalign` is necessary. Scalar remainder and a short-trip/profitability branch may coexist with the vector body (`gcc/tree-vect-loop.cc:1873-1907,2127-2129,2532-2547`). Restrict removes the affine loop's need for alias disambiguation; cheap is not a general ban on alias versioning (`gcc/tree-vect-data-refs.cc:4453-4459`). |
| `-O3` | Dynamic permits alignment peeling and versioning (`gcc/tree-vect-data-refs.cc:2858-2880,2953-2965`). With `movmisalign`, neither is required for correctness; cost may choose peeling. Without it, a version guarded by alignment checks can vectorize the aligned cases. Peeling to align one pointer cannot prove the other's alignment in the separately compiled loop: the driver has congruence, the function contract does not. A congruence/alignment check plus peeling could cover more cases, but do not assume GCC synthesizes that combination. Scalar fallback covers failed checks; scalar remainder handles runtime lengths (`gcc/tree-vect-loop.cc:959-991,2532-2547`). |

No code-generation/profitability prediction here is a compiled result.
Unaligned pairs remain conditional on S3-03's page-fault findings; this
ticket's broadcasts say nothing about their memory safety. Scalar peel/tail
uses the existing x87 path (`i386.h:1215-1224`; scalar FP patterns
`i386.md:10961-10993,11705-11717`).

## Shared-i386 estimate and placement

The sprint measure is added **plus** deleted lines against
`releases/gcc-16.2.0`, in `gcc/config/i386` and `gcc/common/config/i386`,
excluding `imci.md`, `linux-k1om.h`, `i386-knc.*`. Read-only `git diff
--numstat` at the snapshot gives **251** current shared lines, leaving 49.
The following estimates use normal multi-line dispatches (five added lines),
two counted lines for a one-line replacement, and no compressed formatting
to evade the measure. They are a concrete implementation sketch, not a diff.

| Ticket | Estimated incremental shared lines | Derivation and allocation verdict |
|---|---:|---|
| S3-04 | **37** | Expander-only VMOVE copy 12; mov operand replacements 4, condition 2, dispatch 5 (`sse.md:286-295,1462-1469`); mode-support call 2, hard-reg extension 1, zero-constant call 2, ABI guard replacement 3, register-copy-cost extension 1 (`i386.cc:25214,21934,5514,2274,22204`); prototype include 1; t-i386 object rule 4 (`t-i386:65-71`). **Over 24 by 13.** |
| S3-05 | **11** | Use new move iterator in two operands 4, condition 2, dispatch 5 (`sse.md:1950-1957`). **Over 6 by 5.** Pair logic is KNC-only. |
| S3-06 | **35** | VF_BHSD FP entries 4, two conditions 4, two dispatches 10 (`sse.md:404-406,2667-2673,2756-2762`); FMAMODEM entry replacement 2 (`6195`); scalar-element vec_init entries for all four modes 8, condition 2, dispatch 5 (`29735-29762`). **Over 12 by 23.** Assumes all four FMA families receive KNC insns; selective exclusion costs extra shared gating. |
| S3-07 | **8** | Preferred-mode early call 2 (`i386.cc:26038-26041`); three pressure-cost line replacements 6 (`26986,26989,26995`). **Over 4 by 4.** Additional KNC constructor-cost dispatch, if needed, is extra; generic table calibration is deferred. |
| S3-09 | **50** | SI add/sub entry/condition/dispatch 9 (`sse.md:574,16585`); SI multiply same 9 (`661,17245`); expander-only VI clone 8 plus logic operands 6, condition 2, dispatch 5 (`555-560,19082`); integer duplicate entries 4, condition 2, dispatch 5 (`32366-32384`). **No allocation: all 50 need a lead/owner decision.** Vec_init is counted once in S3-06. |

This sketch adds 91 shared lines before S3-09: **342 total**, 42 over the
300 cap; with S3-09, **392**. Different iterator organization may reduce
this, but the existing allocations are not demonstrated by the proposed ADR.
The ABI guard estimate assumes the by-value type walk is entirely KNC-only;
its call must precede the existing large-aggregate return (`i386.cc:2304-2306`).

Put mode predicates, ABI type walking, preferred-mode selection, move/constant
expansion, broadcast construction, general vec_init fallback and unaligned
pair expansion in `i386-knc.cc`, declarations in `i386-knc.h`; put instruction
patterns in `imci.md`. The shared call sites and iterator/condition changes
above remain necessary. Cost-class internals are private to `i386.cc`
(`26308-26340,26983-26996`); moving those wholesale requires an interface,
so the estimate keeps the small pressure edits shared. New object registration
also changes `gcc/config.gcc:439` (about two added-plus-deleted lines), which
is **outside** the sprint's directory measure; do not omit that integration
just because KNC-only files are excluded. No fork changes were made here.
