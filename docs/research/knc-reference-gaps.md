# KNC reference gaps: compiler, card runtime and broad optimization

S12-10, 2026-11-14. Phase 1 was accepted by the lead at `dcf5eaaa`;
phase 2 follows below. Part 1 records the local-only investigation before
that review. Part 2 records subsequent web research and document retrieval.
Code is unchanged; no compiler build, program test or card job was run.

**S12-13 follow-through (2026-11-14):** the stable R-number catalogue is now
[knc-references.md](knc-references.md); implementation/practice consequences
and ADR proposals are in [the digest](knc-digest-2026-11.md). Parts 1 and 2
remain the history of the investigation. Source-specific qualifications below
record additional configuration details found in the PDFs.

## Part 1 — What the existing evidence leaves unresolved

### Scope and evidence boundaries

The immediate tuning problem is explaining the cost of real, strict, serial
`-O2` programs. M4's primary comparison has one pinned worker; the compiler's
default density hint is four active threads per core. Whole-card bandwidth
and OpenMP improvements remain useful, but cannot substitute for that primary
comparison. [M4-DEFINITION](../M4-DEFINITION.md) and
[ADR-0015](../adr/0015-m4-scoring-and-measurement.md) retain the fixed 17 votes,
three resource settings, SQLite donor `-O3` exception, independent correctness
requirements and sealed held-out programs. No held-out artifacts were opened.

Evidence labels used here:

- **Local specification:** directly read in the existing Intel ISA text,
  document 327364-001, September 2012, at
  `.work/_shared/intel-327364-001-xeon-phi-isa.txt`; citations use printed pages.
- **Source:** implementation inspected read-only at shared GCC `knc` revision
  `619e14b479a952edff32e94f22573710d0b8ac17`. Paths beginning `gcc/`,
  `libgomp/` or `libgfortran/` below are relative to that repository. This is
  source behavior, not proof of the installed binary or native acceptance.
- **Reported measurement:** an existing research note or source comment reports
  a card result. It was not rerun or independently requalified here.
- **Reported document:** an existing note attributes a fact to an external
  document. Its original was not fetched or reverified in this phase.
- **Hypothesis:** the proposed explanation, importance or next measurement.
  No positive speedup is assigned to an untested change.

Project references were read at worktree revision
`0031ca337269501d839f4a3ef734056b37c93280`. The audit covered the relevant
sections of every existing `knc-*.md` note, grouped below. Earlier design
proposals and pending-result headings are historical evidence, not current
feature inventories.

| Reference group | What it contributes |
| --- | --- |
| [Microarchitecture](knc-microarch.md), [characterization](knc-characterization.md), [costs](knc-costs.md), [prefetch](knc-prefetch.md) | Hardware model, measured instruction families, subsequent corrections and implementation assumptions |
| [Optimization sources](knc-optimization-sources.md), [optimization gaps](knc-optimization-gaps.md), [best-practice review](knc-best-practice-review.md), [intrinsics sources](knc-intrinsics-sources.md) | Existing primary-source leads and limits of prior reviews; speculative gains are not carried forward |
| [Conversions](knc-conversions.md), [divide/sqrt](knc-div-sqrt.md), [gather/reduce](knc-gather-reduce.md), [masks](knc-masks.md) | Semantics, lowering costs, proof obligations and historically unresolved questions |
| [Register design](knc-register-design.md), [packed modes](knc-packed-modes.md), [unaligned probe](knc-unaligned-probe.md), [small matrices](knc-small-matrix.md) | ABI transfers, storage constraints, fault boundaries and examples where an initial performance diagnosis was wrong |
| [libgomp](knc-libgomp.md), [libstdc++](knc-libstdcxx.md), [libgcc](knc-libgcc-shared.md), [libgfortran](knc-libgfortran.md) | Runtime interfaces, deployment constraints and mixed x87/IMCI state |
| [Measurement](knc-measurement.md), [memory bandwidth](knc-memory-bandwidth.md), [emulator](knc-emulator.md) | Timing limits, recent bandwidth/GEMV results, and why host execution cannot establish KNC behavior |
| [ADR-0003](../adr/0003-fp-defaults-and-division.md), [0005](../adr/0005-knc-packed-vector-modes.md), [0008](../adr/0008-knc-data-movement.md), [0009](../adr/0009-knc-tuning-model.md) | FP, mode, data-movement and tuning contracts |
| [ADR-0010](../adr/0010-knc-measurement-protocol.md), [0012](../adr/0012-knc-malloc-arena-default.md), [0014](../adr/0014-knc-vector-abi-and-vmath-binding.md), [0015](../adr/0015-m4-scoring-and-measurement.md) | Measurement, allocation, vector ABI and whole-program qualification |
| [M4 baseline](m4-baseline.md), [code census](m4-code-census.md) | Qualified development-program exposure and the limits of static instruction counts |

### Corrections before ranking missing knowledge

These are existing answers or discrepancies to reconcile, not reasons to
repeat old experiments or implement already-present features.

| Earlier statement | Better-supported position now |
| --- | --- |
| Most vectors cost four cycles, and four siblings hide all relevant latency | Characterization reports 4-cycle arithmetic, 6-cycle permute/swizzle/reciprocal and 7-cycle double-to-int dependencies, with longer memory chains. Four-way issue does not make every dependency free. Raw latency, per-thread ticks and core reciprocal throughput must remain distinct. |
| A three-cycle AGI needs three intervening instructions | The local address-dependence experiment found about one extra tick for the adjacent case at one thread. `x86-tune-sched.cc` adds one to an address dependence before converting to thread issue opportunities. The broad vendor rule is not an instruction-count recipe. |
| Streaming stores are slow, or NGO is still untested | C1 measured NGO, including completion, and later compiler work uses it. The completed-worker estimate was 204.5 GB/s, distinct from the 226.1 worker-median aggregate. Sweep 2's best write result is only 169.74 GB/s under a different benchmark; the discrepancy is still unexplained. |
| Two-level prefetch is missing; four simultaneous prefetches describe the hardware | The compiler has near/far distances 16/32 lines and a stream/density footprint rule. Its 1024 prefetch slots are pass bookkeeping, not hardware queue capacity. |
| Huge pages cannot be allocated on the card | The later bandwidth sweep reports actual huge-page allocation in 48 configurations. That does not establish transparent promotion for ordinary M4 allocations. Old `nr_hugepages=0` snapshots cannot describe every later run. |
| L2's compiler setting must still be 512 KiB | Physical L2 remains 512 KiB in the references; the inspected cost table exposes 256 KiB to loop heuristics to reflect small-page TLB reach. This is a policy approximation, not a changed cache capacity. |
| A tree barrier is necessarily faster; libgomp still spins about 3 ms | `bar.h` keeps the grouped barrier behind `GOMP_KNC_GROUP_BARRIER`; its comment reports a 1.5–1.7x slowdown against the Linux barrier. `card.h` now sets delay 128 and a 200 ms default. C11's synthetic tree result does not establish real libgomp performance. |
| libgomp should only document arena caps, or 64 arenas always wins | ADR-0012 supersedes the old recommendation. The implementation derives a cap, with user override. Its source comment reports a malloc-heavy case faster near 169 arenas than 60–64. Workload and address-space limits decide the tradeoff. |
| FP64 vector divide/sqrt is absent because the S5 note leaves proofs open | The inspected source contains FP64 expansions and cost hooks, including masked sqrt; its cost constants are 34/35 instructions for division/sqrt. The old note is not a current implementation inventory. This inspection does not certify their proofs or native results. |
| KNC vector traps and MXCSR bit 21 are undocumented | The existing ISA already defines sticky flags, no vector FP traps, mandatory DUE bit 21 and reserved bit 20: §2.4 p.39, §4.1 pp.55–56, §B.3 p.660. `fpu-knc.h` implements a KNC policy. Remaining issues are mixed-domain behavior and conflicting underflow claims, not discovery of those fields. |
| A large code count, stack-reference count or sampled load PC proves a bottleneck | The M4 census explicitly cannot prove spills, alias rejection, misses, taken-branch frequency or removable time. The baseline separates several actual bridges from stack locals and call saves. |

The ISA is principally a semantics/encoding reference. Its relevant sections
do not supply a complete instruction timing or U/V pairing table, branch
predictor specification, or OS scheduling policy. A missing performance fact
should not be inferred from an instruction's presence in that manual.

### Ranked top ten for the lead

This ranks the value of resolving uncertainty for M4 and then runtime work,
not predicted percentage speedup. G01 and G05 share some EP exposure and
must not receive additive benefit credit. Correctness constraints in G13
apply before any affected FP optimization regardless of its list position.

1. **G01 — Scalar FP, conversions and ABI bridges:** separate their costs in EP/IS; the current generic bridge and sqrt estimates cannot identify removable strict-code time.
2. **G02 — Serial-density scheduling and U/V pairing:** establish operand-specific dependencies and pairing when one thread runs under a default four-thread model.
3. **G03 — Ordered indexed loads and gather/scatter:** distinguish CG's scalar recurrence from address/cache stalls; endpoint gather measurements do not price real sparse access.
4. **G04 — Prefetch, stores and locality in real loops:** determine useful coverage and issue/address cost in scalar updates and streams before changing broad defaults.
5. **G05 — Actual libm/libc paths and quality:** identify math-body versus caller costs, string-operation crossovers and the installed runtime's semantics.
6. **G06 — Trustworthy attribution and KNC PMU access:** obtain event definitions and installed-interface facts; repair the evidence gap without treating lost OpenMP samples as wait time.
7. **G07 — Decoder, branch prediction and code footprint:** determine pairing/fetch boundaries and control-flow penalties behind generic branch and layout heuristics.
8. **G08 — TLB, page mode and cache mapping:** connect actual allocation/page size to the 256 KiB heuristic and distinguish translation from cache-set conflicts.
9. **G09 — MPSS scheduling, affinity and libgomp waits:** establish migration, wakeup and imbalance costs with the implemented delay/spin/barrier policy.
10. **G10 — Allocation, first touch and memory limits:** measure realistic allocation lifetimes and page-zeroing cost; arena reservations are neither RSS nor a universal performance rule.

### A. GCC-KNC code generation gaps

#### G01 — Scalar FP arithmetic, conversions and inter-register transfers

**Known/assumed.** The ABI transports scalar FP in zmm lane zero while scalar
arithmetic uses x87. The characterization gives x87 add/mul throughput of
1/2 core cycles and unpipelined divide near 38; it does not give a complete
`fsqrt`, `fyl2x`, integer-conversion, control-word or call-boundary cost map.
The current cost table estimates sqrt as divide, and a dependent bridge from
the measured 12-tick spill/reload family. GPR↔zmm, x87↔zmm, different widths,
misalignment, store forwarding and a live value across a call need not cost
the same. The ABI itself does not permit inventing a direct register transfer.

**Used in.** `knc_processor_costs`, `ix86_knc_stmt_cost`,
`ix86_knc_reload_bridge`/`ix86_knc_reload_memory_bridge_p`, IMCI move patterns,
register allocation, vector reduction epilogues and scalar call lowering.
[Register design](knc-register-design.md), [conversions §1.2](knc-conversions.md)
and the M4 baseline describe the paths.

**Importance.** The baseline's normalized exposure is 51.174 s in EP's
transform/call site and 5.169 s in IS randlc; neither is a measured transfer
budget. EP also has 36.794 s in the separate log path (G05). Repeated x87
control-word conversions are an identifiable candidate. Replacing x87 with
lane-zero FP changes precision/exception questions as well as speed; preserve
the strict contract and consult G13.

**Resolution.** A KNC timing guide and K1OM ABI supplement can constrain legal
forms and expected dependencies. Measurement must separate each transfer
direction/width, dependent versus independent operations, control-word work,
math body and call-save cost. Use matched no-call and call-containing paths
with ordinary and exceptional operands; then a general compiler change needs
whole-program before/after evidence. Do not attribute the entire log budget
to deleting bridges.

#### G02 — Complete scheduling model, pairing restrictions and active density

**Known/assumed.** Local measurements establish simple vector+scalar pairing,
scalar/mask pairing, no vector+vector pair, and the single-thread two-cycle
issue interval. They do not establish the full ordered pairing matrix for
load+load, load+store, integer memory RMW, branches, mask consumers, prefixes,
push/pop, integer multiply/divide, or x87/vector overlap. Smart round robin
under stalls, unequal siblings, delayed threads and three active contexts is
less characterized than steady independent chains. Equal occupancy cannot
be presumed throughout a real loop.

**Used in.** `gcc/config/i386/knc.md`, `ix86_issue_rate` and
`ix86_adjust_cost` in `x86-tune-sched.cc`, plus `knc_processor_costs` and
`ix86_knc_small_loop_unroll`. Dependence costs divide by `max(2,density)`;
`i386.opt` defaults density to four. Scalar memory instructions can reserve
either U or V; the DFA lacks a separate shared L1-access resource. Vector
memory forms receive a broad 12-cycle reservation, while the plain load-chain
measurement is about 3. These abstractions need operand/path validation;
source inspection alone does not prove a scheduling defect.

**Importance.** High for M4's single worker, especially CG/ludcmp and any
memory bridge. A 6- or 7-cycle dependence is not interchangeable with a
4-cycle one. Unmeasured integer divide and x87 sqrt costs still use estimates.
No percentage improvement follows just from changing the density hint.

**Resolution.** Seek the complete KNC pairing, forwarding, port and decode
rules in the SSDG/optimization guide and microbenchmark papers. Measure only
missing hot instruction classes, both orderings, dependencies and alignment,
at one/two/four siblings; use controlled sibling stalls to test the issue
model. Three-thread observations need the ADR-0010 instability issue resolved
before qualifying a tuning comparison. M4's frozen flag list is unchanged;
an experimental density override would be a labelled diagnostic.

#### G03 — Indexed access, gather/scatter and strict sparse reductions

**Known/assumed.** ADR-0008 already records native answers for masked-lane
fault suppression, scaling, duplicate scatter indices and restart. The
missing knowledge is performance: line/page distribution, duplicate lanes,
mask population, cache level, completion-loop iterations and scatter versus
gather. `ix86_knc_stmt_cost` interpolates between 7 and 127 core-throughput
cycles with `7*lines + lines*(lines-1)/16`, assumes a favorable stride start,
and uses the same estimate for scatter. Unknown indices assume one line per
lane. `knc.md` reserves an optimistic seven-slot retry loop. Intermediate
cases and gather-prefetch/completion-unroll tradeoffs are not established.

**Used in.** Gather/scatter optabs and builtin hooks, `imci.md` retry loops,
vectorizer costs and unknown-alignment masked tails. See
[gather/reduce §§1, 2, 4](knc-gather-reduce.md).

**Importance.** CG's 24.547 s normalized hot exposure is an ordered scalar
x87 indexed reduction, with no inner-loop spill. Gather instructions in
other paths do not explain it. A gather or reordered sum is not automatically
a legal or profitable replacement. Sparse C++ and tails give later reach.

**Resolution.** Documents can specify gather progress/prefetch mechanisms;
measurement must distinguish the indexed address chain, loaded-data latency
and ordered FP recurrence. Compare contiguous, cache-resident and
memory-resident controls without changing accumulation order. A bounded
line-count/mask-density gather and separate scatter matrix can calibrate the
cost interpolation. Reuse ADR-0008's resolved correctness facts.

#### G04 — Prefetch, folded memory operands, stores and locality

**Known/assumed.** The implemented near/far rule is 16/32 lines, halving near
distance when streams×density×distance exceeds a quarter of L1. Its basis is
limited stream/stencil/row experiments, not every trip count, sparse index
distribution or scalar loop. `vprefetch0` paired freely in a hot-target test;
`vprefetch1` cost about 2.25 core cycles at multiple siblings. Missed targets,
page boundaries, exclusive hints, hardware-prefetch cooperation and queue
competition remain less known. The DFA classifies both hints as scalar.
The ISA p.641 already establishes that an L1 hit can discard the hint.

**Used in.** `ix86_knc_prefetch_distances`, `ix86_knc_vectorizer_params`,
`tree-ssa-loop-prefetch.cc`, `imci.md` prefetch/folded-memory patterns and
streaming-store selection/fencing. Read hints are used even for written
streams. The code already folds useful broadcast/FMA forms; the small-matrix
note documents why a separate broadcast fix was not merged.

**Importance.** Ludcmp initialization exposes 10.985 s and its two ordered
factorization regions 6.849 s; those include arithmetic/address work as well
as locality. STREAM's three vector loops expose 4.289 s. Prefetch sites also
occur in scalar database code, but static counts cannot show usefulness.
The bandwidth sweep's 120-thread triad collapse and GEMV's divergent hint
response show why one global bandwidth recipe is unsafe.

**Resolution.** Documents should clarify stream detection, replacement,
software-trigger policy, RFO/non-temporal paths and queue allocation. Matched
measurements must hold dispatch/loop shape constant when removing a hint,
vary consume time and reuse, and include actual instruction/address overhead.
Test store reuse and publication cost, not only cold write throughput. For
M4, confirm legal dependence-preserving locality changes on the affected
whole programs and controls; neither initialization nor output may disappear.

#### G07 — Front end, loop buffering and branch prediction

**Known/assumed.** Existing notes report a 16-byte decode path, two-cycle
decoder, two ready bundles per context, prefix penalties, 32 KiB L1I and
32 small-page iTLB entries (SSDG §§2.1.1, 2.1.4–5, pp.16–22, reported).
We lack exact bundle capacity/use, instruction-boundary pairing restrictions,
branch target/refill costs, BTB/direction predictor organization, history
sharing, indirect-target and return behavior. The ready buffer is not proof
of a modern decoded-uop cache or an unlimited loop buffer.

**Used in.** Generic branch costs retained in `knc_processor_costs`, scalar
if-conversion without CMOV, unroll/inline decisions, and
`ix86_knc_tune_features`. Functions align to 64 bytes; tight-loop alignment
was disabled after measured executed-padding regressions. Many scalar tune
flags still retain generic values for lack of evidence.

**Importance.** C10's roughly 5 extra ticks for random branches at one thread
does not directly measure a 10-cycle misprediction: that interpretation
assumes half the branches miss. Predictor accuracy and front-end effects are
unseparated. SQLite's 43,271-byte VM function and zlib's control-heavy code
are candidates, but their low-count profiles do not quantify a bottleneck.
Code growth in all 14 census executables is a reason to inspect, not a
measured cache penalty.

**Resolution.** Seek branch/fetch/loop-buffer details and errata, then measure
controlled instruction-byte lengths, alignment, predictable/unpredictable
direct branches, indirect targets and returns. PMU misprediction/refill
events, if qualified, separate accuracy from penalty. Keep the already
measured padding regression distinct from an assumed predictor limitation.

#### G08 — TLBs, page sizes and cache-bank/set conflicts

**Known/assumed.** The corrected C4 experiment supports a 64-small-page
first-level data-TLB reach per core and about 29 extra ticks beyond it at
one thread. Its first version accidentally measured a same-offset L1-set
conflict. Reported SSDG facts include eight 2 MiB data entries, an L2
translation structure used as a PDE cache for small pages, and small-page
instruction translation. Missing facts include mixed-page replacement,
sibling sharing under asymmetric access, page-walk concurrency, actual
large-page benefit and the interaction with cache indexing/banks.

**Used in.** The 256 KiB effective L2 cost setting, prefetch/blocking and
alignment advice, allocators and Fortran allocation. Ordinary M4 allocation
must not be credited with the explicit hugetlbfs behavior of the bandwidth
experiment. A fixed byte tile is only an approximation to pages touched by
strided or many-stream data.

**Importance.** Potentially significant for sparse/strided working sets and
multiple siblings; no supported universal huge-page gain. Later GEMV tests
reported little benefit for those kernels, despite actual huge pages.
Physical coloring is unproven. ADR-0010 amendment 2 specifically withdrew
the initial attribution of its large cross-launch regime change to physical
page placement; that discarded explanation must not be revived as fact.

**Resolution.** Recover the SSDG translation and cache details and the
matching MPSS HugeTLB/THP implementation/configuration. Measure page count
with distributed within-page offsets, verify actual allocation, and separate
first-fault, steady translation and cache residency. A cache-address or
controller hash claim needs physical-address evidence; virtual offsets alone
do not supply it. No kernel setting change is part of this ticket.

#### G12 — Masks, swizzles, conversions and partial-vector costs

**Known/assumed.** The ISA describes merge masking, k0's special role,
destructive mask operations, swizzle granularity and conversion footprint.
ADR-0005/0008 and the unaligned probe resolve important fault questions.
Standalone swizzles/permutes have measured dependencies, but an attached
swizzle is often priced as free work within an arithmetic instruction.
Mask production-to-consumption, merge-destination dependencies, sparse masks,
mixed-width pack/unpack, carry-based V8DI operations and tail construction
are not fully calibrated. Mask spills through a GPR still compete for
scalar work; pairing does not prove they are always free.

**Used in.** `ix86_knc_stmt_cost`, permute/reduction lowering, `imci.md`,
`knc.md`, mask allocation and partial-vector profitability. FP reassociation
requires its existing permission; a cheaper tree cannot replace a strict
fold. Byte/word transport is not general byte/word arithmetic support.

**Importance.** C6 shows valuable masked-tail crossovers for one add kernel;
it does not settle every operation or tiny trip count. This matters for SLP,
mixed formats and later packed-weight workloads; M4's short-loop dynamic
exposure remains weakly resolved. The old 25%-lane-use rejection proposal
was not a valid explanation for mat8.

**Resolution.** Use instruction references for semantics and a timing guide
for data paths; measure dependent producer/consumer pairs, folded versus
standalone swizzles and operation-specific tails. Keep memory footprints and
guard-page correctness intact. No new intrinsic inventory or vendor header
reading is needed to answer the cost question.

#### G13 — Strict FP environment and exceptional-path qualification

**Known/assumed.** Existing ISA §§4.1–4.2 describes vector sticky flags,
DAZ/FZ and gradual results when FZ is clear, without vector traps. The
best-practice review corrects the blanket claim that IMCI always flushes
subnormals. However, current `libgfortran/config/fpu-knc.h` still comments
that observed underflow results flush regardless of FTZ and reports no
mixed-domain underflow control. Input subnormals and underflowed results are
different tests; a source comment alone cannot resolve this discrepancy.
Characterization C13/C14 still contain empty result tables for scalar
misalignment and subnormal performance in the supplied note.

**Used in.** Scalar-to-vector eligibility, divide/sqrt expansions and costs,
`libgcc` soft-fp, Fortran IEEE operations, libc fenv and vector math calls.
ADR-0014's vector-library contract includes about-one-ulp RN targets and
errno eligibility; it is not a proof of all rounding modes or equivalence to
x87 excess precision. The current FP64 expansions remove the old feature
absence, but instruction counts do not price dependency chains, lane-sparse
exceptional cases or fallback frequency.

**Importance.** Correctness prerequisite for G01/G05 and any new FP default.
No implicit FTZ, reassociation, contraction change or weakened oracle is a
performance remedy. The old open proof text must be reconciled with the
implemented algorithm and its existing qualification before proposing new
proof work. An x87 result can be double-rounded and is not a general exact
FP64 reference.

**Resolution.** The local ISA already closes register-field/trap-definition
questions. MPSS/glibc sources, FP notes and stepping errata should explain
state initialization/save/restore and discrepancies. Retrieve existing test
results first; only missing cases need native all-mode/fenv and boundary
measurements, separating input denormals from tiny outputs and special-path
cost from ordinary throughput. A document cannot replace algorithm-specific
proof or native validation.

### B. Card OS and runtime gaps

#### G09 — MPSS scheduling, affinity, waits and barriers

**Known/assumed.** The historical card topology is known, and the current
libgomp affinity code reads topology, intersects the inherited mask, excludes
the OS core when possible and uses spread defaults. Source presence does not
establish every nested/oversubscribed application's actual placement. We lack
a matched MPSS kernel/configuration account of load balancing, migrations,
interrupt/daemon placement, time slicing, wakeup latency and vector-state
switch overhead. Reserving a compute mask does not remove all OS work.

**Used in.** `libgomp/config/linux/knc/{affinity.c,card.h,futex.h,spincount.h}`,
the default Linux barrier, optional grouped barrier and flat pool dock;
kernel scheduler/futex paths. `delay 128` and 200 ms spin are implemented.
ISA DELAY p.628 permits interrupt-related early exit; its operand is not a
guarantee of an exact wall-time sleep.

**Importance.** High for the OpenMP panel and later parallel applications;
it cannot directly improve M4's serial vote through a faster OpenMP barrier.
The real grouped-barrier slowdown reverses the inference from the synthetic
C11 tree. OpenMP profile cadence failure prevents assigning removable wait
seconds. Long spin can help repeated regions but has different costs with
oversubscription, long serial gaps and competing work.

**Resolution.** Obtain the exact MPSS kernel patches/configuration and runtime
guidance. Measure actual affinity/migration and scheduling/wakeup intervals,
then barrier, dock, imbalance and useful-worker time separately at relevant
densities. Use balanced and skewed arrivals and several serial-gap lengths.
Do not compare with Intel's runtime defaults as though runtime algorithms
and workloads were identical, or enable the grouped barrier on theory alone.

#### G10 — malloc, first touch, page zeroing and memory budgets

**Known/assumed.** Arena reservations and thread stacks explain historical
ENOMEM under `RLIMIT_AS`; reservation bytes are not resident bytes. Current
`gomp_knc_arena_cap` uses finite address-space/strict-commit limits, a 512 MiB
reserve and an eight-arena floor (bounded by CPU count). With no such limit
it chooses one arena per allowed CPU. This differs from ADR-0012's proposed
unlimited-case MemTotal share and deserves source/result reconciliation,
not an unrequested policy edit. Neither formulation proves all application
heaps fit or that the highest feasible arena count is fastest.

**Used in.** libgomp startup's allocator policy and verbose reporting,
glibc 2.21 allocation/mmap thresholds, pthread stacks, Fortran allocation and
fresh-process M4 initialization. Non-OpenMP programs are outside the libgomp
arena override but still pay libc allocation, page faults and zeroing.

**Importance.** Potentially high for allocation-heavy parallel work and
short whole programs; no qualified M4 allocation-removal budget exists.
PolyBench's expensive mathematical initialization is not evidence that
malloc itself dominates. Reusing allocations across scored fresh processes
would change the experiment.

**Resolution.** Read the installed MPSS glibc allocator patches and kernel
fault/zeroing/huge-page paths. Measure allocation lifetime and size mixes,
cross-thread frees, address space, RSS, faults and time separately under the
actual limits. Include first touch and teardown, compare serial versus
parallel initialization without changing work, and preserve user settings.
Recover the existing arena sweep before commissioning another one.

#### G05 — glibc/libm and language-runtime quality

**Known/assumed.** EP's log path uses an internal x87 helper in the sysroot
disassembly; STREAM samples an aligned scalar libc copy helper. The baseline
explicitly makes system-library attribution conditional on the mapped card
library matching that sysroot. It does not have caller stacks for the copy.
Generic-C or x87 implementation is not proof of poor accuracy or a specific
speed deficit. Version strings/symbol availability do not describe vendor
patches, actual dispatch, exceptional inputs or all ABI behavior.

**Used in.** Scalar math libcalls, `knc_stringops` (currently libcall at all
sizes), `ix86_knc_veclibabi`, loader/runtime setup, and C++/Fortran helpers.
The libstdc++ note documents old-kernel fallbacks, pthread linkage, non-lock-free
16-byte atomics and clock behavior. Those mechanisms have costs independent
of vector arithmetic.

**Importance.** EP log's 36.794 s and STREAM copy's 2.823 s normalized exposure
are concrete investigation targets, not compiler-removable totals. Existing
runtime revisions must be matched to the frozen M4 executable; inspecting
the current source does not replace that identity. Large library replacement
projects are outside M4's bounded repair scope.

**Resolution.** Obtain matching open MPSS glibc/libm source and release notes,
plus public ICC/MKL behavior notes where relevant, without reading libimf,
SVML or ICC headers. Establish actual mapped objects and source correspondence
using existing deployment records and Git revisions, without hash manifests.
Measure size/alignment/reuse crossovers for memcpy/memset and representative
math input classes, with independent accuracy/fenv checks. Separate caller
bridges (G01) from the library body and keep errno eligibility explicit.

#### G11 — Ring, directory, GDDR5 and memory concurrency

**Known/assumed.** The references establish distributed private L2s, directory
traffic and eight two-channel memory controllers. The model-specific raw
interface peak is 352 decimal GB/s; it is not attainable payload throughput
for every access mix. Existing sources variously report about 38 outstanding
requests/core, eight L1 misses, sixteen hardware streams/about 24 prefetched
lines, and 56–60 L2 MSHRs on preproduction hardware. These describe different
resources/systems and cannot be substituted for each other.

**Used in.** Prefetch concurrency assumptions, bandwidth forecasts, locality
and false-sharing policy, density selection, allocator placement and runtime
synchronization. Directory/channel hashes, queue partitions, ECC traffic,
refresh, read/write turnaround and load-dependent latency remain incomplete.
C11's similar near/far measurements do not prove that physical ring distance
never matters; logical CPU proximity is not a directory-address mapping.

**Importance.** High for later bandwidth/parallel work, conditional for serial
M4. Sweep 2's approximately halved triad rate at 120 versus 60 workers is
unexplained by its measured small timing overhead. GEMV density depends on
format and instruction work. No measured hardware ceiling has been isolated;
stencil logical bytes cannot be used as channel bytes.

**Resolution.** SSDG/register/uncore references and the cited McCalpin/Fang
measurements should establish resource definitions and system differences.
Then use matched access mixes, loaded latency and verified per-channel
read/write counters (G06) to distinguish issue limits, queues and traffic.
Offsets require fresh-mapping controls. Existing results do not authorize
ECC, clocks, controller-register or kernel changes, and their possible gains
must not be multiplied into an M4 forecast.

#### G14 — Context switching, atomics and non-OpenMP synchronization

**Known/assumed.** ISA §4.7 p.66 explains software handling of vector/mask
state and the device-not-available mechanism; it does not specify MPSS's
actual eager/lazy context policy, signal frames or their costs. The runtime
notes establish important interface/source facts, but do not supply a full
native cost matrix for mutex/futex, TLS, cancellation, signal delivery,
unwinding or 16-byte lock-based atomics. C++ `hardware_concurrency` is not
the inherited affinity allocation.

**Used in.** MPSS scheduler/signal paths, `libgcc` unwinder, glibc pthreads,
`libstdc++` synchronization and `libatomic` fallbacks. This also affects the
reliability and perturbation of profiling (G06).

**Importance.** Correctness when adding runtime/compiler features, and later
threaded C++ performance. There is no qualified M4 exposure supporting a new
general runtime optimization project here.

**Resolution.** Match kernel/glibc source and K1OM ABI documentation to the
deployed stack; retrieve existing cross-DSO and signal test results first.
Only remaining behavior/cost questions need contention, signal or context
switch probes, preserving live zmm/k/x87 state. Do not infer card execution
from host tests or assume ordinary x86 XSAVE/SSE facilities exist.

#### G15 — SCIF and transfer/runtime interference

**Known/assumed.** The bandwidth note points to the MPSS guide's SCIF
huge-page setting (§9.3.6 p.128, a later edition). That controls a transfer
path; it is not evidence that native allocations transparently use huge
pages. Local `tools/card_dma.py` implements receiver-pull synchronous RMA
with explicit completion/lifetime handling. The precise deployed driver's
registration/pinning, DMA-versus-copy thresholds, ordering, teardown,
page-size use and CPU/IRQ cost need matching documentation/source.

**Used in.** SCIF transport helpers and card staging, host/card pinned memory,
and possible ring/memory interference with concurrent native work. It is
not an instruction-selection rule.

**Importance.** Useful for reliable transfers and later integrated workloads.
M4 explicitly excludes host staging and output transfer from scored time;
there is no direct primary speedup credit. Transfer interference can still
invalidate or contaminate a compute measurement.

**Resolution.** Locate the matching MPSS SCIF API/driver documentation and
open sources; distinguish API completion from observed DMA completion and
resource release. Measurements must separate registration, transfer and
completion at several sizes/page modes and report CPU use. Compute/DMA
interference requires a separately coordinated experiment, never overlap
with an ordinary qualification window.

### C. What broad optimization still lacks

#### G06 — Measurement access and trustworthy attribution

**Known/assumed.** Missing `perf` on the card does not prove that
`perf_event_open` or every PMU path is unusable. The existing bibliography
identifies Intel PMU manual 327357-001, but reports an unavailable attachment.
We lack confirmed KNC event encodings/units/errata, core-versus-thread scope,
counter multiplexing behavior, and a usable deployed GBOX/FBOX interface.
Generic Xeon or KNL events are not substitutes. TSC invariance/cross-core
synchrony is also unproven; RAW and RDTSC calibration shared the TSC
clocksource, so their agreement was not an independent oscillator check.

**Used in.** Timing/attribution and acceptance of changes to all compiler and
runtime costs; vector utilization, cache, branch and bandwidth diagnosis.
M4 uses the existing launch-to-exit wall clock, not summed worker times.

**Importance.** Serial profiling provides useful bounded CPU exposure for
some programs, not exact stall fractions. OpenMP delivery lost 96.5–97.5%
of nominal cadence and cannot quantify waiting. Cholesky failed the overhead
gate; several short programs have fewer than 300 PCs; serial MG remains
invalid in the supplied baseline and HPCG has no qualified hot profile.
Donor/restricted-profile sampling was waived, so their composition cannot
be inferred from full-7120 samples. These are specific evidence limits,
not permission to expand the profiler project without a bounded need.

**Resolution.** Recover the PMU manual and MPSS PMU/kernel registration source,
then inventory the actual available unprivileged interfaces and exact failure
reasons. Event definitions alone do not establish access. Calibrate counters
against known work and measure recorder perturbation; retain unknown PCs,
system time and unsampled boundaries. If PMU access remains unavailable,
use narrowly scoped paired diagnostics rather than manufacturing miss or
wait counts from PCs. Documents can close interface knowledge; installed
access and unbiased sampling require a lead-run measurement.

#### G16 — Causal compiler decisions, legality and transfer across code styles

**Known/assumed.** The census is a site-count inventory. Original
optimization-decision dumps were not captured for the baseline. We cannot
tell from a scalar loop alone whether strict dependence, aliasing, alignment,
unsupported modes, cost or pass order blocked a transformation. Stack
references do not establish register-pressure spills; a load need not be
redundant. Dense initialization, indexed reduction, branch-heavy integer
work and runtime setup require different explanations.

**Used in.** Selection among scheduling, IV/address costs, reuse, scalar
replacement, vectorization, unroll, inlining and optional PGO. M4 requires
general mechanisms selected from development programs and bounded to the
approved themes, rather than benchmark-name or dimension special cases.

**Importance.** The baseline's three proof candidates expose 128.669 s across
disjoint regions, but proven removable time is zero. Its 11.70–21.44 s
scenario assumes local gains; it is not a forecast or a median-score gain.
Eight PolyBench votes and limited abstraction-heavy C++/integer evidence
bound any generality claim. Improving the largest absolute-time program
alone need not move a 17-program median.

**Resolution.** Hardware documents constrain the mechanisms; only preserved
compiler decisions/RTL, verified dependence reasoning and controlled A/B
changes explain why a real program improves. Correlate the already-qualified
regions with the relevant passes, then test affected programs and two
controls across all required profiles. Do not infer a hot alias problem
from static counts or make a strict reduction associative. Keep source,
initialization, output and fresh-process boundaries fixed. Held-out programs
stay sealed; MPI, LLM decode and wider corpora remain later evidence.

### Document search priorities after the phase boundary

These are search targets already identified by the local material, not newly
verified URLs or downloaded sources. Part 2 will record exact edition,
author/year, URL, local file, gap IDs and page/section facts, distinguishing
directly verified facts from secondhand reports.

| Priority source family | Existing pointer and what to resolve |
| --- | --- |
| KNC SSDG and optimization/software developer guide | `knc-optimization-sources.md` §§1–2 gives SSDG §§2.1.1–5 and pp.16–22. The bandwidth bibliography identifies revision 2.03/document 488596; the earlier review did not establish its edition. Recover original editions and complete pairing/frontend/TLB/prefetch detail (G02/G04/G07/G08). |
| PMU/uncore guide and x100 registers | PMU 327357-001 is the unresolved download in the bandwidth bibliography; registers 330991-001 is cited by the microarchitecture note. Need event definitions, errata and accessible interfaces, not copied register tables (G06/G11). |
| Matching MPSS kernel, glibc and runtime documentation/source | Existing notes identify MPSS 3.7, kernel 2.6.38 and glibc 2.21; verify patch/version correspondence before applying later guides. Scheduling, fenv, HugeTLB/THP, allocator and SCIF implementation are the targets (G05/G08–G10/G13–G15). |
| Measured microarchitecture papers and lab material | Local bandwidth bibliography names Zhenman Fang et al., TACO 11(4), article 55, Table V p.55:19/§6; Jianbin Fang et al., ICPE 2014 pp.137ff; McCalpin IXPUG 2014 slides 23–28 and address-mapping experiments. Separate preproduction hardware and different traffic metrics (G02/G04/G08/G11). |
| Intel/Klemm, PRACE, TACC/Colfax/LRZ/Jülich guidance and theses | Recover precise configurations and measurements behind pairing, page, placement and runtime advice. Tian et al., IPDPSW 2013 §§III–VI and PRACE v2.0 are already reported sources; they do not prove our workload's gains (G03/G04/G09/G12/G16). |
| K1OM ABI and public compiler/math release notes | Seek scalar/vector calling convention and FP behavior/cost evidence. The ICC guide GUID pointers in the best-practice/intrinsics notes are permissible interface references; they do not authorize vendor header, SVML, libimf, ISPC-code or Intrinsics Guide XML access (G01/G05/G13/G14). |

This was the phase-1 stopping point. The lead accepted the analysis and
authorized phase 2, prioritizing G01 for S12-06, G03 for S12-07, G02/G08
for S12-08, then G06 and G04. The experiments above remain closure criteria,
not scheduled card jobs or new implementation tickets.


## Part 2 — Retrieved evidence and remaining measurements

Research date: 2026-11-14. Local filenames below are relative to
`.work/_shared/knc-refs/`, outside git and this disposable worktree.
The 22 PDFs, two saved web pages and eight small source files are accompanied
by PDF text extracts. Temporary PDF inspection tools/images also remain in
this shared directory because cleanup was blocked by command policy.
Total directory usage is 102,319,508 bytes (about 98 MiB), below the 2 GB limit.
References use printed pages unless marked PDF page or slide. No vendor prose, examples or code is reproduced here.

**Verified (V)** means read in the identified source, including a paper's own
experiment. It does **not** mean reproduced on our card. **Reported (R)**
means a secondhand reference whose underlying document was not recovered.
**Inference (I)** identifies a proposed consequence for GCC-KNC. Production
model names do not establish stepping, firmware or correspondence with our
7120. Source versions do not establish installed binary identity.

### Facts for S12-06/07/08

- **S12-06 — scalar FP, conversions and bridges.** **V:** the K1OM ABI assigns
  float/double arguments to ZMM registers and makes all ZMM and mask registers
  caller-clobbered (R03, §§3.2.1–3). Cornea distinguishes IMCI gradual underflow
  from unsupported SIMD traps and documents ICC's use of x87 for trapping
  semantics (R04, slides 9, 18). **I:** compare complete ABI-to-arithmetic paths,
  including memory bridges, rounding and live values across calls. Neither
  source supplies production timings for our conversions, x87 divide, sqrt
  or log; lane-zero VPU arithmetic is not automatically a strict replacement.
  Keep EP's arithmetic/bridge and libm questions separate.
- **S12-07 — CG/HPCG and gathers.** **V:** measured gather completion costs
  depend on cache level and occupied lines, and include repeated gather/mask
  control (R05, §V.D/Table II). Sparse-matrix work distinguishes useful bytes
  from repeated private-cache transfers (R14, §§4.2–4.3). **I:** the current
  cost formula is not validated by matching one L2 endpoint. Cost indices,
  masks, address generation and ordered reduction separately; no retrieved
  source makes strict CG's FP reduction legally associative. Gather evidence
  does not establish scatter cost.
- **S12-08 — pressure, pairing and x87 versus scalar VPU.** **V:** pairing
  has instruction-length, displacement/immediate and prefix restrictions;
  some vector stores appear in a V-pipe eligibility table (R02, pp.34, 56).
  One context cannot issue in adjacent cycles (R17, slides 10–12). The ABI
  exposes call clobbers, not free scalar/vector transfers (R03). **I:** inspect
  encodings and reload causes before attributing spills or assuming every
  vector operation monopolizes U. Density four is not the serial M4 setting.
  Verify page mappings before explaining cache/TLB effects (R01, R09);
  requesting a 2 MiB allocation does not prove its backing.

### Editions, applicability and corrections

| Evidence | What is established | What must not be inferred |
| --- | --- | --- |
| SSDG R01 | Original Intel PDF **328207-001EN, November 2012, 201 pages** recovered. | It is not the 163-page edition previously cited at pp.16–22. Do not transfer pagination. |
| Later SSDG | **R:** Dolbeau R22 bibliography identifies **328207-002, June 2013**. No original PDF recovered. A transcription of **488596 rev.2.03, November 8, 2012** is another early reference, not the June edition. | The earlier note's 163-page PDF is not positively identified by similar prose. No edition-change claim is justified. |
| Optimization material | Original Klemm 2013/2014 decks, Rahman's 2013 book and Tian's compiler paper recovered. | None supplies a complete, stepping-qualified timing/pairing table. R16 and R17 are different decks. |
| Memory measurements | R06 explicitly uses an engineering sample; R14 uses pre-release SE10P; R20 is preproduction. R05 uses 5110P; R22 uses 7120P. | Absolute timings and saturation counts are not interchangeable. R08's SE10P results retain their own configuration. |
| Internal disagreements | R01 p.22 prose gives alternate-cycle L2 access while its table gives one/clock; pp.19/22 differ on L2 bank count. R17 slides 13–14 give different L1 latency descriptions. | Raw SRAM access, dependent-load latency, issue occupancy and loaded-memory latency cannot become one cost. |
| Vector issue | R01's overview puts vector execution on U; R02's V-pipe table includes vector stores/packstores and masks. R10 has a VPU V-pipe event. | The blanket claim that two vector instructions never pair needs opcode/operand qualification. Reconcile R02's old mnemonics with the ISA before implementation. |
| PMU | R10/R11 agree on **two 40-bit counters per hardware thread**, unlike R01's overview. | Counter count proves neither access nor attribution accuracy, and says nothing about an uncore interface. |
| Huge pages | R09 documents card-side THP in a named MPSS gold update; R26's offload-buffer setting has narrower scope. | Neither proves today's native malloc backing or makes a host SCIF driver option govern native card allocations. |

### Sources and specific findings

#### R01 — Original system software guide

Intel, *Intel Xeon Phi Coprocessor System Software Developers Guide*,
328207-001EN, November 2012.
[Original PDF in a document mirror](https://raw.githubusercontent.com/tpn/pdfs/master/Intel%20Xeon%20Phi%20-%20System%20Software%20Developers%20Guide%20%28Nov%202012%29.pdf).
Local: **ssdg-2012.pdf**. G02/G04/G07/G08/G11.

**V:** pp.19, 23–24 describe a two-cycle decoder, two ready bundles per
context, and selection of the next ready context in round-robin order; a
context cannot issue in consecutive cycles. A transfer outside the ready
buffer refetches from the instruction cache. This is not a documented decoded
loop cache. Slow prefixes include 66/67, LOCK, segment and REP; fast prefixes
include 62/C4/C5, REX and 0F. Address-generation interlock is at least three
clocks. Page 19 describes 16 L2 prefetch streams constrained to 4 KiB pages,
with up to four requests per stream. Pages 22–23 give 64 small-page plus eight
2 MiB data translations, 32 small-page instruction translations, and a
64-entry second-level structure serving large translations or small-page PDEs.
**I:** these constrain models but do not settle branch prediction, mixed-page
replacement, loaded latency or simultaneous memory issue.

#### R02 — Pairing and operand-dependent forwarding

Rezaur Rahman, *Intel Xeon Phi Coprocessor Architecture and Tools*, Apress,
2013. [Publisher PDF](https://link.springer.com/content/pdf/10.1007/978-1-4302-5927-5.pdf).
Local: **rahman-2013.pdf**. G01/G02/G07/G12.

**V:** p.56 (PDF 59) excludes pairing for instructions longer than eight
bytes, combined displacement/immediate operands, microcode, and 62/C4/C5
prefixes with disp32; dependency exceptions include CMP/Jcc.
Table 3-1, p.34, lists masks and selected vector stores among V-pipe candidates,
using some historical names. Page 33 distinguishes forwarding to the ordinary
arithmetic stage from earlier swizzle/EMU consumers; dependent swizzle paths
can add delay. **I:** these are encoding/operand constraints, not a ready-made
reservation table. Independent swizzle throughput does not prove zero extra
dependent latency. The integer-multiply explanation does not quantify bridges.

#### R03 — Scalar/vector ABI and call pressure

H.J. Lu, Milind Girkar, Michael Matz, Jan Hubicka, Andreas Jaeger and Mark
Mitchell, *System V Application Binary Interface: K1OM Architecture Processor
Supplement*, version 1.0, April 26, 2012.
[Archived Intel PDF](https://web.archive.org/web/20230720214845id_/https://www.intel.com/content/dam/develop/external/us/en/documents/k1om-psabi-1-0.pdf).
Local: **k1om-psabi-1.0.pdf**. G01/G02/G05/G14.

**V:** §§3.2.1–3, pp.15–22 (PDF pages one higher), specify argument classes,
ZMM0–7 argument allocation and ZMM0/1 returns for the relevant vector class.
The class name SSE is ABI terminology; it does not enable SSE instructions.
Figure 3.4, p.21, marks all 32 ZMM and eight mask registers caller-clobbered.
MXCSR control bits and the x87 control word are callee-preserved; their status
bits are caller-clobbered. Long-double arguments/returns have separate rules.
**I:** preserve these obligations when comparing calls with inline arithmetic;
ABI conformance says nothing about helper quality or transfer latency.

#### R04 — Floating-point modes and strictness

Marius Cornea, Intel, *Numerical Computation on Intel Xeon Phi Coprocessors
Using the Intel Compilers and Math Libraries*, October 15, 2013.
[Slides](https://www.lip6.fr/public/2013-10-15_Cornea.pdf).
Local: **cornea-2013.pdf**. G01/G05/G13.

**V:** slides 9 and 18 distinguish x87 extended precision from IMCI FP;
IMCI supports gradual underflow, DAZ/FZ, rounding modes and exception flags,
but not SIMD exception traps. ICC's strict/exception-support route uses x87.
**I:** distinguish numerical equivalence, flags, traps and excess precision.
Fast-mode advice and vendor math performance claims do not establish a
conforming GCC replacement. No vendor math implementation was opened.

#### R05 — Gather completion on a production model

Johannes Hofmann, Jan Treibig, Georg Hager and Gerhard Wellein, *Performance
Engineering for a Medical Imaging Application on the Intel Xeon Phi
Accelerator*, arXiv:1401.3615, 2014.
[Authors' paper](https://arxiv.org/pdf/1401.3615).
Local: **hofmann-gather-2014.pdf**. G03/G04/G12/G16.

**V:** §V.D, p.4/Table II, on a 5110P, reports completion-loop cycles for
16 active SP lanes. One versus sixteen occupied lines gives 9.0 versus 36.8
cycles in L1 and 13.6 versus 129.6 in L2. The L1 two-line case is 8.4:
a monotone per-line formula is not an exact fit even here. Section VI, p.5,
reports no benefit from the gather hint, blocking behavior for another
gather-prefetch instruction, and excessive scalar-prefetch index extraction
overhead in this application. **I:** measure the full loop; do not assume an
asynchronous gather-prefetch queue or transplant its tuned distances,
approximate division or application speedup into strict M4.

#### R06 — Detailed memory experiments, explicitly preproduction

Zhenman Fang et al., *Measuring Microarchitectural Details of Multi- and
Many-Core Memory Systems through Microbenchmarking*, ACM TACO 11(4), article
55, publication footer December 2014.
[Author PDF](https://zhenman.github.io/files/J1-TACO2015-uBench-XeonPhi.pdf).
Local: **fang-taco2015.pdf** (host filename says 2015). G04/G08/G11.

**V:** §4, p.55:10, identifies a 1 GHz engineering sample, Linux 2.6.38.8
and ICC 13.0.1. Sections 5–6/Table V, p.55:19, report eight L1 miss-handling
entries shared across siblings and 56–60 L2 entries. These measured capacities
need not be the SSDG's roughly 38 combined requests. Hardware prefetch remains
bounded by 4 KiB even with large pages; software prefetch can cross pages and
initiate translation without servicing a page fault. **I:** useful methodology
and hypotheses; no production constants are imported from this sample.

#### R07 — Independent latency and concurrency measurements

Jianbin Fang, Henk Sips, Lilun Zhang, Chuanfu Xu, Yonggang Che and Ana Lucia
Varbanescu, *Test-Driving Intel Xeon Phi*, ICPE 2014, pp.137–148.
[Proceedings PDF](https://research.spec.org/icpe_proceedings/2014/proceedings/p137.pdf).
Local: **fang-icpe2014.pdf**. G01/G02/G08/G11.

**V:** §3.1 distinguishes dependent-instruction latency from aggregate
throughput; §3.2 measures cache/memory access. The paper describes a 60-core,
1.05 GHz 5100-series configuration (p.139), a different experiment from R06.
**I:** preserve the distinction between latency, available parallelism and
occupancy; neither the series label nor ICC identifies our scalar strict mix.

#### R08 — TACC bandwidth and prefetch tuning

John D. McCalpin, *Native Computing and Optimization on the Intel Xeon Phi Coprocessor*,
IXPUG 2014. [Slides](https://www.ixpug.org/docs/IXPUG_2014_MIC_Native-new.pdf).
Local: **mccalpin-ixpug2014.pdf**. G04/G08/G11.

**V:** slides 23–25 and 28 relate latency, outstanding cache lines and useful
bandwidth on SE10P. They distinguish eight outstanding L1 requests from
additional L2 prefetch traffic, show STREAM behavior changing with density,
and report a 16-stream L2 prefetcher bounded by 4 KiB pages. Stream count and
prefetch aggressiveness change the preferred density. **I:** adding workers
can increase concurrency or contention. Whole-card STREAM maxima and idle
latency do not supply serial M4 prefetch distances.

#### R09 — STREAM, store hints and card-side THP

Karthik Raman, Intel, *Stream on Intel Xeon Phi Coprocessors*, updated
October 22, 2013.
[Intel PDF](https://www.intel.com/content/dam/develop/external/us/en/documents/streamtriad-xeonphi-3.pdf).
Local: **raman-stream-2013.pdf**. G04/G08/G10/G11.

**V:** pp.2–4 give a 7110P STREAM recipe with 60 workers and ICC distances of
64 lines to L2 and eight to L1, plus streaming-store/eviction choices. Page 4
identifies MPSS KNC_gold_update_1-2.1.4982-15 or later as providing THP promotion
for heap/stack data. **I:** native huge pages historically need not require
explicit HugeTLB. Current policy, promotion success and backing remain unknown.
Store legality/order still comes from the ISA conditions in part 1; a
memory-bound recipe is not a generic default.

**S12-13 qualification:** R09 p.4 explicitly labels its results
**pre-production**, despite the 5110P/7110P column names, and identifies
MPSS 2.1.4346-16 for that libhugetlbfs performance table. **Superseded:** ~~Its
later-stack THP guidance is a separate claim. Those results do not measure
transparent promotion under the recommended update or establish today's card
allocation policy.~~ R09 p.5 adds two **pre-production** THP-stack tables,
both without libhugetlbfs: 7110P on MPSS 2.1.4982-15 reports 174/181 GB/s
(ECC on/off), and 7120P on MPSS 2.1.6720-15 reports 177 GB/s with ECC on.
All three tables use MPSS 2.1 and 2.6.x uOS. They do not establish promotion
or backing for today's MPSS 3.7 malloc; S12-12 G08 remains needed.


#### R10 — Core PMU definitions recovered

Intel, *Intel Xeon Phi Coprocessor Performance Monitoring Units*,
327357-001, revision 1.01, July 10, 2012.
[Archived original](https://web.archive.org/web/20240000000000id_/http://software.intel.com/sites/default/files/forum/278102/intelr-xeon-phitm-pmu-rev1.01.pdf).
Local: **pmu-327357-001.pdf**. G02/G03/G06/G07/G08/G11/G12.

**V:** pp.5–7 specify two 40-bit counters per thread; configuration requires
ring 0. User-mode counter instructions do not establish OS permission.
Pages 11–12 distinguish per-thread filtering from events lacking thread
context, and warn that TSC is not a wall-clock source. Table 1-6, pp.12–16,
provides these interpretation constraints (identifiers are interface facts,
not a reproduction of the vendor event table):

| Diagnostic | Verified definition or limitation |
| --- | --- |
| Pairing | INSTRUCTIONS_EXECUTED_V_PIPE counts paired execution. |
| AGI | Ordinary AGI can count both pipes in a cycle; gather/scatter AGI counts that interlock, not full gather time. |
| Branches | BRANCHES_MISPREDICTED excludes BTB misses. |
| L2 traffic | L2_READ_MISS can count prefetch and demand for the same address. Separate events distinguish cache versus memory fills. |
| VPU | Read transactions, register-conflict occurrences and active elements are different units; active elements are not FLOPS. |

**I:** qualify event scope and stepping before ratios. Several definitions
explicitly mention A0. This core guide does not close GBOX/uncore access.

#### R11 — Public KNC perf implementations, not the deployed kernel

Linux contributors, Linux **v3.10**, 2013,
[arch/x86/kernel/cpu/perf_event_knc.c](https://raw.githubusercontent.com/torvalds/linux/v3.10/arch/x86/kernel/cpu/perf_event_knc.c).
Local: **linux-v3.10-perf_event_knc.c**. G06/G14.
Also Mpss-vt Linux fork, revision **b76c20**, version **3.2.14** in its
[Makefile](https://sourceforge.net/p/mpssvt/linux/ci/b76c20/tree/Makefile?format=raw),
[driver](https://sourceforge.net/p/mpssvt/linux/ci/b76c20/tree/arch/x86/kernel/cpu/perf_event_knc.c?format=raw).
Local: **mpssvt-Makefile**, **mpssvt-perf_event_knc.c**; snapshot date not established.

**V:** v3.10's knc_pmu declares two 40-bit counters and maximum period
2^39-1. Its event-constraint table restricts listed CRI/L2 events to counter
0; it contains no corresponding VPU-only-counter-1 table. The generic event
map assigns cache references/misses to L1 data events 0x28/0x29, not a
universal last-level metric. Its cache-event map treats event zero as a valid
data-read event. **I:** checking perf_event_open registration and exact errors
is justified even without a perf executable. Neither tree matches the installed
2.6.38-based MPSS kernel; backports, permissions and sampling remain open.

#### R12 — Production errata change the correctness envelope

Intel, *Intel Xeon Phi Coprocessor Specification Update*, 328205-016,
March 2015.
[Intel PDF](https://www.intel.com/content/dam/www/public/us/en/documents/specification-updates/xeon-phi-coprocessor-specification-update.pdf).
Local: **errata-328205.pdf**. G02/G09/G13/G14/G15.

**V:** CD14 p.22 concerns mask-state lazy switching and a paired mask branch
missing the expected device-not-available exception. CD19 p.23 allows a
faulting vector instruction to affect MXCSR. CD26 p.25 concerns a paired,
uncacheable aligned packstore, not ordinary write-back stores. CD28 p.25
concerns clearing an unmasked x87 exception with FNCLEX. CD34 p.26 describes
unpinned thread migration and variable performance. CD16/17 p.23 concern
DMA completion/interrupt behavior. **I:** match stepping and workaround status
before fenv, signal, pairing or SCIF experiments. A planned MPSS fix is not
proof our image contains it. Not every erratum applies to every card.

#### R13 — Compiler authors on masks, tails and alignment

Xinmin Tian et al., Intel, *Practical SIMD Vectorization Techniques for
Intel Xeon Phi Coprocessors*, IPDPSW 2013, pp.1149–1158.
[Paper](https://faculty.kfupm.edu.sa/coe/mayez/ps-coe502/references/Practical%20SIMD%20Vectorization%20Techniques%20for%20Intel%C2%AE%20Xeon%20Phi%E2%84%A2%20Coprocessors.pdf).
Local: **tian-vectorization-2013.pdf**. G03/G04/G12/G13/G16.

**V:** §§III–V, PDF pp.2–6, discuss masked tails, alignment peeling,
multi-versioning and two-dimensional vectorization. Masked/converting unaligned
accesses distinguish unpack/pack fault behavior from gather/scatter.
The safe-padding option assumes another 64 bytes after objects, an extra
program contract. **I:** ordinary GCC programs cannot be presumed padded.
Tail and mask overhead belong in costs; reported option-dependent gains
do not establish strict M4 gains or legal extra memory accesses.

**S12-13 configuration qualification:** R13's introduction names a 5110P,
but Table 6.1 p.1155 (PDF p.7) describes the measured system as 61 cores,
1 GHz and 7936 MB. Its exact model/production status is not established;
do not label the experiments 5110P from the introductory example.

#### R14 — Sparse locality is not nominal bandwidth

Erik Saule, Kamer Kaya and Umit V. Catalyurek, *Performance Evaluation of
Sparse Matrix Multiplication Kernels on Intel Xeon Phi*, arXiv:1302.1078,
v1, February 2013. [Paper](https://arxiv.org/pdf/1302.1078).
Local: **saulea-spmv-2013.pdf**. G03/G08/G11/G16.

**V:** §2 p.2 identifies a **pre-release SE10P**. Sections 4.2–4.3,
pp.7–10, relate useful cache-line density to vectorization and distinguish
one-copy application traffic from input-vector replication/reloads in private
caches. The rendering's later generated date does not make it a 2024 experiment.
**I:** layout and reuse can explain low useful bandwidth without saturating
GDDR. Its reordering/register blocking are algorithmic transformations,
not automatically legal fixes for CG's ordered arithmetic or benchmark inputs.

#### R15 — Alternative vectorization for indirect layouts

Mingfei Ma, Jinlong Hou, Jason Ye, Meena Arunachalam and Rafael Gutierrez,
Intel, *Optimizing Non-Contiguous Memory Access on Intel Xeon Phi
Coprocessors*, HPCC 2015.
[Paper](https://aiichironakano.github.io/cs653/Ma-XeonPhiOpt-HPCC15.pdf).
Local: **ma-noncontiguous-2015.pdf**. G03/G12/G16.

**V:** §§III–IV, pp.2–4, compare intra-loop/inter-loop vectorization,
alignment/padding and layout/conversion choices for molecular dynamics.
**I:** alternatives include changing which independent work occupies lanes
and separating movement from computation. They require actual independence
and observable-layout legality; this application study does not prove that
more gathers improve generic sparse code.

#### R16 — Original optimization slides, 2013 edition

Michael Klemm, Intel, *Optimization Strategies for Intel Xeon Phi
Coprocessors*, 2013.
[HPC2N-hosted slides](https://www.hpc2n.umu.se/sites/default/files/2.03%20Optimization%20Strategies.pdf).
Local: **klemm-optimization-2013.pdf**. G02/G04/G08/G09/G16.

**V:** slides 51–54 separate placement, vectorization decisions, memory/TLB
behavior and eviction control. The density-sensitive compiler hint on
slide 51 is experimental. **I:** retain actual density and inspect reasons
for missed vectorization; this does not validate a universal four-thread
model. Intel runtime variables/ICC flags are not libgomp/GCC controls.
Slide numbers from the 2014 deck do not apply.

#### R17 — Original microarchitecture slides, 2014 edition

Michael Klemm, Intel, *The Intel Xeon Phi Coprocessor*, LMU seminar,
December 11, 2014.
[Slides](https://www.nm.ifi.lmu.de/teaching/Seminare/2014ws/Hauptseminar/doc/2014-12-11.Xeon.Phi.pdf).
Local: **klemm-microarch-2014.pdf**. G02/G07/G08/G11/G12.

**V:** slides 10–12 describe next-ready selection, the adjacent-cycle
restriction, 32 ZMM/eight mask registers per context, and usual four-cycle
vector latency/one-cycle throughput. Slides 13–14 give cache geometry and
distinguish raw L2 from memory latency but differ on L1 access-time wording.
**I:** these corroborate capacities, not a complete timing model. Labeled
ring bandwidth, GDDR pin rate, useful bytes and bidirectional traffic are
different quantities.

#### R18 — PRACE/LRZ best practices, version and runtime scope

Emil Atanassov et al., editor Volker Weinberg (LRZ), *Best Practice Guide
Intel Xeon Phi*, **v2.0, January 31, 2017**.
[PRACE PDF](https://prace-ri.eu/wp-content/uploads/Best-Practice-Guide_Intel-Xeon-Phi.pdf).
Local: **prace-bpg-v2.pdf**. G04/G08/G09/G10/G16.

**V:** KNC §§13.2.4–13.2.5, pp.59–61, discuss Intel OpenMP's 200 ms blocktime
and distinguish repeated parallel regions from barriers remaining inside
a persistent region. **I:** reducing region count need not reduce barriers
or wakeups. These Intel-library controls do not establish libgomp's policy.
The guide also contains KNL material, which is not imported into KNC advice.

#### R19 — Colfax application-level guidance

Andrey Vladimirov, Ryo Asai and Vadim Karpusenko, *Parallel Programming and
Optimization with Intel Xeon Phi Coprocessors*, second edition,
Colfax International, copyright **2013–2015** (free release announced 2019).
[Publisher PDF](https://colfaxresearch.com/download/8609/).
Local: **colfax-2ed.pdf**. G04/G09/G10/G16.

**V:** §4.4.5 p.341 separates placement choices for memory/compute-bound
work. Section 4.5.4 pp.376–377 explains first-touch NUMA placement using a
multi-socket **Xeon host** example. **I:** that example does not establish
socket-style NUMA placement on KNC. Card first touch still affects faults,
zeroing and cache residency; measure the actual allocation path.
Recommendations are workload-dependent, not runtime defaults.

#### R20 — Early OpenMP synchronization experiments

Tim Cramer, Dirk Schmidl, Michael Klemm and Dieter an Mey, *OpenMP Programming
on Intel Xeon Phi Coprocessors: An Early Performance Comparison*, MARC 2012.
[Authors' PDF](https://www.lfbs.rwth-aachen.de/marc2012/07_Cramer.pdf).
Local: **cramer-openmp-2012.pdf**. G09/G16.

**V:** §II p.2 identifies preproduction hardware; EPCC measurements and
applications, pp.3–6, distinguish synchronization overhead from kernel
throughput. **I:** measure realistic grain sizes; do not transplant early
Intel-library costs to libgomp or equate synthetic and application gains.

#### R21 — Lab measurements on 5110P

Subhash Saini et al., NASA Ames/SGI/CSC, *An Early Performance Evaluation of
Many Integrated Core Architecture Based SGI Rackable Computing System*,
NAS Technical Report **NAS-2015-04**.
[NASA PDF](https://www.nas.nasa.gov/assets/nas/pdf/papers/NAS_Technical_Report_NAS-2015-04.pdf).
Local: **nasa-2015-04.pdf**. G08/G09/G11/G16.

**V:** p.3 identifies 5110P; §6.5, pp.7–8, measures OpenMP synchronization and
loop scheduling with EPCC. **I:** synchronization, scheduling and memory need
separate denominators/configuration. This is production-model laboratory
evidence, not proof the local optional libgomp barrier beats its baseline.

#### R22 — Physical-address effects on communication

Romain Dolbeau, CAPS, *Address Selection for Efficient Barriers on the Intel
Xeon Phi*, revision 1.40, April 8, 2014.
[Author PDF](http://www.dolbeau.name/dolbeau/publications/barrierphi.pdf).
Local: **dolbeau-barriers-2014.pdf**. G08/G09/G11.

**V:** §II pp.1–3 studies cache-line ping-pong on a **7120P**, controlling
the physical page and changing offsets/core pairs. Section III/Figures 7–8
shows address-dependent barrier cost for that algorithm and placement.
DTD mapping is not exposed as a portable formula. **I:** physical placement
is a credible communication variable. It does not revive the withdrawn C4
coloring attribution: our experiments did not control those variables.
Do not copy this paper's reboot/page-reservation procedure into M4.

#### R23 — A thesis with application synchronization attribution

Thomas Lang, University of Passau, *An Intel Xeon Phi Backend for the
ExaStencils Code Generator*, bachelor thesis, April 27, 2016.
[University PDF](https://infosun.fim.uni-passau.de/cl/arbeiten/lang-b.pdf).
Local: **lang-thesis-2016.pdf**. G06/G09/G16.

**V:** §4.3 p.33 (PDF 41) reports about 57% of one stencil program's runtime
in OpenMP using perf. **I:** this demonstrates an application synchronization
bottleneck and historical profiling, not access on our image or a transferable
percentage. Some numerals extract poorly; no hardware/compiler version is
inferred from damaged text. Its generated-code transformations are not applied.

**S12-13 source update:** direct PDF text at §4.1 p.29 (PDF p.37) gives
57 cores at 1.1 GHz and ICC 16.0.1.150. This supersedes the earlier inability
to establish those configuration fields from the damaged extraction. The
commercial model, stepping and production qualification remain unspecified;
they must not be inferred from core count.


#### R24 — Allocator policy and an upstream x87 math reference

GNU C Library contributors, **glibc-2.21**, 2015:
[malloc/arena.c](https://raw.githubusercontent.com/bminor/glibc/glibc-2.21/malloc/arena.c),
[malloc/malloc.c](https://raw.githubusercontent.com/bminor/glibc/glibc-2.21/malloc/malloc.c),
[sysdeps/i386/fpu/e_log.S](https://raw.githubusercontent.com/bminor/glibc/glibc-2.21/sysdeps/i386/fpu/e_log.S).
Local: **glibc-2.21-arena.c**, **glibc-2.21-malloc.c**, **glibc-2.21-e_log.S**.
G01/G05/G10.

**V:** arena_get2 uses an explicit maximum when supplied, otherwise
__get_nprocs() and the architecture-dependent arena factor (eight for 64-bit).
new_heap reserves space with PROT_NONE/MAP_NORESERVE before enabling the used
portion. The i386 math source uses x87 logarithm instructions with a near-one
path. **I:** reported CPUs are not affinity, and virtual reserve is not RSS.
The math file is a mechanism reference, **not K1OM's installed log**.
Neither a version string nor a matching sysroot proves source identity;
MPSS patches and installed symbol paths remain unresolved.

#### R25 — SCIF synchronization and CPU-versus-DMA paths

Intel MPSS contributors, MPSS modules **3.6.1-1** source mirror, revision
**2850ead25b5c81ece2006d7ae06c2b3149175565** (release metadata; calendar date
not established):
[include/scif.h](https://raw.githubusercontent.com/CIRCL/mpss-modules/2850ead25b5c81ece2006d7ae06c2b3149175565/include/scif.h),
[micscif/micscif_rma.c](https://raw.githubusercontent.com/CIRCL/mpss-modules/2850ead25b5c81ece2006d7ae06c2b3149175565/micscif/micscif_rma.c).
Local: **scif-3.6.1.h**, **scif-3.6.1-rma.c**. G10/G14/G15.

**V:** the scif_readfrom/write API descriptions distinguish synchronous
completion, CPU copies and ordered final-cache-line visibility. RMA copy
setup selects DMA polling for synchronous final chunks and a separate CPU
route; registration caching depends on configuration. **I:** initiation is
not completion; pinning/cache resources and CPU/DMA interference are separate
costs. These small files preserve original notices outside git. They do not
establish MPSS 3.7 behavior.

#### R26 — MKL tuning scope and ICC release boundary

Intel, *Intel MKL 11.3 Update 4 Developer Guide*, 2016, section on improving
performance on Intel Xeon Phi coprocessors:
[Guide page](https://portal.nacad.ufrj.br/online/intel/mkl/common/mkl_userguide/GUID-7F67CA7F-0B2D-4584-AE90-63A64A58F0EC.htm).
Local: **mkl-11.3-knc-tuning.html**. G05/G08/G09/G10.
**V:** large-buffer advice describes MIC_USE_2MB_BUFFERS for pointer-based
**offload transfers**, not general native allocation. **I:** do not apply
that variable to GCC native malloc or infer glibc behavior from MKL choices.

Intel, *Intel C++ Compiler 18.0 for Linux Release Notes for Intel Parallel
Studio XE 2018*, initial release 2017:
[Release notes](https://www.intel.com/content/www/us/en/developer/articles/release-notes/c-compiler-legacy/18-0-linux-for-psxe2018.html).
Local: **icc18-release-notes.html**. G01/G05/G16.
**V:** the new-features section identifies removal of x100/KNC support in
18.0. **I:** later Intel compiler/AVX-512 advice cannot be assumed to describe
IMCI. No recovered release note provides complete KNC timings or warrants
replacing strict library calls with fast vector math.

### Sources not recovered and claims still reported

| Target | Retrieval result and evidentiary limit |
| --- | --- |
| Intel **330991-001**, *Xeon Phi Coprocessor x100 Product Family: Registers*, December 2014 | **R:** identified in [knc-microarch.md](knc-microarch.md); no recoverable original URL/PDF found through title/number searches and Intel/archive paths. Local file: **none**. Its cited TUNE_PREFQ pp.17–18, counters pp.35–37 and GBOX p.39 remain secondhand. R10 closes core PMU definitions, not uncore programming or queue controls. |
| Intel SSDG **328207-002**, June 2013 | **R:** R22 reference [10] supplies the [old Intel URL](http://software.intel.com/sites/default/files/article/334766/intel-xeon-phi-systemssoftwaredevelopersguide_0.pdf). Direct/archive retrievals failed or redirected to a landing page; local file: **none**. Do not substitute R01's pagination or claim an edition comparison. |
| SSDG **488596 rev.2.03**, November 8, 2012 | A [transcription](https://doczz.net/doc/21375/intel%C2%AE-xeon-phi%E2%84%A2-coprocessor-system-software-developers-g...) exposed the identifier; PDF download failed. Local file: **none**. Used only to distinguish bibliographic identities, not as new hardware constants. |
| Matching **MPSS 3.7** kernel/libc patches and guide | Small snapshots R11/R24/R25 were obtainable; none establishes the installed patchset. An MPSS **3.8**, April 2017 [guide transcription](https://manualzz.com/doc/48993479/intel%C2%AE-manycore-platform-software-stack--intel%C2%AE-mpss-) was found; original PDF unavailable. No 3.8 host-driver setting becomes a verified 3.7 card-side fact. Local file: **none**. |
| Complete production instruction timing, branch predictor and uncore-event manuals | Not recovered. Original guides, errata, papers and slides provide partial constraints. Failure to find a document is not evidence that a hardware facility is absent. |

The corpus covers Intel originals, compiler papers, independent experiments,
a thesis, TACC/PRACE/LRZ/Colfax guidance, release notes and small kernel/libc
sources. Acquisition failures are recorded rather than filled with KNL advice.
No ICC headers, SVML, libimf, Intrinsics Guide XML or ISPC code was accessed.

### Ranked residual gaps and bounded closure experiments

These are **estimates of exclusive card wall time**, including repetitions
and simple calibration, after host preparation/builds. They are proposals for
the lead, not jobs launched here. Setup, document acquisition, compiler builds,
full M4 scoring and scheduling delays are extra. Each row is a bounded
diagnostic, not a request to repeat passing acceptance.

Checks exceeding about a minute must split independent work over assigned
CPUs. Timing cases requiring one isolated core must retain their single-core
meaning; parallel case execution must not contaminate shared-memory/cache
measurements. Record affinity, sibling activity, actual page backing, clock
source and power state. No speedup is forecast.

| M4 priority | Residual gap and why documents do not close it | Smallest discriminating experiment | Card time |
| --- | --- | --- | --- |
| 1 | **G01**, S12-06: full scalar FP/conversion/call-bridge cost and strict semantics on our production card | Compare hot sequences with known-live inputs, dependent chains and independent work at density one; include subnormal, range, rounding and exception boundaries for proposed alternatives. Separate arithmetic from spills/call transfers. | 20–40 min |
| 2 | **G03**, S12-07: indexed loads/gather completion versus ordered scalar reduction; scatter remains unmeasured | Fix active lanes/arithmetic; vary occupied lines, cache residence and index extraction. Time complete loops, masks and setup. Test scatter separately only if a candidate emits it. | 20–35 min |
| 3 | **G02/G12**, S12-08: production pairing/forwarding and real serial pressure | For classes in candidate RTL, vary pair order, dependencies, encoding length and disp32. Separate reload spills from program storage; add one/two/four siblings only to resolve ambiguous issue behavior. | 20–40 min |
| 4 | **G06**: working event access and unbiased attribution, enabling several later rows | Inventory registration/permissions; count known work with one feasible event pair, retaining exact errors and enabled/running times. Calibrate counts and sampling loss/perturbation before profiling. Stop if infrastructure prevents trustworthy counting. | 10–20 min; driver repair extra |
| 5 | **G04**: profitable prefetch distances, queues and stores for real access mixes | Fix alignment, mappings and initialization; compare no hint with a small distance set on identified streams. Distinguish temporal/no-read/weakly-ordered stores only where legal; count traffic if PMU access qualifies. | 20–35 min |
| 6 | **G08**, S12-08: actual page backing and cache-versus-TLB effects | Inspect mappings/faults; compare verified 4 KiB/2 MiB pages with distributed offsets. Vary working set and stride independently; avoid the known same-offset cache-conflict mistake. | 15–30 min |
| 7 | **G05**: installed libc/libm route, bridge share and numerical quality | Identify loaded objects/symbols first; time actual log and copy/set paths on representative inputs/sizes, separating process setup from steady state. Correctness checks are required for a proposed replacement. | 15–30 min; accuracy campaign extra |
| 8 | **G16**: whether a general mechanism removes an observed hot cost | Preserve decisions/RTL for approved themes; use region A/B diagnostics with fixed inputs and two controls. Attribute eliminated work or better scheduling before requesting full M4 qualification. | 20–45 min diagnostic budget |
| 9 | **G07**: prediction/refill, footprint and alignment costs | Restrict to a hot branch family; control predictability, target placement, work and cache footprint. Separate BTB misses from the incomplete PMU misprediction event. | 15–25 min |
| 10 | **G10**: arena limits, first touch and retained memory on this image | Observe CPU count versus affinity, allocator settings, faults, RSS and mappings. Compare a small arena-cap set only if allocation is material; preserve fresh-process timing. | 10–20 min |

Other gaps have higher expected value for later parallel/runtime sprints than
the primary serial M4 vote. Correctness gates precede dependent optimizations.

| Later-sprint priority | Residual gap | Closure experiment | Card time |
| --- | --- | --- | --- |
| 1 | **G09** waits, affinity and realistic barrier grain | Compare current/optional libgomp paths with useful work, fixed topology and active/passive waits; observe wakeups/migrations if possible. Preserve the existing measured regression as baseline. | 20–40 min |
| 2 | **G11** loaded ring/GDDR traffic and ownership | With qualified counters, compare read/write/RFO/remote-cache mixes under fixed affinity/pages. Vary physical/directory placement only if observable and controllable; distinguish useful and transferred bytes. | 30–60 min |
| 3 | **G13/G14** FP environment, masks, signals and switching | Match errata/workarounds; for a proposed path test flags/rounding/traps, signal return and deliberate migration with nontrivial vector/mask state. ABI text does not prove kernel correctness. | 15–30 min |
| 4 | **G15** SCIF and system interference | With lead coordination, separate registration, submission and fenced completion; compare CPU/DMA and concurrent native work, recording pinned memory/traffic. Transfer time remains outside M4 where specified. | 20–40 min |
| 5 | **G16** transfer beyond development code | After establishing mechanisms, sample independent sparse, branch-heavy, abstraction-heavy and parallel programs; retain decisions/regressions without opening held-out artifacts. | 1–2 h initial sample; not full qualification |

Documents resolve interface and resource constraints. Scalar bridges,
production pairing, gathers/scatters and deployed runtimes still need bounded
measurements or source identification. They do not justify precision changes,
reassociation, invisible memory transfers or benchmark-specific tuning.
