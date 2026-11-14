# Code-style coverage and broad KNC optimization (S11-20)

Research snapshot: 2026-11-12. Recommendation: investigate scalar overhead first,
pressure-aware scheduling second, and legal reuse/locality third. Admit only the
parts supported by S11-15 development profiles. Alias-sensitive vectorization is
the next breadth candidate; class-specific prefetch is more conditional. This is
an investigation ranking, not evidence that any new theme has improved a program.

The [M4 definition](../M4-DEFINITION.md), [Sprint 12](../sprints/SPRINT-12.md) and
[ADR-0015](../adr/0015-m4-scoring-and-measurement.md) remain authoritative:
14 development programs select work; 17 frozen votes decide M4. Three themes are
the target, at most five, in one round. The extra checks proposed below never
enter that score. No code, corpus source, flags, plans or scoring rules change here.
No builds, benchmarks or card jobs were run for this research.

## 1. Styles are properties of code, not measures of programmer competence

Use six overlapping strata. A professional can write an untuned loop; a student
can call a tuned library. Count the mechanism exposed by each case, not its author's
job title. The following expectations are engineering hypotheses, with evidence
and limits identified; they are not estimates of population frequency.

| Stratum | Properties worth covering | Evidence and limits |
| --- | --- | --- |
| H: tuned HPC and numerical libraries | Long regular loops, explicit layouts, alignment, blocking and alias contracts; residual scalar setup, tails and register pressure | Reference BLAS provides inspectable numerical interfaces and loop variants [BLAS]. Already tuned code can leave little removable time. Its interface does not imply that the implementation is hand-vectorized. |
| S: domain-expert science, C and Fortran | Direct formulas, nested loops, strict reductions, runtime dimensions, library math and persistent arrays; sometimes no subsequent tuning | Prabhu et al. study scientific programming practices at one research university [Survey]. It supports treating scientific users separately from compiler experts, but is not a loop census or evidence that all scientific code is untuned. |
| N: educational, student and amateur styles | Naive nests, poor traversal order, raw pointers without `restrict`, AoS, tiny callees, globals, recursion, unpredictable conditions, broad use of `double`/`long`, sparse `const`, and I/O | Educational MD and the teaching renderer expose several of these properties [MD], [Ray]. They are expert-authored teaching examples, not sampled student submissions. No reliable frequency or time distribution for this entire list was established. |
| C: abstraction-heavy C++ | Templates, inline value types, iterators, `std::vector`, ownership wrappers and sometimes virtual dispatch | Garcia and Stroustrup's fluidanimate refactoring case study shows that abstraction can coexist with improved performance [Cpp]. Ray provides concrete container/dispatch and small value-type cases. Neither proves all abstractions are free. |
| G: generated code | Regular arithmetic expansions at one extreme; large branch graphs, state machines, repeated expressions and temporaries at the other | re2c generates control flow from lexer specifications [Gen]. This is evidence for generated parsers, not for all model-generated numerical code. Large generated numerical expressions remain a gap. |
| B: branch/call-heavy applications and libraries | Byte processing, parsing, pointer chasing, switches, helper calls, allocation and I/O | SQLite and zlib in the development corpus represent this stratum [Corpus], [Harness]. Their fixed inputs do not represent interactive services, all database queries or arbitrary compression data. |

Three studies constrain what can responsibly be inferred:

- Maleki et al., PACT 2011, evaluated 151 synthetic loops and ten applications
  with GCC 4.7, ICC 12 and XLC 11.01. Synthetic-loop vectorization ranged from
  45% to 71%, while few application loops vectorized [VecStudy]. This is historical
  evidence that synthetic success is insufficient, not a GCC 16 or KNC forecast.
- Gong et al., OOPSLA 2018, extracted over 1,000 loop nests from benchmarks,
  libraries and applications. Searching equivalent source transformations and
  vectorization settings improved 46.7% of their GCC cases by at least 1.15x
  ([Loops], abstract and sections 3-5). This motivates checking loop-form sensitivity.
  Extracted nests, search-selected variants and older machines do not establish
  whole-program gains, programmer skill levels or today's remaining headroom.
- The fluidanimate case replaces globals and low-level organization with C++
  abstractions and reports improved performance ([Cpp], sections 3 and 6). It is a
  source-refactoring case study, not a compiler-only experiment. It also cautions
  against declaring AoS universally inferior to SoA.

Evidence is particularly thin for skill-stratified aliasing, dynamic call density,
recursion and loop-trip distributions. Static loop counts cannot fill that gap.
Treat the proposed set as property coverage, not a representative survey.
`const` does not establish disjointness; C++ restricted pointers are an extension
[Restrict]. Fortran dummy-argument rules can provide stronger alias information,
but POINTER/TARGET and other exceptions require care [Fortran]. Neither language
nor absence of annotations proves that a particular loop must remain scalar.

## 2. Mechanisms, removable time and implementation boundaries

KNC is in-order, with four hardware threads per core, separate scalar x87 and
512-bit vector execution, and a GDDR5 memory system [Microarch]. The M4 primary
comparison nevertheless pins **one serial worker**, not four workers per core
[Harness]. Four-thread throughput must not be substituted for primary latency.
The [measured characterization](knc-characterization.md) supersedes architectural
guesses: the measured address interlock is about one extra tick at one thread,
hidden at four, rather than blindly applying the older three-cycle assumption.

For program p and a nonoverlapping cost bucket m, let F(p,m) be its fraction of
baseline launch-to-exit time, q(p,m) the fraction of that bucket actually removed,
and h(p,m) added checking/setup/spill time divided by baseline time. Then
`removed fraction = F*q - h` and `speedup = 1 / (1 - F*q + h)`.
For example, halving a bucket containing 20% of wall time removes 10% overall,
giving 1.111x before overhead. This is arithmetic, not a prediction for any style.
No credible F values for the six strata are available here; S11-15 must supply
program-level shares. The table supplies conditional bounds rather than invented
percentages of amateur or professional execution time.

Costs below: L = bounded KNC cost/hook adjustment; M = several interacting
decisions or legality cases; H = substantial transformation/semantic exposure.
They are relative engineering estimates, not promised days. The implementation
must fit the sprint's two-week cap including builds and qualification.

| Mechanism and exposed styles | Plausibly removable bucket, with quantitative limits where supported | GCC 16 route, cost and risk |
| --- | --- | --- |
| Address modes, induction variables, redundant extensions (H,S,N,C,G,B) | F is redundant address/update/setup time, not all loop time. q is unknown; may be zero when scalar work pairs with a vector op. A prior add-cost error changed IV choice and added a bound spill ([Costs], stencil regression correction). | Existing IV optimization plus KNC address/RTL costs [Gcc], [Costs], [Hooks]. L-M; dependency costs differ from independent throughput. Preserve pointer widths and overflow semantics. |
| Inlining, call overhead, scalar replacement of aggregates (especially N,C,G,B; small helpers in H,S) | F is avoidable call/argument/temporary traffic. Direct overhead can largely disappear for an eligible tiny call; callee computation remains. Secondary constant propagation/vectorization gains must be measured separately without double counting. Unknown external calls and recursion can yield q=0. | Existing inlining, IPA and SRA [Gcc]. M; text growth and longer live ranges can reverse gains. No new LTO project; bounded target costing rather than global inliner rewriting. |
| If-conversion, branch layout, code size (especially N,C,G,B; conditional H,S) | F is avoidable control stalls/front-end work. C10 measures 11.27 versus 6.22 ticks/branch for random versus fixed direction at one thread: about 45% of that microbenchmark's branch time, not 45% of application time. Extra predicated work subtracts from this. | Existing if-conversion/reordering with branch costs [Gcc], [Hooks]. L-M; preserve trapping, memory and FP effects. Predictable branches can beat branchless forms. More inlining/unrolling may hurt the 32 KiB instruction cache [Microarch]. |
| Store motion, scalar replacement, reuse (H,S,N,C,G; B only with proven private state) | F is redundant loads/stores and memory-carried recurrence stalls. C9's one-thread memory chain is 11.07 ticks versus 4.02 in registers: roughly 64% local headroom for that fixture, not a general rate. Unrolling alone recovered much less ([Characterization], C9). | Existing loop invariant/store motion and SRA [Gcc]; M. Escaping addresses, calls, volatile/atomic accesses and aliasing limit legality; increased live ranges create spills. |
| Interchange and blocking for traversal order (H,S,N,C; regular generated arithmetic) | F is avoidable cache/TLB/line-traffic time. If a region genuinely transfers eight times too many lines and is purely bandwidth-bound, correcting that traffic has an ideal 87.5% regional ceiling. This constructed bound needs measured traffic; recurrence and already good order give q=0. | GCC 16 has non-Graphite interchange, normally an O3 pass [Gcc]. M-H for bounded reuse; general automatic tiling/Graphite is out of Sprint 12. Dependence legality and each reduction's order must survive; cannot swap loops merely because strides look bad. |
| Alias analysis and runtime disjointness checks (especially C-language science in S, plus N,C; some H,G,B) | F is time in loops blocked by uncertainty rather than true dependence. Checks help disjoint long loops; overlap must retain the correct path. Short loops can lose more in h than they gain. No generic percentage follows from missing `restrict` [LLVM]. | Existing points-to/dependence analysis and versioning; M-H. GCC 16 O2's very-cheap vector policy can reject required runtime checks [Gcc]. A cost tweak alone is not proof of eligibility. Any KNC-specific default change needs explicit qualification at unchanged primary flags. |
| Reduction, AoS and tail vectorization (H,S,N,C; arithmetic G) | F is legal scalar arithmetic plus tail overhead. With equal scalar/vector instruction throughput, independent double/float arithmetic has width-only model ceilings of 87.5%/93.75% removal before overhead; these are not hardware speedup bounds. Strict FP recurrence may have q=0. C6's float add favors an aligned masked tail from n=2, but its thresholds do not generalize to arbitrary loops ([Characterization], C6). | Existing loop/SLP mechanisms and IMCI patterns [LLVM], [Costs]. M-H; AoS may need permutations or expensive gathers. Measured gather service grows from about 7 to 127 core cycles as touched lines go from one to sixteen [Characterization]. No automatic reassociation or layout/ABI rewrite. |
| Pressure-aware scheduling and bounded unroll (H,S,N,C,G,B) | F is exposed latency, loop control and avoidable spill chains. Spill/reload dependency latency is 12-13 ticks versus much cheaper independent throughput. C9's register-chain unroll 1 to 2 changes 4.02 to 3.02 ticks at one thread (25% locally); whole-program gains are F-weighted [Characterization]. | Existing scheduler and register/memory costs [Sched], [Hooks], [Costs]. M; stretching lifetimes can add spills and instruction-cache pressure. Expose actual transfers/helpers. No software-pipelining project; schedule first, unroll only when a remaining bucket justifies it. |
| x87 versus vector-scalar FP regions (H,S,N,C; numerical G) | F is eligible scalar FP execution. x87 divide costs about 38-39 ticks at one thread; this is not removable by declaring a vector substitute. Small regions can lose to x87/vector transfers; q is unknown even for add/multiply [Characterization], [Costs]. | H; requires operation/mode proof, ABI boundaries, rounding, exceptions, subnormal behavior and excess-precision analysis. Keep divide/sqrt scalar until proved. No implicit fast-math, FTZ, precision narrowing or hidden memory bridge. |
| Prefetch and full-line store policy (streaming H,S,N,C,G; selective B) | F is exposed memory latency or avoidable traffic. Prefetch can hide latency, not eliminate compulsory bytes or serial dependencies. Existing C5 results depend on stream geometry; C1 store choices are workload-dependent. Bandwidth saturation, reuse and short loops can produce q=0 or regress ([Characterization], C1/C5). | M-H; reuse existing infrastructure and measured KNC costs. Separate prefetch, NGO and eviction experiments; account for instructions, bandwidth, cache pollution, alignment and ordering. No blanket defaults based on a streaming kernel. |

For every row, an I/O-wait-dominated workload has a small F for compiler-removable
CPU work; if only 10% is eligible, even eliminating all of it caps speedup at
1.111x. A better asymptotic algorithm, fewer disk writes or an application data
layout redesign is not a compiler gain. `double` and 64-bit `long` are semantic
choices, not permission to narrow: KNC's narrower vector integer repertoire makes
wide-integer costing important [Microarch]. Integer reductions also require
correct overflow behavior. Strict ordered FP reductions must stay ordered;
parallel partial sums need separately authorized semantics [Costs].

GCC 16 documentation confirms existing mechanisms, not that every one fires on
the fork. [Gcc] is the versioned 16.1 manual; the repository describes a 16.2 base.
Before implementation, inspect that base's pass gates and KNC hooks. LLVM examples
explain mechanisms, not KNC availability. PR99954's upstream fix shows how alias
analysis can trade a correctness repair against lost copy recognition [AliasBug];
it is historical evidence of risk, not an assertion that this fork still has it.

[ADR-0006](../adr/0006-portable-shared-i386.md) bounds all rows: prefer existing
passes and KNC-local costs/hooks; shared i386 entries dispatch into KNC code,
IMCI vector patterns stay KNC-only, and no SSE/AVX/AVX512F flags are enabled.
Large shared/middle-end rewrites fail the bounded-scope test. Budget lead-run x86
identity and forward-port qualification for affected changes; a local benchmark
win cannot waive them. Historical cost/alignment repairs are already present
[Costs]; their benefits cannot be claimed again as Sprint 12 gains.

## 3. Frozen corpus coverage and a separate generality set

This inventory uses package/workload descriptions and development evidence only.
Held-out program identities are listed to account for the 17 votes; their loop
diagnostics, profiles and timings supply no selection evidence.

| Frozen programs | Useful coverage | Important limitation |
| --- | --- | --- |
| Development PB-gemm, PB-atax, PB-cholesky, PB-ludcmp, PB-jacobi-2d, PB-heat-3d | Dense nests, reductions, recurrences and stencils; H/S numeric properties | Six related development votes do not establish six independent styles. Fixed double arrays/dimensions do not cover raw-pointer uncertainty or short runtime-size distributions adequately. |
| Held-out PB-adi, PB-durbin | Two further frozen PolyBench votes | Sealed; no inference about their costs or likely response. |
| STREAM 5.10 | Regular streaming arrays and bandwidth, H/S | Four kernels within one program; not four votes, nor irregular application evidence. |
| NPB 3.4.2 CG, EP, MG, IS | Sparse science, random-number/math work, multigrid, integer sorting; C and Fortran | Curated benchmarks, not an untuned-scientist sample. Serial primary builds differ from their OpenMP panel. |
| HPCG 3.1 | C++ sparse numerical program with reference kernels, calls and setup | One C++ numerical package does not cover ordinary iterator/template/virtual-dispatch programming. |
| zlib 1.3.1; SQLite 3.46.1 | Byte/integer/control work, library calls, SQL parsing/VM/B-trees; B and some G | zlib's fixed 8 MiB buffer roundtrip is not a streaming filesystem workload; SQLite's fixed SQL transaction is not a database workload distribution. |
| Held-out bzip2 1.0.8 | One frozen library vote | Sealed; no source-pattern or timing-based selection. |

Versions and inventory come from [Corpus]; current inputs/timing come from
[Harness], `tools/corpus/roundtrip.c` and `tools/corpus/input.sql`. The old coverage
study compiled GCC 14.4 at O3 for Skylake AVX-512, not KNC: development examples
include 11/17 vectorized reported loop locations in STREAM, 28/1505 in SQLite,
and 13/134 in partially compiled zlib. These are neither dynamic fractions nor
primary O2 outcomes. Its partial HPCG/zlib builds also limit interpretation.
The newer harness documents the authorized HPCG fix and complete-program checks;
that does not retroactively turn compile-only counts into native results.

Eight of 17 votes are PolyBench. The corpus is useful across numeric and control
costs but weak on N/C/G diversity: no deliberately bad loop order, systematic
no-restrict/overlap pair, AoS/SoA contrast, small runtime trip-count sweep, recursive
teaching program, or generated arithmetic family. Globals occur but are not a
controlled dimension. It also lacks representative network/I/O services and
modern abstraction-heavy applications. Do not expand M4 to repair these gaps.

### Proposed unscored checks (no source imported or adaptation implemented)

Freeze cases, inputs, semantics and correctness checks before evaluating a theme.
Use small extracts with transparent drivers where whole applications are costly;
report both kernel and complete-driver time, including checks/setup consistently.
This is a predeclared secondary selection set: transfer evidence can affect the
choice of themes through G below, but never the M4 score. It is not held out.
Do not repeatedly tune against it or add favorable cases after results.

| Check / exact upstream edition | Case and missing property | License / acquisition status |
| --- | --- | --- |
| Q1: [Ray Tracing in One Weekend v4.0.2][Ray], `src/InOneWeekend/`: [hittable_list.h][RayHits], [sphere.h][RaySphere], [camera.h][RayCamera] | Preserve container range iteration, shared ownership, virtual hit dispatch, rejection branches and recursive rays. Fixed scene/rays; separately retain output-heavy full-driver timing. Tests C/N/B. | [CC0 1.0][RayLicense], including file notices. Tagged sources inspected. Keep plain CPU path and strict FP. |
| Q2: same v4.0.2, [src/InOneWeekend/vec3.h][RayVec] | New batch driver around original small double operators, using `std::vector<vec3>`: AoS/value abstraction, short lengths and scalar replacement. Explicitly a constructed driver, not an upstream loop. | Same CC0. One source family with Q1, never two independent-family credits. |
| Q3: [Burkardt MD, SC-hosted md.cpp][MD], main revision 2014-12-27 (`compute` 2008-07-15, `update` 2007-11-21) | Preserve raw pointer arguments, all-pairs nests, small dimension loops, `dist` calls, math and reductions. Separate compute/update observations; fixed particles/steps. Tests educational S/N properties. | File states GNU LGPL without a version qualifier in the inspected notice. Retain the source notice and applicable LGPL terms when staging. Dated source edition, not a tagged release; do not substitute the differently licensed current FSU webpage. |
| Q4: [Reference LAPACK v3.12.0][BlasRelease], `BLAS/SRC/dgemm.f` and required `lsame`/`xerbla` | Small Fortran N/T cases with padded leading dimensions: baseline structured science. Add separately labelled, independently written C traversal-order variants of matrix multiplication with the same per-output reduction order. These constructed kernels cover wrong order, no `restrict`, globals and wide indices without pretending they are student submissions. | [BSD-style three-clause LICENSE][BlasLicense] includes additional disclaimer; preserve exact terms and file notices. Tagged dgemm source inspected [BLAS]. Never substitute a tuned external BLAS implementation. |
| Q5: [smallpt, author's original 2008 edition][Smallpt], original `smallpt.cpp` | Existing Sphere AoS, global scene, tiny methods, scalar math and recursion; serial fixed seed/sample count. Optional bounded full render is a useful I/O-inclusive counterexample. | Author declares MIT and supplies a full distribution with LICENSE. Dated edition, not a tagged release; freeze original, excluding separately offered algorithmic variants. Shares rendering domain with Q1, so limited additional diversity. |
| Q6: reserve generated-code check, [re2c 3.1 release][Re2cRelease], proposed `examples/c/submatch/parse_etc_passwd.re` generated with that release | Small generated lexer over fixed valid/invalid records, branch layout, byte widths and code size. Tests G/B without another dense numerical kernel. | Upstream [LICENSE][Re2cLicense] states public-domain status and free distribution of generated programs. Release verified; tagged example/license retrieval failed. Verify the exact release's files/notices before admission; **Q6 is not yet acquisition-ready and earns no evidence credit**. |

For dated editions, stage the stated source and notices once in the shared area;
if the upstream file no longer matches its documented edition, resolve that before
running. No hashes or provenance manifests are needed. Preserve third-party code
and licenses in their own files; this proposal grants no permission to copy code
into the compiler. [ADR-0013](../adr/0013-knc-intrinsics-clean-room.md) applies to
vendor material; this study imports no Intel text, examples or headers.

For alias/vector claims, add explicitly constructed positive **and negative**
inputs: disjoint and legally overlapping buffers, lengths 0/1/below/at/above a
vector width, unaligned starts, and cache-resident versus memory-sized cases.
Do not pass overlap to a restricted-pointer routine or violate Fortran rules.
For FP, compare all live outputs with a predeclared oracle/tolerance while testing
special values separately where the function contract allows them; tolerance is
not permission to change FP semantics. Keep inputs opaque enough that optimization
cannot remove the work; inspect generated code. Repeated copies are not independent
style evidence. No case should be altered after seeing its winner.

The lead runs future card checks. Keep them short; a native program exceeding
about a minute must use its allocated CPUs as required by AGENTS.md, reporting
that parallel check separately from the one-worker primary comparison.
No performance result for Q1-Q6 is available. Large generated numerical code,
genuine student submissions and broad I/O services remain acknowledged gaps.

## 4. Selection rubric and present ranking

**Eligibility first.** A candidate needs a named general property, strict semantics,
a GCC 16 mechanism within ADR-0006, an explicit implementation/build/card budget,
and a hot removable bucket in development profiles. Reject name/dimension-specific
rules, concealed spills/helpers and relaxation masquerading as strict performance.
Before coding, name affected programs and two plausibly unaffected controls. Exit
requires correctness, intended generated code, paired before/after GCC-KNC benefit
and controls across all three settings, plus the integrated scan [Sprint12].
Donor-relative gains cannot establish the causal effect of a patch.

Record a scorecard `(B, G, F, D, U, C, R)`:

- **B, style breadth:** count strata H/S/N/C/G/B with confirmed useful effect,
  at most one point each. A style needs a matching source property, generated-code
  explanation and paired timing evidence; one example is limited coverage, not a
  population claim. Assign each case one primary stratum before runs; overlapping
  descriptive tags do not create extra points. Show the six-cell evidence matrix.
- **G, generality:** number of independent external source families confirming
  transfer into corpus gaps, capped at three. Q1/Q2 count once; related rendering
  examples do not alone establish several domains. Missing/unrun checks score zero.
- **F, development-family breadth:** count improved families among PolyBench,
  STREAM, NPB, HPCG, zlib, SQLite (0-6). **D** is improved development programs
  (0-14), retaining failures and regressions. This prevents six PolyBench wins
  from overwhelming independent application evidence in selection.
- **U, removable wall time:** report per-program `F(p,m)*q-h` estimates with
  uncertainty, and then paired measured reductions, separately by resource setting.
  Use the conservative cross-setting result. Avoid summing overlapping buckets or
  averaging kernel percentages as program benefit; report launch-to-exit results.
  For the U tie-breaker, take the median across all 14 development programs of
  each program's conservative fractional reduction across settings, retaining
  negative results. Missing evidence makes U unknown, never zero. Also show
  saved seconds so a large percentage in a tiny program remains visible.
- **C, total cost (1-3):** bounded local hook; interacting hooks/patterns; or a
  major/shared transformation. Include rebuild/install/qualification effort.
  **R, risk (1-3):** local cost decision; pressure/layout/legality interaction; or
  FP/ABI/shared dependence exposure. A risk score is no waiver of correctness.

After eligibility, rank lexicographically by **B, G, F, D**, then conservative U,
then lower C and R. Thus a verified cross-style gain beats a single-style outlier;
even a very large one-program gain cannot buy breadth. Require useful effect
outside timing noise rather than a positive point estimate. Freeze the evidence
threshold and run budget before measurement, retaining inconclusive results.
These priorities are a proposed selection policy, not a modification of M4 voting.

Today confirmed B/G/F/D are **0/0/0/0 for every proposed new theme**, and U is
unknown: neither old fixes nor static coverage prove a new change's benefit.
For investigation only, replace B/F/D with explicitly hypothesized Bp/Fp/Dp;
the following conservative shortlist names every counted development program.
Candidate lists are opportunities to inspect, not claims all are hot or will win.

| Rank / bounded theme | Hypothesized styles and development candidates | Bp/Fp/Dp; C/R | Evidence, generality check and decision condition |
| --- | --- | --- | --- |
| 1. Scalar addressing/control/call overhead, with code-size limits | H,S,N,C,G,B; PB-atax, PB-jacobi-2d, NPB-IS, HPCG, zlib, SQLite | 6/5/6; 1/2 | IV and alignment history [Costs], C10 [Characterization], control-heavy development proxy [Corpus]. Q1/Q3/Q5, Q6 only after acquisition. Split into bounded subchanges; do not bundle unrelated fixes to inflate B. |
| 2. Scheduling with pressure and visible transfers; unroll only afterward | H,S,N,C,G,B; PB-gemm, PB-heat-3d, NPB-CG, HPCG, zlib, SQLite | 6/5/6; 2/2 | Measured pairing, memory chains and spills ([Characterization], C9). Q2/Q3/Q5. Loses priority if S11-15 finds already hidden latency or no avoidable spills. |
| 3. Legal reuse/scalar replacement, then bounded locality | H,S,N,C,G; PB-gemm, PB-atax, PB-jacobi-2d, PB-heat-3d, NPB-MG, HPCG | 5/3/6; 2/2 | C9 memory recurrence and loop-form study [Loops]; Q2/Q3/Q4. Count only scalar replacement already legal under strict semantics. Interchange raises C/R to 3/3 if it needs shared dependence surgery. |
| 4. Profitable alias-sensitive vectorization, AoS and short tails | H,S,N,C,G; PB-atax, PB-heat-3d, STREAM, HPCG | 5/3/4; 2/3 | C6 and gather costs; source exposure [LLVM]. Q2/Q3 and explicit overlap controls. First establish O2 pass eligibility; strict recurrences and runtime-check overhead can eliminate the opportunity. |
| 5. Class-specific prefetch/store traffic | H,S,N,C,G; STREAM, NPB-CG, NPB-MG, HPCG | 5/3/4; 3/3 | C1/C5 do not support one global policy [Characterization]. Q3/Q4 plus resident/reuse controls. Requires actual exposed memory cost, matched page/resource controls and a compiler-generated development loop. |
| 6. Scalar FP regions on the VPU | H,S,N,C,G; PB-cholesky, PB-ludcmp, NPB-EP | 5/2/3; 3/3 | x87 costs are real but transfer/semantic proof is absent [Costs]. Q3/Q5. Defer unless a large strict, provably eligible region and bounded solution emerge; no automatic divide/sqrt replacement. |

Ranks 1/2 tie on hypothesized breadth; estimated implementation cost breaks the
tie. Ranks 3/4 differ on named development reach; 4/5 tie until cost; 6 has less
development-family evidence and higher semantic risk. S11-15 can reorder all of
them. Apparent generic applicability is deliberately insufficient for admission.
Select the portfolio by **marginal** confirmed coverage: once a style/family/cost
bucket is covered, another theme does not earn it again for portfolio choice.
Prefer three complementary themes; use a fourth/fifth only to close a demonstrated
gap within the cap. Fewer is preferable to unqualified or redundant work.

## Primary sources and local evidence

Reference labels below are used at the claims they support. External sources were
consulted on 2026-11-12. Studies describe their own populations and machines.

[Survey]: https://collaborate.princeton.edu/en/publications/a-survey-of-the-practice-of-computational-science/
[VecStudy]: https://www.microsoft.com/en-us/research/publication/an-evaluation-of-vectorizing-compilers/
[Loops]: https://iacoma.cs.uiuc.edu/iacoma-papers/oopsla18.pdf
[Cpp]: https://www.stroustrup.com/improving_garcia_stroustrup_2015.pdf
[Gcc]: https://gcc.gnu.org/onlinedocs/gcc-16.1.0/gcc/Optimize-Options.html
[LLVM]: https://llvm.org/docs/Vectorizers.html
[Hooks]: https://gcc.gnu.org/onlinedocs/gccint/Costs.html
[Sched]: https://gcc.gnu.org/onlinedocs/gccint/Scheduling.html
[Restrict]: https://gcc.gnu.org/onlinedocs/gcc/Restricted-Pointers.html
[Fortran]: https://flang.llvm.org/docs/Aliasing.html
[AliasBug]: https://gcc.gnu.org/pipermail/gcc-cvs/2024-May/402745.html
[Gen]: https://github.com/skvadrik/re2c
[Re2cRelease]: https://github.com/skvadrik/re2c/releases/tag/3.1
[Re2cLicense]: https://github.com/skvadrik/re2c/blob/master/LICENSE
[Ray]: https://github.com/RayTracing/raytracing.github.io/releases/tag/v4.0.2
[RayHits]: https://raw.githubusercontent.com/RayTracing/raytracing.github.io/v4.0.2/src/InOneWeekend/hittable_list.h
[RaySphere]: https://raw.githubusercontent.com/RayTracing/raytracing.github.io/v4.0.2/src/InOneWeekend/sphere.h
[RayCamera]: https://raw.githubusercontent.com/RayTracing/raytracing.github.io/v4.0.2/src/InOneWeekend/camera.h
[RayVec]: https://raw.githubusercontent.com/RayTracing/raytracing.github.io/v4.0.2/src/InOneWeekend/vec3.h
[RayLicense]: https://raw.githubusercontent.com/RayTracing/raytracing.github.io/v4.0.2/COPYING.txt
[MD]: https://people.math.sc.edu/Burkardt/cpp_src/md/md.cpp
[Smallpt]: https://www.kevinbeason.com/smallpt/
[BlasRelease]: https://netlib.org/lapack/lapack-3.12.0.html
[BLAS]: https://raw.githubusercontent.com/Reference-LAPACK/lapack/v3.12.0/BLAS/SRC/dgemm.f
[BlasLicense]: https://raw.githubusercontent.com/Reference-LAPACK/lapack/v3.12.0/LICENSE
[Microarch]: knc-microarch.md
[Characterization]: knc-characterization.md
[Costs]: knc-costs.md
[Corpus]: corpus-and-coverage.md
[Harness]: ../../tools/corpus/README.md
[Sprint12]: ../sprints/SPRINT-12.md
