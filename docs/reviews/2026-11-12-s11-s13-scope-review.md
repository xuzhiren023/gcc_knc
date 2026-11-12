# S11–S13 scope review for M4

2026-11-12 · S11-13 · Senior compiler engineering review · Recommendations only

**Verdict.** M4 is plausible, but the plan as written does not justify predicting a pass. The threshold is a median whole-program speedup of 1.25x over GCC 5.1.1, with no unexplained slowdown above 5%; the available corpus evidence is a compile-only GCC 14/AVX-512 proxy, not a native baseline ([P] §6; [C] lines 3–6, 43–64). Strong kernel gains already exist, but cannot be multiplied into a whole-program forecast: Sprint 8 improved mat8 5.7x and mat16 3x over Sprint 7, while short kernels lost 5–10%, and neither comparison is against the donor ([CS] line 98). The highest-value change is to make S11 establish a frozen, valid M4 experiment, move profiling and a small default/PGO screen forward, and spend S12 on the largest measured development-corpus losses. Keep transport and GEMV as explicit owner priorities, with separate success criteria and bounded card turns; do not make their bandwidth aspirations a prerequisite for M4. Reserve S13 for qualification, one bounded repair cycle, and the decision already specified in [P], rather than several new optimization projects ([S11] Goals; [S13] Order).

## Evidence boundary and the speedup budget

This review uses the repository's collected evidence; it runs no program and makes no new native-performance claim. Dated results supersede historical predictions: [CS] line 19 supersedes [DS] §6's unimplemented FP64 proposal; [MB] §“sweep-2 results” supersedes its first-sweep forecasts; [CS] line 98 and [B] E7-15 supersede the “card numbers pending” headings of the S9 notes. Historical gap lists are candidate mechanisms, not a list of missing implementations ([GAP] lines 6–7).

For an unchanged workload, the planning calculation is `S = 1 / ((1-f) + f/s)`, where `f` is the donor wall-time fraction accelerated and `s` its local speedup. Reaching 1.25x requires eliminating 20% of donor time: even a 2x local improvement needs `f >= 0.40`; 3x needs `f >= 0.30`. These are arithmetic scenarios, not measured corpus fractions. Profiling must supply `f`, including setup, runtime and serial work ([C] §Interpretation; [P] §6).

The proposed set contains 17 program units: eight selected PolyBench programs, STREAM, four NPB programs, HPCG, zlib, SQLite and bzip2 ([C] lines 17–33). With one vote per program, at least nine must reach 1.25x for the median to reach it. Eight PolyBench programs alone therefore cannot deliver a pass. If all three held-out programs are conservatively budgeted at 1.00x, nine of fourteen development programs must supply the gains. This is a sensitivity calculation, not a proposal to tune toward nine winners or to discard failures.

The table gives **conditional whole-program planning estimates**, not confidence intervals or forecasts measured on these programs. Each numeric scenario states the unmeasured hot fraction and local gain it requires; a failure to find that fraction returns the planning estimate toward 1.00x. Kernel comparisons below establish plausible mechanisms, not donor-relative multipliers. Vector, scalar, memory and runtime effects overlap and must not be added together.

| Program | Where gain could come from; conditional budget | Evidence and what the current plan misses |
|---|---|---|
| PolyBench gemm | Vectorized independent work, scalar replacement, legal interchange/blocking. If 50–75% of donor time improves 2x: 1.33–1.60x. No credit for reassociating strict sums. | [C] Results and Interpretation identify loop-form limits; [SM] §§Root cause/Fix and [CS] line 23 show large gains from removing scalar/vector bridges. Add a locality/loop-form diagnosis; the old mat16 result is not a GEMM prediction. |
| PolyBench atax | Vector updates and reuse of matrix/vector data; strict reductions can remain a limiter. The same hypothetical 50–75% at 2x gives 1.33–1.60x. | [C] Results/Interpretation; [SRC] insight I-2 on TLB-limited blocking. GEMV research may suggest a mechanism, but require compiler-generated atax evidence before assigning it value. |
| PolyBench cholesky | Remaining scalar FP, dependency-preserving transformations, already-qualified divide/sqrt where legal. If 30–60% improves 1.5x: 1.11–1.25x. | [C] Results/Interpretation; [CS] line 19; [DS] §4.1. Scheduling/prefetch alone does not establish the necessary fraction; inspect scalar/vector transitions and recurrence costs. |
| PolyBench ludcmp | Similar scalar FP and recurrence exposure, with profitable independent updates. If 30–60% improves 1.5x: 1.11–1.25x. | [C] Results/Interpretation; [CHAR] C9 corrected memory chain. Add scalar replacement and loop-order diagnosis; do not infer speed from its 50% proxy loop coverage. |
| PolyBench jacobi-2d | Vector stencil code, reuse, redundant-load removal and prefetch. If 60–90% improves 1.5x: 1.25–1.43x. | [M2] lines 25–27 show stencil gain relative to hand IMCI; [CS] line 23 also shows folding did almost nothing for later stencils. Profile first; avoid counting already-realized improvements again. |
| PolyBench heat-3d | Vector stencil work and cache/TLB-aware traversal; same 60–90% at 1.5x scenario: 1.25–1.43x. | [C] Results; [SRC] I-2; [MB] lines 506–509. Logical stencil GB/s is not physical DRAM bandwidth or whole-program speedup. |
| STREAM | Compiler-generated prefetch/store choice, density and placement. If 80–95% is streaming and the matched local improvement is 1.10–1.25x: 1.08–1.23x. | [MB] lines 471–505: best triad 168.23 GB/s, density-sensitive collapse. No donor bandwidth is measured here; STREAM is not an automatic 1.25x vote, and its four operations are one program. |
| NPB CG | Sparse/indexed access, gather profitability, strict reductions, OpenMP work/wait balance. If 50–80% improves 1.2–1.5x: 1.09–1.36x. | [C] Results/Interpretation; [GAP] G11 is explicitly a hypothesis; [M3] runtime evidence. Split E7-09 into a measured sparse-loop proof and only then compiler work. |
| NPB EP | Scalar/control work and math-call vectorization if call and loop legality permit. If 30–60% achieves the measured double log/exp local range 1.20–1.57x: 1.05–1.28x. | [C] Results; [CS] line 21; [D14] point 2. Math presence is not hot time; measure both call share and binding before adding functions. |
| NPB MG | Vector stencil work, locality and runtime balance. If 50–80% improves 1.5x: 1.20–1.36x. | [C] Results; [M2] stencil evidence; [M3] libgomp defaults. Measure useful work versus synchronization before considering a new barrier. |
| NPB IS | Scalar addressing/branches, memory access and parallel runtime. If 50–80% improves 1.10–1.25x: 1.05–1.19x. | [C] Results show little proxy vectorization; [CHAR] C10 and [B] E7-13 supply concrete scalar leads. Generic vector tuning is unlikely to supply its missing gain by itself. |
| HPCG | Buildability first; then sparse memory access, reductions and runtime. If 50–80% improves 1.2–1.5x: 1.09–1.36x. | [C] lines 136–143, 152 record an OpenMP source issue. Its inclusion is conditional today; do not silently omit it from the denominator or count a failed build as a timing result. |
| zlib | Scalar branches, inlining/code size, alignment and optional PGO. If 50–80% benefits like the 19–21% time reductions in the successful PGO microcases: 1.10–1.20x; zero if those mechanisms are absent. | [C] Results/Interpretation; [CS] line 98. PGO is an optional track, not baseline credit. Proper zlib configuration may fix wrapper compilation without source changes ([C] lines 136–143). |
| SQLite | VM/control flow, calls, code locality and scalar memory operations. Same conditional PGO budget as zlib: 1.10–1.20x; no demonstrated corpus gain yet. | [C] lines 24, 127, 154, 184–190; [PGO] §Assembly; [CS] line 98. Fixed in-memory SQL must exercise a meaningful transaction mix, not only one easy prepared query. |
| PolyBench adi, held out | Budget 1.00x pending the sealed final evaluation; no program-specific optimization hypothesis or numerical uplift is justified. | [C] lines 27–31; [H] held-out rule. Keep eligibility/correctness checks separate from tuning information. |
| PolyBench durbin, held out | Budget 1.00x pending the sealed final evaluation, for the same reason. | [C] lines 27–31; [H]. No diagnostic-derived tuning recommendation is made here. |
| bzip2, held out | Budget 1.00x pending the sealed final evaluation, for the same reason. | [C] lines 25–31; [H]. General scalar changes may transfer, but that is unmeasured. |

These scenarios leave only a handful of evident candidate wins and several likely difficult votes. A pass could come primarily from capabilities already delivered since the donor, rather than new Sprint 12 work. Conversely, improving read bandwidth from 147.24 to 186.14 GB/s in one benchmark cannot supply the same factor to every program: that comparison combines density/prefetch settings and triad moves in the opposite direction ([MB] lines 479–500). Establish the donor-relative baseline before promising the target.

## Findings ranked by impact on M4

### 1. Freeze the scoring contract before tuning; S11-11 is necessary but insufficient

**Impact: critical; cost: small specification change, moderate harness work.** [H] specifies frozen inputs, paired launches and three repetitions, but not the final unit of aggregation, a confidence procedure, a whole-program timing boundary, or how two densities and multiple flag sets enter the median. [P] §5 still puts the full corpus in M5 while §6 requires it for M4. Recommend that the lead reconcile this wording: the fixed initial corpus is an M4 dependency; M5 widens it ([S13] Out of scope; [B] E8).

**Re-specify and split S11-11 into build/check support and a measurement-contract follow-up**, without discarding existing work. Freeze the following before E7-03:

- One vote for each of the 17 named programs. Treat input variants, repeated launches, STREAM operations and densities as subordinate observations. If the owner chooses a smaller eligible set because of a genuine blocker, decide and document it before tuning; retain the blocked row and report that M4's scope changed. Never compute an apparently complete median from successful rows only ([C] corpus table; [H] Results).
- A primary `-O2`/`-O2` pair with documented matching FP policy, source, work and resources. Report `-O3`, `-mphinix` and PGO separately until the owner chooses the M4 comparison track. `-mphinix` changes `errno` expectations, so it is not an unlabeled equivalent of default C semantics ([H] Compilers; [D14] point 2; [S13] item 1).
- Recommend 240 threads as the primary OpenMP resource condition under existing ADR-0009; show 60 and 120 as separate sensitivity panels, and one pinned worker for serial programs. An alternative application-density policy is reasonable only if frozen before tuning and applied equally to both compilers. Never compare each compiler's hindsight-best density or pool densities as extra programs ([D9] point 2; [D10] point 2).
- Fix program-specific timed boundaries and completed work: launch-to-exit wall time for whole-program reporting, with initialization/allocation and algorithm phases also reported when separable. Exclude staging, output transfer and independent validation from the timed application; apply the same boundary to both compilers. PolyBench/STREAM kernel timers and HPCG validity/performance output are secondary diagnostics, not interchangeable whole-program scores ([P] §6; [H] Inputs/Results; [C] lines 66–73).
- For repeated short tasks, report whether the number is fresh-process latency or repeated resident throughput. Do not hide initialization or turn a serial latency benchmark into 240 independent jobs and call it one faster program. [H]'s “every program multithreaded” clause conflicts with its serial-program pinning and unmodified-source requirements; clarify that existing algorithm parallelism is used, not rewritten by the harness.

### 2. Adapt ADR-0010 explicitly to separate executables and whole programs

**Impact: critical; cost: moderate, mostly harness/analysis.** Three repetitions and interleaving alone do not resolve known regime changes. ADR-0010 tuning compares builds inside one process on the same buffers; donor/runtime isolation makes that unsuitable as the universal whole-program protocol. Its microbenchmark 50–200 ms batching also cannot simply be imposed on [H]'s 1–10 s programs ([D10] amendment 2 points 1, 7; [H] Frozen inputs).

**Add an M4 measurement protocol approval to the S11-11 follow-up**, recommended as follows:

- Separate the under-two-hour first pass in [H] from the final gate. Use it for buildability, correctness and pilot duration. Fix a final budget before results: at least five independent paired launches per program, balanced AB/BA order, identical inputs/resources within a pair, raw chronological times retained. Choose one fixed extension block in advance for an inconclusive result; never rerun only unfavorable pairs ([D10] amendments 1–2).
- Use card-side monotonic wall time, verified affinity, exclusive benchmark windows, consistent first-touch/warm-up policy, and start/end environment records. Report clock/power policy, actual page mode, allocator/runtime settings, compiler/runtime revisions and flags. Keep invalid infrastructure/correctness runs visible with reasons; timing spread is a flag, not a reason to delete an inconvenient sample ([D10] points 1–5 and amendment 2; [MB] lines 446–460).
- Compute speedup within each launch pair, then a per-program median of those ratios. Report paired uncertainty and the median across program values. For uncertainty on the fixed-corpus median, resample paired launches within each program while keeping all 17 programs represented; do not imply that these convenience-selected programs are a random population sample. Freeze the method before the final run ([D10] amendment 2's ratio/interval principle; [C] lines 176–190).
- Report both `T_new/T_old` and its inverse. A 5% slowdown is `T_new/T_old > 1.05`, equivalent to speedup below about 0.95238, not exactly 0.95. Flag intervals overlapping the threshold as unresolved evidence. The owner must decide how uncertainty gates 1.25x; a conservative recommendation is a one-sided 95% lower bound at least 1.25x plus the per-program regression review. This would be an approved clarification, not an already-existing M4 rule ([P] §6).
- Require independent correctness evidence. A numerical array sum can hide compensating errors; compare complete outputs or deterministic reference/residual checks with predeclared absolute/relative or ULP tolerances and NaN/Inf handling. Retain NPB verification, HPCG validity, exact compression round trips and SQL expected results; also cross-decode compression outputs with the other implementation where feasible. Run a deliberately corrupted-result control through the harness checks. Donor agreement alone is insufficient: [M3] lines 32–33 and [CS] lines 19–21 document oracle/FP differences.
- Freeze NPB class, HPCG grid/work and PolyBench dimensions based on a neutral feasibility pilot, not whichever input maximizes a new-compiler gain. Record full commands and actual work. Use representative fixed compression content (mixed text/binary and redundancy) and a fixed SQL transaction mix. Include cache-resident and memory-resident sensitivity where useful, but do not change the primary input after tuning ([C] lines 35–39; [H] Frozen inputs).

### 3. Make baseline/profile/qualification the critical path, not transport or peak bandwidth

**Impact: high; cost: mostly ordering.** [S12] waits to write tickets until the harness and bandwidth sweeps land. Yet transport is outside the timed computation by ADR-0010, and [MB] lines 525–532 still need 42–83% improvements to reach the requested bandwidth targets. Nothing makes those targets prerequisites for comparing already-staged programs. The owner explicitly prioritizes transport ([S10T] opening); honor that operational priority without blocking corpus preparation.

**Move E7-03's first development-corpus baseline/profile slice into late S11**, once verified programs are runnable. Record top functions/loops and wall-time shares, vectorization decisions, x87/vector bridges, address/FP spills, assembly size and runtime wait/compute time. Extend to the full development set before selecting S12 implementations. Use existing sampling capability if adequate, or a bounded targeted profiler; do not make an AutoFDO recorder a profiling prerequisite ([AUTO] §2; [B] E7-03/E7-16).

Keep S11-02 gated on concrete acceptance and measured completion/integrity; it remains a placeholder in the open ticket ([T2]). The 1.67/1.35 GB/s figures are reported 64 MiB observations, not proof of every size/direction or symmetric saturation: S11-10 records a 1 MiB timing defect and a cleanup/lifetime bug ([S11] final measurements; [S10T] 15:25 lead note). Close those defects and define production fallback before rollout; do not demand more compiler speed from a transport study ([TR] §S11-02 implementation plan).

Create the referenced S11-12 batch ticket explicitly: [S11] lists it, but the reviewed `work/tickets/S11-*.md` snapshot has no S11-12 file. Give it the actual final compiler/runtime revisions, native checks, x86 and forward-port obligations, and a lead-owned card-time estimate. Separate “script staged” from “numbers validated”: [H] acceptance allows recorded build failures and a staged script, whereas [S11] goal 3 says every program runs.

### 4. Use bandwidth results to choose experiments, not blanket defaults

**Impact: high for memory programs; cost: medium to high if generalized.** Two-level prefetch and streaming stores already exist ([PF] §Rules; [BP] §Adopted). The new findings are more specific: read reaches 186.14 GB/s at 120 threads, matched 60/120 read settings differ only 1%; triad roughly halves at 120; NGO write emits no prefetch in this benchmark; RMW has no matched no-eviction control ([MB] lines 479–505). Thus “bandwidth winners by default” in [S12] is premature.

**Split S12 item 2** into (a) causal confirmation of the large class-specific effects, (b) compiler classification/code generation, and (c) runtime/user guidance. Start with E7-06 stream count, distance and read/write ownership; require a matched baseline, controls for density and actual page mode, a compiler-generated development-corpus loop, and no-regression cache-resident/reuse cases. Keep distances in bytes/lines through vectorization/unrolling ([PF] lines 13–28). Do not promote a handwritten benchmark's combined setting directly into a compiler heuristic.

Treat NGO store selection and eviction as separate changes: full-line/no-reuse evidence, fences and publication semantics remain visible; RMW cannot claim an avoided-RFO benefit for a line it already reads ([MB] traffic table and candidate 1). Keep exclusive store prefetch as a measured candidate rather than an unconditional best practice. Drop blanket eviction and automatic libgomp team downsizing from S12's committed scope; reconsider only with net whole-program evidence, preserving explicit user settings ([MB] candidates 2–4; [BP] line 27).

Huge pages are now observed in 48 sweep-2 configurations, superseding older “unavailable” notes, but a matched long-run page-size benefit is not established. Record actual mode and allocation overhead; do not make privileged memory configuration part of default compiler performance ([MB] lines 424–425, 508–509; [D10] amendment 1 point 5).

### 5. Give scalar code, pressure and locality explicit, bounded stories

**Impact: broad; cost: moderate for diagnosis/local fixes, high for new passes.** The corpus includes scalar compression/SQL and numeric recurrences, not just streaming vectors ([C] §Interpretation). The current scalar item bundles scheduling, inlining, branches and unaligned moves; each has a different proof and regression surface ([S12] item 3). Rank opportunities provisionally as below, then replace this order with E7-03's measured removable wall time. Benefit is conditional, not a promise.

| Priority | Recommended work and expected reach | Cost / decision rule |
|---|---|---|
| 1 | Scalar addressing/alignment and branch/call/code-size quality: E7-13 plus a focused E7-04. Most broadly relevant to scalar programs and numeric setup. C13's 4–8x access penalties and C10's branch cost are local mechanisms, not program gains ([B] E7-13; [CHAR] C10). | Small/medium separate stories. Inspect hot misaligned stores, spills, calls, hot `.text` and padding; compare inlining thresholds/branch shape only on identified hot paths. Never branch-eliminate a predictable test merely because CMOV is absent. |
| 2 | Loop locality/scalar replacement: add an E7-03-derived story for legal interchange, blocking, invariant hoisting and predictive commoning. Relevant to dense/stencil kernels and memory-carried recurrences ([SRC] I-2; [CHAR] C9 correction). | Medium if existing passes suffice; high for a new transformation. First verify pass availability in this GCC and diagnose dumps. Preserve dependence and strict FP order; charge temporaries, versioning and GPR/zmm pressure. |
| 3 | Scheduling with pressure: split E7-15 into x87 reservation/stack-pressure correction and vector scheduling at 1/2 threads. Vector loops gained 4–12%; pre-RA x87 lost 21–25%; at four threads variants were within 1.3% ([B] E7-15; [SCH] hot-loop spill table). | Medium. No global `-fschedule-insns` switch. Count spills/reloads and bridge costs, then pair on the affected programs at their relevant densities. |
| 4 | Density-aware unroll/accumulators: retain E7-12 after scheduling/pressure diagnosis. Existing low-density stream gains are 3–7%, not a broad 25% promise ([B] E7-12). | Small/medium. Jointly cost code size, address registers, live vectors and tails. Only reassociate reductions under an explicit compatible FP mode ([COST] lines 18–25). |
| 5 | Source-format scalar FP in zmm: add a bounded diagnosis/prototype decision for hot scalar FP, including comparisons, conversions and call boundaries. x87 multiply/divide and bridge costs justify investigation ([COST] lines 47–53; [GAP] G5). | High for a general path. First inventory existing support; require an end-to-end region win. Preserve x87 excess precision/long double and fenv requirements, account for all transfers; do not enable SSE or mask off real semantics. Defer a full scalar libm rewrite to M5 or later. |
| 6 | Sparse prefetch E7-09 and long-loop alignment E7-10: potentially valuable for CG/HPCG and proven unaligned streams, less universal ([B] E7-09/10; [C] Results). | Medium/high. Separate proof-of-benefit from implementation. Keep masked prologue/guard-page correctness; do not restore the x87 peeling that caused the old `-mphinix` loss ([B] E7-10; [CS] line 98). |
| 7 | Tiny remainders E7-19: retain only if profiles show frequent 1–2-element tails. The existing short regression matters, but an aggregate long-program median may barely move ([B] E7-19; [CS] line 98). | Small/medium targeted fix. Do not resurrect the rejected masked unpack/pack approach without new evidence. |

**Software pipelining:** keep swing modulo scheduling out of committed M4 scope. The collected GCC analysis found no i386 `doloop_end`, so enabling a flag is insufficient ([SRC] Supplement, lines 346–367). The corrected C9 experiment does show a residual memory-carried latency gap; it points first to scalar replacement/store motion, not proof that SMS is useless or automatically profitable ([CHAR] lines 415–429). Reopen only after a hot development loop still loses after existing unroll/scheduling, with an ADR-0006-compatible implementation plan. Likewise do not add a Graphite project or LTO as an assumed quick win: [GAP] §3 parks Graphite and [CS] line 274 puts LTO out of current scope.

### 6. Bring PGO/default selection forward; stop rediscovering completed runtime work

**Impact: medium/broad, essential to a fair final comparison; cost: small/medium reuse.** Instrumented PGO is not greenfield: libgcov and the train/use path exist ([PGO] lines 10–20), and native results show 19–21% less time in two microcases, no gain in two others, and only 0.94/1.01 time ratios when trained on another mix ([CS] line 98). S13 currently schedules both basic PGO infrastructure and final defaults immediately before the gate ([S13] items 1–2).

**Move E7-08's corpus integration into S12, with an S11 feasibility check**, and replace its infrastructure wording with “reuse/qualify atomic profiling and train/use workflow on complete programs.” Freeze distinct representative training and evaluation inputs, record missing/mismatched profiles, and compare a donor PGO build if claiming PGO competitiveness. Do not train on the held-out programs or make a GCC-KNC PGO versus donor plain `-O2` number the unqualified compiler headline ([PGO] variants; [H] held-out rule).

Start E7-14 with a small development-only `-O2`/`-O3`/current `-mphinix` screen once the baseline works; finalize the default at the end of S12. Permit only a bounded number of candidates and keep strict/default and `errno`-relaxed results distinct ([D14] point 2; [B] E7-14). **Move E7-18 autotune to M5**, not “if time allows” inside the final decision sprint: it multiplies builds/card runs and changes the selection procedure precisely when choices should freeze ([B] E7-18).

For OpenMP, keep E6-09 conditional. Spread placement, `delay` 128, 200 ms spin and the flat barrier already have native evidence; the proposed hierarchy was 1.5–1.7x slower, up to 2–2.5x at fan-out ([M3] runtime table; [B] E6-09). First distinguish barrier implementation cost from late-arriving workers, load imbalance, fork/join and allocator time. A large wait fraction does not mean a new barrier can remove it. WRF's 54–58% wait is context, not evidence about NPB/HPCG ([WRF] lines 20–21). Re-specify runtime work as a profile-selected remedy, not a promised hierarchical-barrier default.

### 7. Close correctness/ABI integration gaps early; keep intrinsics demand-driven

**Impact: high for trust/buildability, uncertain median gain; cost: small verification to large feature work.** FP64 vector div/sqrt and six v0 math functions already have native qualification, while the installed vector library lagged completed work in one prefix ([CS] lines 19–21, 85). [B] still describes FP64 support as future work. New math coverage is not the first M4 task.

**Add a prefix/compiler/runtime consistency prerequisite to S11-11**: record revisions, installed library set, actual linked runtimes and supported modes. Confirm whole-program use of already-qualified math, with its real call/repair/spill cost and legality restrictions. C/C++ `errno` and strict reductions can prevent vectorization even when an entry point exists ([D14] points 2–4; [DS] §4.1). Prioritize a missing function only when E7-03 identifies a material hot call; no relaxed math, FTZ or reassociation enters a default performance rescue ([D9] point 7; [BP] Denormals correction).

**Move E7-21's bounded long-double hazard audit to late S11/early S12**, before freezing correctness oracles. The `cbrtl` fault was real, but checking other entry points is still a hypothesis, not evidence that all libm is bad ([B] E7-21; [CS] lines 85–88). Scope fixes by a reproducer; do not convert it into a new libm project.

ABI compatibility is not implied by matching symbols: GCC-KNC's 64-byte vectors use zmm registers while the donor uses memory/hidden returns; Fortran descriptors also differ ([CS] line 99; [B] E6-02; [D14] point 1). Keep each compiler's whole program and incompatible runtimes separate. Include native ABI/runtime qualification in the final batch; never use mixed donor objects as a performance shortcut.

**Keep E6-05's full intrinsics implementation in M5**, except an identified build blocker for the frozen corpus. Its portable sources presently require no modern x86 intrinsics, and the donor lacks a complete KNC intrinsic interface too ([C] §Intrinsic suitability; [INTR] lines 29–31). A small facts-only demand inventory can precede M5, with the clean-room split of [D13] points 1–4/12. Defer broad headers, `__MIC__`, FFTW and ISPC acceptance together; defining `__MIC__` alone can select code whose required interface is absent ([B] E6-05b–e). No new third-party code is needed for this review.

### 8. Give the corpus a defensible scope and preserve its held-out value

**Impact: high for interpretation; cost: small policy, medium if widened.** The set has useful C/Fortran/C++, serial/OpenMP, dense/sparse, integer/FP coverage, but eight of seventeen votes are closely related PolyBench kernels and only a few exercise application control flow. It does not establish broad production performance, MPI behavior or LLM decode ([C] corpus table and §Intrinsic suitability). Keep it as a bounded M4 experiment, publish per-family diagnostics beside the unchanged program median, and reserve broad external claims for M5. Do not add programs after seeing which category wins.

**Strengthen [H]'s held-out separation to access separation.** The runner may build/check them, but tuning engineers should receive only readiness/failure status; diagnostics, profiles and timings go to the lead's sealed gate output until choices freeze. A `held_out` Boolean in a visible table is not enough to enforce [C] lines 27–31. A genuine correctness failure can be minimized/fixed; record the exposure and any loss of independence. If the one M4 retry is triggered by the held-out result, label the rerun an exposed-set confirmation, not a fresh held-out validation ([P] §6).

Resolve HPCG eligibility early: [C] records a `default(none)` source error, while [H] forbids corpus-source edits. Reproduce/classify it under both actual toolchains; if still blocked, the lead must choose an authorized minimal upstream compatibility fix, a different frozen version, or a formally revised corpus. Do not suppress diagnostics, remove OpenMP, or quietly substitute an easier program to make the harness green ([H] Rules).

### 9. Preserve M4 time for portability and independent qualification

**Impact: high schedule/release risk; cost: real lead/build/card capacity.** ADR-0006 requires x86 identity at batch/milestone boundaries and a milestone trunk build with T1/T2, not just a clean textual cherry-pick. The S10 drill reports 730 shared-i386 changed lines, 135 hunks and 14 conflicted files/27 hunks on its local master ref; it also records an unresolved upstream libgomp interface port ([PORT] S10-05 classification). These figures measure maintenance exposure, not proof of breakage or of current upstream compatibility.

**Make S13's final batch explicit and book it before optional work.** The lead runs x86 identity on the final head, refreshes the intended upstream refs, does the forward-port drill and required trunk checks, and records runtime portability findings separately. New shared middle-end/prefetch/scheduler work gets isolated hooks and targeted non-KNC checks in its batch ([D6] points 1–7). Do not count an older x86 pass as final-head evidence. The historical 2.81-minute `.cc` rebuild is useful planning evidence, but the same note warns a semantic `.md` edit can invalidate much more; allow build/install/lead-review time rather than budgeting only coding ([TIME] lines 37–58).

Book disjoint lead-run windows for corpus pilots, selected A/B experiments, the already-staged bandwidth/GEMV sweeps and final qualification. S11-09 alone stages 55 cases under an 89-minute cap; sweep 3 has 58 cases under its own cap ([GEMV] final lead note; [MB] lines 534–540). The final gate must not depend on spare time after unlimited sweeps. Keep hardware model claims bounded: [S13] asks validity on 3120/5110P/7120, but the current measurements are on 7120P and the existing notes explicitly limit the prefetch/store evidence to it ([CS] line 98). Topology/resource profiles can test behavior; they do not reproduce another card's bandwidth or establish its speedup.

## Proposed revised sprint outline

This is a replacement ordering for the lead to ticket, not an edit to the accepted plans. It retains their two-week caps, the S11–S13/M4 assignment in [MILESTONES], and [P] §6's one-retry decision policy.

| Sprint | Committed outcome and ticket changes | Exit evidence / scope limit |
|---|---|---|
| S11: make the experiment valid | Finish S11-10 defects; write real S11-02 acceptance and qualify transport. Split/re-specify S11-11 as findings 1–2; resolve HPCG and runtime-prefix readiness. Move the first E7-03 baseline/profile slice here, start E7-21's bounded audit, and perform a small PGO feasibility check. Complete the staged S11-09/S11-06 analyses in separately booked windows. Create S11-12. | A frozen corpus/inputs/flags/density/score policy; correctness-ready programs with visible blockers; first development timings and uncertainty/pilot budget; sealed held-out output; explicit batch status. A 264 GB/s result is not an exit requirement ([S11] Goal 2). |
| S12: remove measured whole-program costs | Complete E7-03; select at most three implementation themes by removable time and coverage. Likely candidates: focused E7-04/13 scalar work, E7-15 pressure/scheduling, E7-06 class-specific prefetch, or locality/indirect-access work if profiles beat those. Split each as above. Reuse E7-08 PGO on development programs; screen E7-14 early and freeze its contents at the end. E6-09 only for proven runtime loss. | Each accepted change has shape/correctness evidence and ADR-0010-style paired benefit on affected development programs plus the planned unaffected controls; development-corpus regression scan at the integrated head; batch portability evidence. New library/intrinsic/loop-pass projects need a measured blocker, not spare time ([S12] acceptance; findings 4–7). |
| S13: qualification and M4 decision | Freeze compiler, libraries, flags and runner; finish the final batch, execute E7-05 on all frozen programs including held-out, report uncertainty and every failure/regression. Diagnose an actual gate failure; perform only the one bounded retry allowed by [P]. E7-21 repairs already identified may finish before the freeze; no new autotuner or broad PGO infrastructure project. | Full results with known causes backed by evidence, final-head x86/trunk checks and explicit model limits; lead recommendation and owner go/adjust/stop. If the threshold remains unmet, follow [P]'s documented-limits path without redefining the denominator or labeling an exposed set held-out. |

M5 keeps full llama.cpp (E8-01), WRF (E7-20), demand-driven intrinsics (E6-05), autotune (E7-18) and broader corpus coverage ([B]; [S13] Out of scope). WRF entails rebuilt Fortran bindings/runtime dependencies and an estimated 4–6 tickets; that is not a quick M4 benchmark addition ([B] E7-20; [REUSE] reuse table).

**Memory bandwidth and LLM decode:** finish the bounded S11 GEMV study because it is an explicit owner objective, but maintain a separate result table for fp32/int8/fp16 weight bytes, conversion work, validation and complete GEMV time. Its results are pending; no current number establishes decode throughput ([GEMV] Deliverables and final lead note). Promote only generally applicable compiler/runtime findings through S12's corpus gate. Do not force quantization, a particular row width, special padding or hand-coded kernels into generic defaults. Actual tokens/s, logits/text correctness and non-kernel operators belong to E8-01's matched complete-program test ([B] E8-01). The 352 GB/s interface peak and 264–299 target remain research aspirations, not a measured channel ceiling or a multiplier for the M4 score ([MB] §§Peak, Gap).

## Questions for the owner, to resolve through the lead's tickets

1. Which comparison decides M4: strict matched `-O2`, matched recommended optimization settings, or a separately labeled PGO track? Recommend retaining `-O2` as the primary and publishing the others alongside it; explicitly approve any `errno`/FP-policy distinction ([H] Compilers; [D14] point 2).
2. Approve the 17 program units, primary density policy and uncertainty rule before tuning? Is HPCG mandatory if its unchanged source cannot build? Recommend no post-results exclusions and no pooling of density/input rows ([C] corpus table; [P] §6; findings 1–2).
3. With transport still the immediate priority, what fixed share of upcoming exclusive card turns belongs to the corpus versus bandwidth/GEMV research? Recommend protecting the baseline and final-gate windows even if the 264–299 GB/s aspiration remains open ([S10T] opening; [S11] Goal 2).
4. If held-out output triggers the allowed retry, accept an explicitly exposed-set confirmation, or require a newly designated independent validation set for a stronger generalization claim? That choice changes scope/time and must not be made by silently relabeling results ([C] lines 27–31; [P] §6).
5. Is 7120P measured performance with documented 3120/5110P limits acceptable for M4, or must native validation on those models be acquired? Resource-profile tests alone cannot meet the broader speed claim ([S13] item 1; [CS] line 98).
6. If M4 misses after the specified retry, confirm the existing release-with-limits policy rather than consuming M5's application/intrinsics budget pursuing a changed benchmark target ([P] §6; [B] E8-01).

## Source map

Links identify repository files; sections/line numbers above refer to the reviewed worktree snapshot. Repeated references to [CS] line 98 intentionally cite the dated consolidated card results rather than stale predictions in individual research notes.

[P]: ../PROJECT_PLAN.md
[MILESTONES]: ../../work/milestones.json
[B]: ../BACKLOG.md
[S11]: ../sprints/SPRINT-11.md
[S12]: ../sprints/SPRINT-12.md
[S13]: ../sprints/SPRINT-13.md
[H]: ../../work/tickets/S11-11.md
[T2]: ../../work/tickets/S11-02.md
[S10T]: ../../work/tickets/S11-10.md
[GEMV]: ../../work/tickets/S11-09.md
[C]: ../research/corpus-and-coverage.md
[CS]: ../../CURRENT_STATE.md
[M2]: ../research/m2-result.md
[M3]: ../research/m3-result.md
[MB]: ../research/knc-memory-bandwidth.md
[TR]: ../research/host-card-transfer.md
[D6]: ../adr/0006-portable-shared-i386.md
[D9]: ../adr/0009-knc-tuning-model.md
[D10]: ../adr/0010-knc-measurement-protocol.md
[D13]: ../adr/0013-knc-intrinsics-clean-room.md
[D14]: ../adr/0014-knc-vector-abi-and-vmath-binding.md
[DS]: ../research/knc-div-sqrt.md
[SM]: ../research/knc-small-matrix.md
[SRC]: ../research/knc-optimization-sources.md
[GAP]: ../research/knc-optimization-gaps.md
[CHAR]: ../research/knc-characterization.md
[COST]: ../research/knc-costs.md
[SCH]: ../research/s9-20-sched.md
[PF]: ../research/knc-prefetch.md
[BP]: ../research/knc-best-practice-review.md
[PGO]: ../research/s9-18-pgo.md
[AUTO]: ../research/s9-19-auto.md
[INTR]: ../research/knc-intrinsics-sources.md
[WRF]: ../research/wrf-input-2026-11-06.md
[REUSE]: ../research/wrf-imci-reuse.md
[PORT]: ../research/forward-port.md
[TIME]: ../research/gcc-16-timing.md
