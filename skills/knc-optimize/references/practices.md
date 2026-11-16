# Practices by limiting term

Read the rows for the diagnosed term, not this table as a checklist of changes.
The order within a group favors legality and existing evidence before uncertain
tuning. A verdict concerns the claim in that row only. `confirmed` and
`contradicted` refer to reported local card evidence; neither proves all inputs
or all cards. `untested` includes plausible advice with no matching local
comparison. `not applicable to GCC-KNC` describes a compiler/runtime mismatch or
an action already automatic, not a failed hardware experiment.

GCC mappings are the documented interface in `gcc-knc-flags.md`,
`knc-prefetch.md` and `knc-digest-2026-11.md`. Check the installed version's
driver expansion and emitted code. ICC mappings describe KNC-era compilers;
the separate ICC option-guide originals cited by the earlier project review
were not present in the supplied local corpus. The mappings below use the
available books, decks, STREAM recipe and MKL page instead. Do not treat an
experimental option in a deck as a current supported option.

## Scope and diagnosis

| ID / practice | When it pays or what it establishes | Source locator | Card verdict | GCC-KNC route | ICC route or difference |
| --- | --- | --- | --- | --- | --- |
| D1. Profile fixed useful work, then set a resource target | Avoids spending time on cold code or a wrong resource | R02 pp.153-159; R16 slides 7,49-53; R19 pp.261-265,356-360 | confirmed: S11-09's instruction and format accounting explains why weight GB/s alone misranks work; knc-memory-bandwidth.md, Native evidence and Executed instruction cost | Project timer/profile, assembly and model-first; knc-twin for supported one-core work | Compiler loop profiles and VTune in the historical sources; use tools available for the actual image |
| D2. Calibrate PMU events before using lane-use or stall ratios | Useful only if counters can be read with the required event semantics | R10 pp.5-7,11-16; R16 slide 52 | untested: documentation and driver maps do not establish local access or sampling accuracy; knc-digest-2026-11.md, practice M4-3 | Use the actual KNC event map and kernel interface; timer/assembly fallback | VTune support in a historical deck is not proof of current collector support |
| D3. Separate complete-job time from kernel and worker time | Startup, skew, completion and host transport can change the apparent winner | R02 pp.154-159; R19 pp.264-265 | confirmed: corrected completion envelopes and measured wall overhead; knc-memory-bandwidth.md, S11-06 Calibration | Calling project's measurement harness; keep completion in the timed region | Same measurement requirement; do not transfer published peak rates into an application result |
| D4. Choose native, offload or host execution from the whole workload | Serial work, transfers or limited card capacity can dominate | R16 slides 5-7; R17 slides 25-31; R19 pp.261-262,387-395 | untested: no matched host/offload comparison for the caller; system-tuning-playbook.md, step 12 | Native K1OM binary or an application-owned transport; compare complete paths | Historical offload directives and MKL automatic offload are additional mechanisms |

## Issue, arithmetic and vectors

| ID / practice | When it pays or what it establishes | Source locator | Card verdict | GCC-KNC route | ICC route or difference |
| --- | --- | --- | --- | --- | --- |
| V1. Enable the target's existing vectorization and scheduling | Establishes a sensible baseline before hand optimization | R02 pp.160,167-168; R16 slides 16-17,52 | not applicable to GCC-KNC: adding a separate enable-vectorization recipe is redundant with the documented optimized KNC target | Start with `-O2 -march=knc`; evaluate `-O3`; inspect `-fopt-info-vec-all` and assembly | `-mmic` and optimization level; historical `-vec-report`/optimization reports |
| V2. Express proven non-aliasing | Compiler dependence uncertainty blocks an otherwise legal vector loop | R02 p.162; R08 slide 12; R19 pp.303-305 | untested: no isolated local speed measurement for adding a restrict contract | C `restrict`, correct Fortran alias contracts, or explicit independent buffers; never assert a false contract | C restrict support and the documented alias options; global no-alias promises need stronger proof |
| V3. Align the allocation and prove alignment at each hot access | Removes avoidable unpack/pack paths when offsets retain alignment | R02 pp.161-162; R08 slide 15; R13 pp.1152-1153; R19 pp.302-303 | untested: implementation evidence alone is not an isolated heap-alignment card comparison | Aligned allocator; `__attribute__((aligned(64)))` or `__builtin_assume_aligned` only if true; statics/locals already use cache-line alignment | `__assume_aligned`, aligned directives; Fortran alignment flags |
| V4. Use safe masked tails or a guarded aligned version | Short/remainder loops can benefit without overrunning objects | R13 pp.1151-1153; R17 slide 37 | confirmed: knc-characterization.md, C6 tail table supports masked tails for the measured add loop, not arbitrary short loops | Automatic masked tails and target cost model; `-O3` for documented dynamic alignment versioning | ICC's guarded/masked vector paths; do not import safe-padding assumptions implicitly |
| V5. Promise extra padding only when the object contract provides it | May simplify a legal remainder access; otherwise changes memory safety | R13 pp.1152-1153; R02 p.162 | not applicable to GCC-KNC: the ICC assume-safe-padding switch is not provided; ordinary objects have no such contract | Use ordinary safe tails; an explicit padded layout requires source-level proof | `-opt-assume-safe-padding` in the cited edition, only with its allocation contract |
| V6. Choose contiguous lane work before using general gathers | Dense occupied lines can lower the full completion cost | R05 p.4 Table II; R14 pp.7-10; R15 pp.1616-1619 | confirmed: knc-characterization.md, gather_all versus gather_scattered rows, confirms density sensitivity, not a specific layout transformation | SoA/AoSoA, loop interchange or another independent lane axis where semantics allow; inspect full retry loop | Auto-vectorizer or intrinsics; gather presence alone does not imply profitable SIMD |
| V7. Use shuffles/broadcasts or another lane axis for small matrices | Conventional across-iteration SIMD may underuse useful lanes | R13 pp.1153-1156; R15 pp.1617-1619 | untested: no transferable local gain for those published small-matrix transformations | Source layout, independent work and constant permutations; check the chosen sequence | Multi-dimensional vectorization and explicit intrinsics in the papers; examples are not code to copy |
| V8. Keep loop-carried state in registers | A store/load on the recurrence delays dependent progress | R02 pp.32-33,165-166; R01 p.19 | confirmed: knc-characterization.md, corrected C9 memory-chain versus register-chain rows | Scalar replacement, invariant hoisting and narrower live ranges; inspect spills and calls | Compiler scalar replacement or source refactoring; same legality requirement |
| V9. Remove repeated control and unroll only enough to amortize it | Branch/address work consumes issue slots before a resource limit is reached | R02 pp.165-166; R16 slide 52 | confirmed: knc-characterization.md, C9 register cases improve with modest unroll; knc-memory-bandwidth.md, S11-09 unroll table shows no robust extra GEMV gain | Existing small-loop policy; `#pragma GCC unroll N` or a measured source specialization | Historical unroll controls and HLO report; larger unroll can spill |
| V10. Interleave independent recurrences when legal | Can cover a dependency without changing required ordering within a chain | R01 pp.19,23-24; R02 pp.165-166; R07 pp.139-140 | untested: C7 in knc-characterization.md ties at the measured density and does not establish a lower-density gain | Independent rows/work items; multiple sums only if reassociation is authorized; density parameter is a compiler hint | Equivalent source approach and threads-per-core code-generation hint |
| V11. Do not assume every vector op is U-only or every apparent pair is legal | Encoding, operands and dependencies affect scheduling | R02 pp.34,56 | untested: local tested pairs do not establish all encoding classes; knc-digest-2026-11.md, M4-2 | Inspect assembly and let target scheduling price actual classes; no opaque opcode workarounds | Same hardware restrictions; a historical mnemonic is not a current encoding authority |
| V12. Schedule around address dependencies | Helps only when the actual producer/consumer path stalls | R01 p.19; R02 pp.32-34 | confirmed: knc-characterization.md, AGI rows show a sequence-specific gap; no universal per-load penalty follows | Hoist address work or place independent operations between producer and consumer; verify emitted schedule | Same source transformation; compiler scheduling may already cover it |
| V13. Use FMA, reduced precision or approximate math only under the numerical contract | Arithmetic work can shrink, but results/flags may change | R04 slides 9,18; R19 pp.269-281; R27 pp.55-56 | untested: no blanket permission or application-wide accuracy/speed result follows from vendor advice | Explicit numerical policy; current divide/sqrt remain correctly rounded; `-ffast-math` is an opt-in semantic change | KNC-era FP modes and FTZ differ from GCC defaults; validate the requested result model |
| V14. Pack weights without materializing a widened matrix | Reduces weight bytes but increases arithmetic and conversion per line | R27 section 2.2.2 pp.30-33 and VMOVAPS pp.379-382 | confirmed: knc-memory-bandwidth.md, S11-09 matched format rows and disassembly; greater weights/s despite lower weight GB/s | Legal load expansion plus arithmetic; preserve scale, accumulator and accuracy semantics | Equivalent conversion/load interface; published interface does not establish application accuracy |
| V15. Use available vector math/library routes after checking call cost and semantics | Function calls can block vectorization; tuned libraries may help | R02 pp.167-168; R04 slide 18; R19 pp.427-443 | untested: practice-lessons.md records invalid historical timing batches; no general vector-math speedup follows | Documented vector library ABI; `-fno-math-errno` only when errno is not required; inspect call saves | KNC-era SVML/MKL interfaces; do not read or copy their implementations |
| V16. Replace Intel-specific language extensions with supported source constructs | Porting Cilk array notation is not a hardware optimization switch | R02 pp.165-168 | not applicable to GCC-KNC: the historical Cilk Plus/SDLT advice is not this compiler's KNC interface | Ordinary loops, supported OpenMP and explicit data layout | Historical Cilk/elemental-function routes depend on the compiler/runtime version |
| V17. Supply real trip-count information or specialize a common case | Can avoid a bad short-loop path without assuming all calls have the same size | R16 slide 45; R17 slide 37 | confirmed: knc-prefetch.md, Rules, reports the M2 short-loop prefetch regression and guarded path; not a universal gain from hints | Explicit size dispatch when justified, or profile feedback under project rules; no invented trip counts | Historical `loop_count` hints and loop profiling have version/platform limits |
| V18. Narrow integer width only after a range and overflow proof | May expose more useful lanes and simpler indices | R16 slide 47 | untested: no isolated local gain from integer narrowing | Use an appropriate fixed-width type; prove bounds, signedness and address arithmetic | Same source change; signed and unsigned arithmetic are not interchangeable |
| V19. Inline a hot call only when the full path gets cheaper | Removes call/ABI work but may increase code size and register pressure | R16 slide 55; R03 pp.15-22 | untested: no general local gain from forced inlining | Ordinary inlining first; function-level inline/noinline attributes only with inspected evidence | R16's statement-scoped inline pragmas are ICC-specific; not GCC equivalents |

## Bytes, cache, translation and overlap

| ID / practice | When it pays or what it establishes | Source locator | Card verdict | GCC-KNC route | ICC route or difference |
| --- | --- | --- | --- | --- | --- |
| M1. Make the hot traversal contiguous; tile for reuse and actual touched pages | Saves transferred lines or repeated data without exhausting translation/cache capacity | R02 pp.163-165; R19 pp.356-375; R01 pp.22-23 | confirmed: knc-characterization.md, corrected C4 identifies translation reach; knc-memory-bandwidth.md, S11-09 window table qualifies smaller-is-better | Legal interchange/blocking, source dimensions and stride; target heuristic capacity is not physical L2 capacity | HLO transformations or explicit source tiling; verify output and dependence order |
| M2. Fuse loops where it removes traffic; split only to remove a demonstrated obstruction | Changes reuse, vectorization, working set and stream count together | R02 p.164; R19 pp.380-384 | contradicted: the tested split-triad proposal loses; knc-memory-bandwidth.md, sweep-2 case 50; this does not reject all fission | Source fusion/fission with dependency proof; model added temporary traffic | HLO transformations or source changes; compare complete useful work |
| M3. Use NGO only for eligible cold whole-line output and preserve completion | Avoids fetching overwritten data when output is not immediately reused | R27 pp.388-398; R02 p.162; R09 p.4 | confirmed: knc-characterization.md, C1 completed stores; knc-memory-bandwidth.md, sweep-2 write cases | Automatic streaming stores for eligible large loops with loop prefetch enabled; inspect NGO and fence | Streaming-store auto/always controls; always is not a legality override |
| M4. Add two-level software prefetch only for a delivery gap | L1 lacks hardware prefetch; software may expose useful lookahead | R01 p.19; R02 p.161; R08 slides 28-30; R27 pp.641-656 | confirmed: knc-characterization.md, corrected C5, for those stream/residence cases | Automatic at optimized KNC levels; `--param knc-prefetch-l1-distance=N`, `knc-prefetch-l2-distance=N`; source prefetch for supported cases | Historical `-opt-prefetch` and far-first distance option; inspect units and generated hints |
| M5. Couple distance to stream count, consumption rate and worker density | Extra lookahead can consume cache and issue capacity before use | R08 slides 23-25,28-30; R16 slide 53 | confirmed: knc-memory-bandwidth.md, S11-09 hint table and sweep-2 triad density pairs; no single best distance | Match compiler density hint to actual execution; tune a focused candidate set, not every parameter | Threads-per-core hint plus prefetch controls; experimental R16 switch is not a supported modern spelling |
| M6. Prefetch indices and indirect data only when advance addresses exist | May overlap sparse misses; address discovery and hint work can outweigh gains | R02 p.161; R16 slide 53; R05 p.5; R27 pp.303-310 | untested: local gain from gather-prefetch is not established; published R05 observations qualify the mechanism | Inspect existing lowering; source prefetch only where valid; no assumed gather-hint speedup | Gather/scatter and prefetch controls vary by ICC release; interface facts do not imply useful overlap |
| M7. Use exclusive hints for reusable written lines only after a matched test | Ownership may arrive sooner; extra hints and contention can hurt | R27 pp.649-656; R16 slide 53 | contradicted: normal-store plus exclusive-prefetch candidate loses to NGO in its cold-output setting; knc-memory-bandwidth.md, sweep-2 cases 9/47; reusable-output benefit remains untested | No promise that `__builtin_prefetch` write intent maps to exclusive hints in the documented tree; inspect assembly | Direct hints/controls only if supported by that KNC-era compiler |
| M8. Treat cache eviction as a workload-specific choice | May preserve useful cache or may add traffic/issue overhead | R16 slide 54; R09 p.4; R27 pp.624-627 | untested: knc-memory-bandwidth.md, sweep-2 RMW rows lack a matched long no-eviction control | No automatic clevict in the documented streaming path; explicit changes need matching evidence | Early default eviction conflicts with tuned STREAM's disabled eviction |
| M9. Check actual huge-page backing before attributing a translation gain | Helps only if translation limits useful progress and allocations succeed | R01 pp.22-23; R09 pp.4-5; R26a heading Memory Allocation | confirmed: actual huge-page allocations exist in knc-memory-bandwidth.md, S11-06 sweep 2; S11-09 shows no large matched GEMV gain | Project-approved native allocation mechanism; inspect mappings and fallback, not just a requested flag | Native huge pages differ from `MIC_USE_2MB_BUFFERS` for pointer offload |
| M10. Reuse large allocations and keep enough capacity for runtime/services | Can avoid repeated allocation, zeroing and transfer setup | R19 pp.387-392; R26a heading Memory Allocation; R24a heading new_heap | untested: no isolated current native malloc reuse/arena-speed result; knc-digest-2026-11.md, allocator row | Allocate once and reuse; inspect RSS/reservations before changing allocator controls | MKL persistent-memory cap or compiler allocator options are not automatic native GCC controls |
| M11. Apply host first-touch NUMA policy only to a NUMA host | A host allocation may be remote from its workers or PCIe service thread | R19 pp.376-377 | not applicable to GCC-KNC: the cited socket-placement mechanism is not a card-local memory policy | On card, initialization can prefault/cache data; do not claim socket-local KNC pages | Same distinction; the Colfax example is a multi-socket Xeon host |

## Parallel span, runtime and transfer

| ID / practice | When it pays or what it establishes | Source locator | Card verdict | GCC-KNC route | ICC route or difference |
| --- | --- | --- | --- | --- | --- |
| P1. Measure density with affinity held explicit | Balances latency hiding against shared issue/cache/memory resources | R01 pp.19,23-24; R08 slide 24; R16 slide 51; R19 pp.341-355 | confirmed: knc-memory-bandwidth.md, S11-06 and S11-09 density tables, has opposite class-specific responses | Project-approved CPU set; supported OpenMP/GOMP placement; `knc-threads-per-core` changes code generation, not worker count | `OMP_NUM_THREADS` and KMP placement controls for Intel runtime |
| P2. Enlarge useful parallel regions and remove only redundant barriers | Amortizes team and synchronization costs while preserving dependencies | R08 slides 17-18; R18 pp.59-61; R20 pp.3-6; R23 p.33 | untested: published overheads are not a current-libgomp matched application gain | `parallel`, worksharing and `nowait` only after dependence proof | Same OpenMP constructs; blocktime controls are runtime-specific |
| P3. Balance work, using static scheduling as a regular-loop baseline | A lagging worker sets completion; dynamic dispatch has its own cost | R08 slide 18; R18 pp.65-66; R19 pp.321-340; R21 pp.7-8 | untested: no universal local fastest schedule | OpenMP `schedule(static)` for regular work; change scheduling only for measured imbalance | Equivalent OpenMP schedule controls |
| P4. Separate independent per-worker writes to avoid false sharing | Coherence traffic can dominate otherwise small updates | R18 pp.61-63; R19 pp.316-320; R22 pp.1-7 | confirmed: knc-characterization.md, C11 false-share/padding evidence; not proof of a physical-directory hash | Align and pad owned state to the sourced cache-line size; account for capacity cost | Same layout change; compiler alignment alone does not separate adjacent fields |
| P5. Expose independent outer work; control nested teams | Insufficient parallelism and library oversubscription limit scaling | R17 slide 32; R18 pp.64-65; R19 pp.329-340 | untested: no general local gain from collapse/nesting for the caller | Legal OpenMP collapse, independent tasks, explicit inner library thread count; verify team sizes | Similar OpenMP controls plus Intel library controls |
| P6. Tune waiting for actual arrival patterns and useful work | Team wakeup, barrier, imbalance and spin are different costs | R18 pp.59-61; R22 pp.1-7 | contradicted: the local grouped-barrier replacement was slower; knc-digest-2026-11.md, runtime grouped-barrier row; no universal spin optimum established | Keep established libgomp default; use its supported controls only for a measured problem | KMP blocktime does not configure libgomp |
| P7. Keep card data resident and reuse transfer registrations | Repeated marshaling/setup may erase native-compute gains | R17 slides 25-31; R19 pp.387-395; R25a heading scif_readfrom | untested: system-tuning-playbook.md, step 9, gives methods and external results, not a caller-specific completed-transfer speedup | Application-owned supported transport; include registration and completion; obey project transfer rules | Offload allocation/reuse and asynchronous transfer clauses; lifetime/completion still matter |
| P8. Use MKL-specific allocation, affinity and size advice only for MKL | Useful controls depend on routine and execution mode | R26a heading Memory Allocation; R02 p.168; R19 pp.432-443 | not applicable to GCC-KNC: MKL offload variables do not configure native GCC loops or libgomp | Use application/native allocation and runtime controls; an explicitly linked compatible library remains a separate option | KNC-era MKL native/automatic/compiler-assisted modes have different controls |
| P9. Preserve ABI and erratum requirements during optimization | Correctness precedes profitable instruction selection or system tuning | R03 pp.15-22; R12 pp.17-19,22-26; R27 pp.39,55-56,393-398 | untested: source rules are not a new native test of all caller boundaries or deployed firmware | Keep call-clobber saves, masks, fences, numerical state and fault footprint; consult pitfalls | Same hardware/ABI gates; compiler mode cannot authorize unsafe ordering |
| P10. Balance MPI ranks and host/card partitions from measured phases | Rank replication, communication and unequal processors can dominate | R02 pp.154,169; R16 slides 30-31,36; R19 pp.396-425 | untested: no universal local best MPI/OpenMP split | Caller-approved MPI/transport; use disjoint domains and verify actual placement; minimize critical-phase time | Intel MPI tracing and fabric controls are version-specific; one rank per core is a hypothesis, not a default |
| P11. Apply FFT-specific padding and density advice only to the named library | Library stride/size behavior differs from a general streaming loop | R26a heading Data Alignment and Leading Dimensions; R26a heading Number of Threads | not applicable to GCC-KNC: these are MKL FFT recommendations, not GCC loop heuristics | A compatible explicitly linked FFT library needs its own interface and measurements | MKL page specifies aligned data and precision-specific padded strides, size-dependent density, balanced affinity and TBB affinity controls; not locally tested |

## Source editions

All PDF locators above are printed pages unless a slide is named. Source facts
were read in these local originals (verified); published timings remain the
authors' results. Project-card conclusions above are reported. Any proposed
speedup is inference until measured. The register also states scope for sources
that constrain the method but do not recommend a tuning sequence.

- R01: Intel SSDG 328207-001EN, November 2012. Early architectural description,
  not stepping-qualified production timing. Not the unidentified shorter SSDG.
- R02: Rahman, Architecture and Tools, 2013. KNC description and examples with
  no single qualified production stepping. Tuning sequence pp.153-169.
- R03: K1OM ABI supplement, April 2012, v1.0. Interface independent of SKU.
- R04: Cornea, numerical computation deck, October 2013. KNC FP and Intel
  compiler semantics; no local production qualification.
- R05: Hofmann et al., medical imaging, 2014. Production-model 5110P;
  gather completion/residence Table II p.4; prefetch caveats p.5.
- R06: Zhenman Fang et al., TACO 2014, article 55. Explicit pre-production
  engineering sample (p.55:10); capacities/timings Table V p.55:19.
- R07: Jianbin Fang et al., ICPE 2014. 5100-series; exact model/stepping and
  production qualification unspecified. Latency/throughput pp.139-140.
- R08: McCalpin, IXPUG 2014 native optimization deck. SE10P with unspecified
  production qualification; configuration-dependent prefetch and density.
- R09: Raman, STREAM, updated October 2013. All results pre-production;
  explicit pages on p.4 and THP-stack results on p.5 are different setups.
- R10: Intel PMU 327357-001 rev.1.01, July 2012. Architectural events; some
  definitions explicitly refer to A0. Does not prove installed access.
- R11a/b/c: upstream Linux v3.10 and the Mpss-vt b76c20 driver/Makefile
  snapshots. Neither identifies the installed MPSS kernel. Implementation
  references, not a performance recipe.
- R12: Intel x100 specification update 328205-016, March 2015. Production
  stepping matrix and errata; applies ahead of conflicting early descriptions.
- R13: Tian et al., SIMD techniques, IPDPSW 2013. Methods pp.1151-1154;
  test configuration p.1155 does not identify a production-qualified model.
- R14: Saule et al., sparse matrix work from 2013. Explicit pre-release SE10P.
  The later PDF rendering date is not the experiment date.
- R15: Ma et al., non-contiguous access, HPCC 2015. Production-model 7120P;
  lane/layout methods pp.1616-1618, configuration/results p.1619.
- R16: Klemm, Optimization Strategies, 2013, 58-slide deck. KNC guidance
  without a qualified stepping. Keep distinct from R17.
- R17: Klemm, LMU micro-architecture seminar, December 2014, 40 slides.
  KNC core overview and offload case; KNL preview slides are not KNC facts.
- R18: PRACE/LRZ Best Practice Guide v2.0, January 2017. Mixed KNC/KNL;
  KNC OpenMP example identifies 7110, with stepping unspecified.
- R19: Colfax, Parallel Programming and Optimization, second edition,
  copyright 2013-2015. Both Xeon host and KNC examples; per-example scope.
- R20: Cramer et al., MARC 2012 OpenMP comparison. Explicit pre-production KNC.
- R21: Saini et al., NAS-2015-04. Production-model 5110P; EPCC results are
  that laboratory's runtime configuration.
- R22: Dolbeau, barrier address selection rev.1.40, April 2014. Production-model
  7120P. Physical-address experiments do not provide a portable directory hash.
- R23: Lang, ExaStencils thesis, April 2016. Exact card model and production
  qualification unspecified; perf analysis p.33 is application-specific.
- R24a/b/c: upstream glibc-2.21 allocator and i386 x87 log snapshots.
  Source mechanisms, not proof of installed MPSS behavior.
- R25a/b: MPSS 3.6.1-1 SCIF header and implementation snapshot, revision
  2850ead25b5c81ece2006d7ae06c2b3149175565. API/implementation scope only;
  does not establish the behavior of a different installed driver.
- R26a: Intel MKL 11.3 Update 4 KNC tuning page, 2016,
  GUID-7F67CA7F-0B2D-4584-AE90-63A64A58F0EC. HTML headings, no PDF pages.
  R26b: ICC 18.0 Linux release notes, Support Removed; KNC support removed.
- R27: Intel ISA 327364-001, September 2012. Early architectural interface;
  use R12 for applicable production errata. No instruction timing guarantee.

The source recheck and correction record lives in the originating project's
`knc-optimize-method.md`. That document is not needed to execute this skill.
