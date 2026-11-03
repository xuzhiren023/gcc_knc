# S3-03: boundary behavior of KNC unaligned and masked moves

Native execution is pending the lead. Host checks do not establish native safety.
This is a research probe, not an implementation of `movmisalign` or masked tails.

## Source and interpretation

Intel, *Xeon Phi Coprocessor Instruction Set Architecture Reference Manual*,
327364-001, 7 September 2012. The lead supplied the PDF and searchable text at
`.work/_shared/intel-327364-001-xeon-phi-isa.{pdf,txt}`.
All page numbers below are printed pages, not PDF viewer page indexes.
Chapter 6 identifies instruction sections by mnemonic rather than subsection number.

Section 2.1.3.2, pp.25–26, describes element masking and alignment according to
the memory operand's accessed size. Section 2.2.2, p.32, specifies UpConv operand
alignment before conversion/broadcast. An ordinary, unconverted vector move
therefore requires 64-byte alignment, even when only some lanes are enabled.
These rules do not make an ordinary aligned move into an unaligned instruction.

Section 4.5.2, p.62, says unpack loads access an entire 64-byte region.
Its printed address expression uses `address & 0x3F` where the surrounding
cache-line wording implies rounding DOWN to a 64-byte boundary. This document
uses that interpretation; it is not a claim that the printed expression is correct.
The instruction descriptions repeat the full-line warning, including masked forms.
Section 4.5.4, p.62, says stores update selected elements with the conversion's
element size; it does not grant unpack loads' full-line behavior to stores.

For an unpack/pack pair, the mask selects elements of a compacted stream.
Memory position is determined by the count of earlier enabled lanes, not simply
by the vector lane number. A suffix mask at a starting boundary does NOT move
the stream's first memory address past the guard. The probe models this rule.
For ordinary `vmovaps`/`vmovapd`, masking retains normal lane positions instead.

## Per-form manual references and predictions

`A` is the logical stream address. Low uses `A`; high always uses `A+64`.
`G` is the first byte of the ending guard; `S` is the first mapped byte.
No conversion, broadcast, zeroing mask, or non-temporal modifier is used.
All observations in this document are deliberately empty.

| Form | Chapter 6 section and printed pages | Fault-related statement and prediction | Observed |
| --- | --- | --- | --- |
| `vloadunpackld` | VLOADUNPACKLD, 361–363 | Element alignment; full-line read; page-fault address at line start. Mapped low line should succeed; guard low line should fault, including truncated masks. | |
| `vloadunpacklpd` | VLOADUNPACKLPD, 364–366 | Same low-line rule, 8-byte elements. | |
| `vloadunpacklps` | VLOADUNPACKLPS, 367–369 | Same low-line rule, 4-byte elements. | |
| `vloadunpacklq` | VLOADUNPACKLQ, 370–372 | Same low-line rule, 8-byte elements. | |
| `vloadunpackhd` | VLOADUNPACKHD, 349–351 | Full-line warning, but aligned high operand explicitly suppresses page faults. Unaligned guard high operand is expected to fault; aligned `A+64=G` should be a no-op. | |
| `vloadunpackhpd` | VLOADUNPACKHPD, 352–354 | Same high-line rule, 8-byte elements. | |
| `vloadunpackhps` | VLOADUNPACKHPS, 355–357 | Same high-line rule, 4-byte elements. | |
| `vloadunpackhq` | VLOADUNPACKHQ, 358–360 | Same high-line rule, 8-byte elements. | |
| `vpackstoreld` | VPACKSTORELD, 417–419 | Selected lanes pack consecutively into the low line; element alignment and page faults are listed. Only selected stream bytes may change. | |
| `vpackstorelpd` | VPACKSTORELPD, 420–422 | Same low-store rule, 8-byte elements. | |
| `vpackstorelps` | VPACKSTORELPS, 423–425 | Same low-store rule, 4-byte elements. | |
| `vpackstorelq` | VPACKSTORELQ, 426–428 | Same low-store rule, 8-byte elements. | |
| `vpackstorehd` | VPACKSTOREHD, 405–407 | Selected stream's high bytes only; aligned high operand explicitly suppresses page faults. `A+64=G` should perform no store and not fault. | |
| `vpackstorehpd` | VPACKSTOREHPD, 408–410 | Same high-store rule, 8-byte elements. | |
| `vpackstorehps` | VPACKSTOREHPS, 411–413 | Same high-store rule, 4-byte elements. | |
| `vpackstorehq` | VPACKSTOREHQ, 414–416 | Same high-store rule, 8-byte elements. | |
| `vmovaps` load | VMOVAPS, 379–381; UpConv table p.380 | Masked destination retains disabled lanes; pseudocode forms the memory source before applying the destination mask. Mapped aligned control should succeed; nonzero guard mask should fault. Empty-mask guard fault suppression remains an empirical question. | |
| `vmovaps` store | VMOVAPS, 379–381; DownConv table p.381 | Memory writes occur inside the enabled-lane condition. Expect no writes/fault for an empty guard mask; nonzero guard mask should fault. | |
| `vmovapd` load | VMOVAPD, 376–378 | Same aligned-load question for 8-byte lanes; exception table p.378. | |
| `vmovapd` store | VMOVAPD, 376–378 | Same aligned-store prediction for 8-byte lanes. | |

The high-instruction exception is specific: the descriptions on pp.349–350,
352–353, 355–356, 358, 405, 408, 411 and 414 explicitly discuss a 64-byte-aligned
high operand suppressing canonicity/page faults. It must not be generalized to
unaligned operands, low instructions, or ordinary aligned moves.

## Case table and boundary expectations

The lead's S3-03 answer replaces the impossible aligned vector spanning two
pages. An aligned 64-byte vector cannot straddle an ordinary page boundary.
The test uses mapped and guard aligned addresses, unaligned masked streams,
and one misaligned crossing load per type as an alignment-fault control.

The mapping is `[PROT_NONE page][read/write page][PROT_NONE page]`.
`e` is 4 bytes for `ps,d`, 8 for `pd,q`; `L=64/e`.
Offsets `o=0..63` are measured in ELEMENTS. Byte displacements are also printed
through `A`, relative to `S`. The extra crossing cases include wholly guarded
streams and therefore provide positive fault controls as well as partial cases.

| Printed case | Logical address / mask | Forms and count | Expected result | Observed |
| --- | --- | --- | --- | --- |
| `inside-start` | `A=S+o*e`, full mask, `o=0..63` | Pair load/store, all four types; 512 | No fault; load all lanes/store 64 bytes. | |
| `inside-end` | `A=G-64-o*e`, full mask, `o=0..63` | Pair load/store, all four types; 512 | No fault, including the aligned high no-op at `o=0`. | |
| `cross-start` | `A=S-o*e`, full mask, `o=0..63` | Pair load/store, all four types; 512 | `o=0` succeeds; other cases touch the preceding guard and should fault. | |
| `cross-end` | `A=G-64+o*e`, full mask, `o=0..63` | Pair load/store, all four types; 512 | `o=0` succeeds; other cases touch the ending guard and should fault. Earlier low stores may remain visible. | |
| `mask-start` | `A=S-o*e`, `o=1..L-1`; clear nominal guard lanes, or empty mask | Pair/low/high, load/store, all types; 528 | Nonempty suffix compacts back into the guard: low should fault. Isolated high tests the mapped line independently. Empty unpack-load mask may still access the low guard line; empty stores should not write. | |
| `mask-end` | `A=G-64+o*e`, `o=1..L-1`; clear nominal guard lanes, or empty mask | Pair/low/high, load/store, all types; 528 | Prefix stream ends at G. Low should succeed. High unpack's full-line warning predicts a guard fault despite no remaining logical elements; high store has no selected stream bytes and is expected not to write. Observe fault suppression directly. | |
| `high-end` | `A=G-64`, full mask; high operand is G | High alone, load/store, all types; 8 | No fault, no load lane/store byte transferred. | |
| `aligned-end` | `A=G-64`, full or empty mask | Aligned load/store, all types; 16 | No fault; full mask moves 64 bytes, empty moves none. | |
| `aligned-guard` | `A=G`, mask `1` or `0` | Aligned load/store, all types; 16 | Mask 1 faults; empty load suppression is unresolved; empty store should not fault or write. | |
| `misaligned` | `A=G-32`, full mask | Aligned load only, one per type; 4 | Alignment fault expected; distinguish it from a page fault by signal metadata. | |

Total: **3,148 cases**. The aligned controls use `vmovaps` for `ps,d` and
`vmovapd` for `pd,q`, preserving the same finite data bits. Integer pair cases
use the actual `d/q` unpack/pack instructions, not floating substitutes.

The full-mask pairs whose entire 64-byte payload is mapped are the evidence
needed for the ticket's ADR-0005 question. Masked prefix safety cannot be inferred
from those cases: an unaligned high unpack operand may reference the guard line.
Likewise, suffix masks are not a generic way to access a mapped starting tail,
because stream compaction changes the memory positions of the enabled lanes.

## Self-checking behavior and limits

Each case prints form, boundary group, element offset/size, stream address,
mask, fault/no-fault, numeric `si_code`, raw `si_addr`, completion phase,
transferred bytes, load lane bits, sentinel changes, and data-check status.
The header prints actual mapping addresses for interpreting `si_addr`.
The handler uses `SA_SIGINFO` and recovers with `sigsetjmp`/`siglongjmp`,
restoring the signal mask. SIGBUS is also recorded if delivered.
For SIGSEGV, retain the raw code/address: the lead requested distinguishing
`SI_KERNEL` alignment/#GP reports from `SEGV_ACCERR`/`SEGV_MAPERR` page faults.

Low and high instructions use separate inline assembly blocks with an aligned,
mapped load checkpoint between them. A pair proceeds to high only if low returns.
The isolated low/high cases ensure low faults cannot conceal high behavior.
High always receives `A+64`, including the standalone high boundary case.
The checkpoint/reload is an intentional measurement aid, not a proposed compiler
sequence or a performance measurement.

Loads begin with `0xd7` in every destination byte; mapped input bytes use 1..127.
After a high fault, reported load bytes/lanes describe the completed low checkpoint.
If the first load faults they are zero. The faulting load's architectural vector
state is not inspected, so no claim is made about its partially transferred lanes.
Phase 0 means no low checkpoint, phase 1 means low completed, phase 2 means
the entire requested form returned. For high-only faults phase remains 0.

Before each store the entire mapped page is `0xa5`. Source lanes have distinct,
finite normal IEEE bit patterns and no conversion is requested. The checker scans
the entire mapped page, including both sides of the intended stream range.
Any out-of-range change or incorrect payload byte fails. A returned store must
produce every intended byte. After a fault, a subset of correct intended bytes
is allowed and counted, because a pair is not an atomic transaction.
Guard pages remain protected throughout instruction execution.
Loads also check that the mapped source page was not modified.

Fault predictions are research expectations, not assertions that can hide an
unexpected observation. Native exit 0 means the observed data/sentinel checks
passed, not that all accesses were fault-free or that every prediction held.
Native exit 1 indicates a data/sentinel mismatch; exit 2 is setup/usage failure.
Every fault must still be reviewed in the output, including mapped controls.

T0 is in the same C file under `--self-test`, compiled with `HOST_LOGIC`.
It checks all type/direction/offset combinations, exact addresses, mask geometry,
empty masks, isolated halves, aligned guard controls, and the 3,148-case total.
Independent known answers check prefix/suffix compaction and aligned high no-op.
Sentinel negative controls inject overruns before/after the stream, wrong data,
missing writes, and valid partial writes. No KNC instruction exists in this build;
it rejects `--native`. No additional test file is required.

## Build and lead execution

The one-off preparation helper is staged outside git at
`.work/_shared/tmp/S3-03/prepare_s3_03.py`. From this worktree's root, run:

```text
python tools/run.py --name S3-03-t0 --inputs tests/regress/knc-unaligned-probe.c ../_shared/tmp/S3-03/prepare_s3_03.py -- python ../_shared/tmp/S3-03/prepare_s3_03.py --t0-only
python tools/run.py --name S3-03-build --inputs tests/regress/knc-unaligned-probe.c ../_shared/tmp/S3-03/prepare_s3_03.py -- python ../_shared/tmp/S3-03/prepare_s3_03.py --build-only
```

The helper uses shared Cygwin GCC for T0 and the shared GCC 16 `xgcc` for KNC,
with `-O2 -march=knc -fno-tree-vectorize -Wall -Wextra -Werror`.
Assembly/link uses `-Wa,--march=k1om`; generated assembly and the linked program
both go through `tools/knc_lint`. Dynamic linking uses the shared configured
sysroot. No compiler/build/sysroot is copied into this worktree.

Staged files are in `.work/_shared/tmp/S3-03/`, outside git:

- `knc-unaligned-probe.mic`: program for the card only.
- `batch.txt`: tab-separated program, JSON arguments, memory limit in MiB.
- `probe-host.exe`: T0 program for the host only.
- `probe.s`: generated KNC assembly used by the lint check.

The batch entry is `knc-unaligned-probe.mic`, `["--native"]`, `128`.
The lead runs that entry only through `tools/card_run`, with its memory policy
set to 128 MiB, retaining stdout and the runner's result JSON in the shared area.
Do not invoke the `.mic` program on the host. Preparation never contacts the card.

## Results for the lead to complete

| Result | Value |
| --- | --- |
| Host T0 | PASS: 3,148 cases and sentinel negative controls |
| GCC 16 build, K1OM assembly, assembly/program lint | PASS |
| Native runner result class / exit | |
| Native data/sentinel failures | |
| Full-mask pairs wholly inside mapped memory ever fault? | |
| Aligned high operand on guard ever faults? | |
| Empty aligned guard load/store faults? | |
| Masked prefix unpack high guard access faults? | |
| Suffix-mask observations | |
| Unexpected alignment / page-fault metadata | |
| Native output location | |
| Runner result JSON location | |
| Card minutes (copy `card_minutes` from runner result JSON) | |

Successful host logs are recorded on the ticket at submission. Card minutes and
native results remain empty until the lead actually executes the batch.

## Card results (lead, 2026-11-03)

Run by the lead through `tools/card_run` (job with `--native`, 128 MiB, 0.142 card minutes, boot
`e9bfb0ab` unchanged): 3,148 cases, 0 data or sentinel failures, exit 0. Fault counts by case:

| Case | Pair (ld+hd) | Low (ld) | High (hd) | Aligned |
| --- | --- | --- | --- | --- |
| `inside-start`, `inside-end` (o = 0..63) | no fault, all 64 offsets, all types | | | |
| `cross-start`, `cross-end` | o = 0 no fault; o = 1..63 SIGSEGV | | | |
| `mask-start` (guard lanes cleared) | SIGSEGV every case | SIGSEGV every case | no fault | |
| `mask-end` (guard lanes cleared) | SIGSEGV every case | no fault | SIGSEGV every case | |
| `high-end` (A = G-64, aligned) | | | no fault | |
| `aligned-end` (full or empty mask) | | | | no fault |
| `aligned-guard` (mask 1 or empty) | | | | SIGSEGV, loads and stores |
| `misaligned` aligned load | | | | SIGSEGV, `si_code=128` |

Answers to ADR-0005 question 1:

1. An unpack/pack half accesses its whole 64-byte line whenever its address is not 64-byte
   aligned, whatever the mask: clearing every lane that falls in an unmapped page does not stop the
   fault (`mask-start` for the low half, `mask-end` for the high half).
2. At a 64-byte-aligned address the high half is a no-op and touches no memory, even when the
   next page is unmapped (`high-end`, `inside-end` at o = 0).
3. Masks never suppress a page fault: aligned loads **and stores** with an empty mask fault on an
   unmapped page (`aligned-guard`). The design above predicted that an empty-mask store would not
   fault; it does.
4. A misaligned aligned load faults as SIGSEGV with `si_code=128` (a general-protection fault, not
   a page fault), so it is distinguishable.

So on KNC a masked vector access is safe only if every 64-byte line it names is mapped; masking
cannot be used to read or write past the end of an array.
