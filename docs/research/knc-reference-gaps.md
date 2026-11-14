# KNC reference gaps: compiler, card runtime and broad optimization

S12-10, phase 1, 2026-11-14. **Awaiting the lead's ranked-gap review before
phase 2.** This part uses existing local material only. No web research,
document download, build, test or card job was performed. Code is unchanged.

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

The next decision is which of the ranked gaps deserves deeper document
acquisition. Phase 2 has not started. Its final residual-gap list and card-time
estimates must follow the document search; the experiments above are closure
criteria, not scheduled card jobs or new implementation tickets.
