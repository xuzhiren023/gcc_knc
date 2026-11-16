# KNC optimization method recheck

S14-42, 2026-11-16. Research and portable skill; no new card job or GCC build.
The accepted red artifact test predates this note. This pass reads local
originals and the ticket's project evidence. It does not reproduce the
published experiments or claim fresh native qualification.

**Source gap:** the local source folders contain R26a's MKL tuning page and
R26b's ICC release notes, but not the separate ICC option-guide pages cited
by `knc-best-practice-review.md`. Their individual interfaces cannot be
rechecked from the supplied originals. See the final section before treating
the ticket's exhaustive source-recheck requirement as complete.

## Evidence and scope

R numbers and editions are defined in [knc-references.md](knc-references.md).
Verified means read in the source; reported means an existing project result
or a secondary citation; inference means our interpretation. A vendor's
measurement is not our card's result. Production model does not establish
exact stepping. R06/R09/R14/R20 are explicitly pre-production; R08's SE10P
qualification remains unspecified. The skill retains these distinctions.

The normalized practice/evidence table is
[practices.md](../../skills/knc-optimize/references/practices.md). Its stable
D/V/M/P row IDs join the source table below to each practice's condition,
source locator, one of the four ticket verdicts, local evidence and GCC/ICC
mapping. This avoids copying a second, drifting verdict for each source that
recommends the same practice. A confirmed mechanism does not imply a universal
setting. The source table also calls out the relevant local result directly.

Local evidence reviewed: `knc-machine.yaml`, `knc-characterization.md`,
`knc-best-practice-review.md`, `knc-optimization-sources.md`,
`knc-digest-2026-11.md`, `knc-memory-bandwidth.md`, `knc-prefetch.md`,
`knc-gather-reduce.md`, `system-tuning-playbook.md`, `practice-lessons.md`,
`gcc-knc-flags.md`, and model-first's method/levers. Historical proposals in
these files are not an inventory of the current compiler. The portable skill
cites unique basenames and sections; installed links stay within its folder.

## Source-by-source method

Page numbers are printed pages unless marked PDF. Page ranges below identify
the relevant method and constraints, not an assertion that every page of a
book was reread. PDF text was used to check locators; R16 slide 52 and R09 p.5
were also rendered to resolve the formula and table scope. HTML and source
snapshots have headings or symbols instead of invented PDF pages.

| Source and locator, including PDF position where different | Recommended order or contribution | Practices and our card status |
| --- | --- | --- |
| R01, SSDG 328207-001EN, pp.18-24 (same PDF pages), sections 2.1.1-2.1.5 | Architectural constraints, not an application tuning recipe: distinguish issue, dependencies, shared cache, translation and stream tracking before assigning costs. | V8/V12 confirmed only for the measured paths in knc-characterization.md, Full table/C9; M1/M4 confirmed in corrected C4/C5; P1 confirmed workload-dependently in knc-memory-bandwidth.md. Exact production queue capacity remains untested. |
| R02, Rahman, pp.153-169 (PDF pp.152-168); pp.32-34 (PDF pp.36-38), p.56 (PDF p.59) | Baseline a node; profile; set an attainable resource target; investigate system constraints; change compiler/source choices; consider suitable libraries; improve threading; balance host/card work; measure again. Only then tune cluster imbalance, communication and stack configuration. Table 10-1 p.160 is a set of conditional levers, not a command to apply all of them. | D1/D3 confirmed as useful accounting in S11-06/S11-09, knc-memory-bandwidth.md. V2/V3/V10/V13/V15, M10, P2/P3/P10 untested locally as general speed claims. V4/V8/V9/V12, M1/M3/M4/M5/P1 have the restricted confirmations in the practice table. M2's tested fission candidate is contradicted (sweep-2 case 50). V5/V16 are not applicable GCC switches. |
| R03, K1OM ABI v1.0, sections 3.2.1-3, pp.15-22; Fig.3.4 p.21 (PDF p.22) | ABI boundary, not an optimization sequence. Keep argument/result transport, saved state and call-clobbers in the cost and correctness model. | P9/V19 untested as optimization gains. knc-digest-2026-11.md, M4-8, identifies source behavior but does not make call saves optional. |
| R04, Cornea 2013, slides 9,18 (same PDF pages) | Choose and preserve the numerical contract before compiler FP/library options. Distinguish x87 precision/traps from IMCI flags and gradual underflow; division/sqrt are synthesized. | V13/V15 untested as universal performance advice. gcc-knc-flags.md supplies the current correctly-rounded divide/sqrt contract; knc-digest-2026-11.md leaves tiny-output behavior and exact qualification separate. No new native pass inferred. |
| R05, Hofmann et al., section V.D/Table II p.4, discussion p.5 | Inspect generated code and whole gather completion, then improve application memory behavior. Its unsuccessful gather-prefetch experiments qualify speculative hint advice. | V6 confirmed for local occupied-line endpoints, knc-characterization.md, gather_all/gather_scattered. M6 untested locally; published failures on a production-model 5110P are reported source evidence, not our measurements. |
| R06, Zhenman Fang et al., sections 4-6, p.55:10 and Table V p.55:19 (PDF pp.10,19) | Isolate capacity/latency experimentally before extrapolation. This is a measurement methodology on an engineering sample, not a production optimization recipe. | D3/M1 inform controls. Production queue and loaded-latency transfer is untested; knc-machine.yaml keeps these unknown. Do not turn sample MSHRs into a tuning default. |
| R07, Jianbin Fang et al., section 3.1 pp.139-140 (PDF pp.3-4), section 3.2 | Separate serial dependency timing from aggregate arithmetic and cache/remote-memory throughput. Sweep the actual resource rather than assuming one issue width. | V10 is untested as a general local benefit; local arithmetic latency/rate distinctions are confirmed by knc-characterization.md, Full table. Exact source hardware qualification remains unspecified. |
| R08, McCalpin IXPUG 2014, slides 6,12-18,23-30 | Pin for repeatability; inspect vector reports and alias/alignment; address parallel overhead; compare traffic with latency/concurrency requirements; tune prefetch and density; repeat measurements. Hot-cache and memory-resident paths need different hints. | D3/V6/M4/M5/P1 confirmed within local C2/C5 and S11-06/S11-09; V2/V3/P2/P3 untested as isolated local gains. knc-memory-bandwidth.md shows STREAM and GEMV density differ. Do not import the SE10P rate or queue count as a production ceiling. |
| R09, Raman STREAM, October 2013 update, pp.2-5 (same PDF pages) | Specific STREAM recipe: compile with tuned prefetch/stores and eviction off, spread over usable cores, use a large workload, compare page mechanisms. Explicit pages and later THP support are separate paths. It is not a general optimization order. | M3 confirmed by local C1 and sweep-2 stores; M5/P1 confirmed only per workload; M8 untested as a universal eviction rule; M9 confirms actual local huge mappings but not ordinary malloc promotion (knc-memory-bandwidth.md). All R09 tables are pre-production. |
| R10, PMU rev.1.01, pp.5-7,11-16 | Measurement interface and event units, not a recipe. Establish event meanings and counting constraints before interpreting ratios. | D2 untested for actual access/sampling on the caller's image. knc-digest-2026-11.md, practice M4-3, records missing access proof. R10 takes precedence over R01's counter overview. |
| R11a/b/c, KNC perf driver snapshots and version Makefile | Implementation evidence, not vendor optimization guidance. No PDF pagination. Existing index identifies event maps, constraints and kernel versions. This pass does not promote the snapshots into installed-kernel identity. | D2 untested for deployment; no source-only confirmation of usable PMU access. |
| R12, production specification update 328205-016, pp.17-19,21-26 | Apply the stepping matrix and exact erratum trigger before tuning affected paths. This is a correctness/system gate; it gives no universal speed recipe. | P9 untested as a fresh deployed-image qualification. CD9 is conditional, not all prefetch; CD26 is UC-only, not ordinary WB stores. knc-prefetch.md and knc-digest-2026-11.md preserve the scope. |
| R13, Tian SIMD, sections III-V pp.1151-1154 (PDF pp.3-6), results pp.1155-1156 | First legal masked short/remainder loops, then alignment/versioning and safe access footprint, then multi-dimensional lane choices. The paper's presentation order is not a universal optimization ranking. | V4 confirmed only for local C6; V3/V7 untested as the paper's local gains; V5 not applicable as a GCC switch. knc-characterization.md and knc-gather-reduce.md distinguish timing from fault-safety questions. |
| R14, Saule sparse kernels, sections 4.2-4.3 pp.7-10 | Count useful occupied lines and replicated input traffic; compare vectorization/density; distinguish bandwidth from per-core issue/latency. No generic streaming roof for sparse work. | V6 confirmed by local gather endpoints; a specific sparse layout or density optimum remains untested. knc-machine.yaml does not transfer pre-release SE10P constants. |
| R15, Ma non-contiguous access, sections III-IV pp.1616-1618 (PDF pp.2-4), results p.1619 (PDF p.5) | Identify AoS/SoA conversion and gather/scatter cost; consider inter-loop, intra-loop or hybrid lane assignment; compare useful throughput and legality. | V6's density mechanism confirmed locally; V7's particular layout/lane strategy untested. Published production-model 7120P speedups are not local gains. |
| R16, Klemm Optimization Strategies 2013, slides 5-7,14,16-17,30-31,34-47,49-55 | Choose execution mode and representative workload; profile/validate; inspect compiler/runtime reports; improve parallelism and vectorization; then use predicted algorithm, threading, compute and memory limits to select a lever. Details include alias contracts, interchange, trip counts, alignment, integer width, precision, density, pages, prefetch, eviction and inlining. | D1/V4/V8/V9/V12/V17/M1/M3/M4/M5/P1/P4 have scoped local confirmations. V2/V3/V7/V10/V13/V18/V19/M6/M8/M10/P2/P3/P5/P10 are untested locally as general gains. V5/V16 and historical experimental compiler syntax are not applicable GCC settings. See each practice row for its evidence. |
| R17, Klemm LMU 2014, slides 10-14 and 25-37 | Core facts support resource modeling. The offload case proceeds from hotspot/call-tree/loop analysis to transfer placement, kernel parallelism, legal interchange and guarded aligned variants. KNL preview slides are excluded. | D4/P7/P5 untested as local whole-application gains; V4 has narrower C6 evidence; M1/V2/V3 need per-program proof. The case study does not authorize numerical reorderings in a different program. |
| R18, PRACE/LRZ v2.0, KNC sections 13.2 pp.56-66 and 15.1.1 pp.69-73 | Select placement/density, distinguish team setup from barriers, avoid false sharing, budget private storage, expose nested work only if needed, balance scheduling. STREAM separately compares allocation, hints, stores and density. | P1/P4 confirmed per local density/C11 rows; P2/P3/P5 untested as current-runtime gains; P6's grouped-barrier proposal contradicted (knc-digest-2026-11.md). M4 has C5 evidence, but no universal distance or store-gain magnitude transfers. |
| R19, Colfax second edition, pp.261-265 (PDF pp.287-291); sections 4.2-4.7 pp.267-425 (PDF offset +26 in these sections) | General arithmetic/call optimization, profitable vectors, scalable threading, memory locality, then communication; measure at each stage. Roofline at pp.356-360 chooses the relevant resource. Later chapters discuss libraries, not a requirement to use vendor code. | D1/D3, V4/V8/V9/V12, M1/M3/M4/M5 and P1/P4 have narrow local confirmations. Other applicable transformations are untested in the practice matrix. M11 is not applicable to card-local NUMA; its first-touch example pp.376-377 is host-only. |
| R20, Cramer OpenMP 2012, pp.3-6 | Compare placement, parallel overhead and useful workload scaling; amortize synchronization. Pre-production KNC, not present libgomp. | P2/P3 untested for our real application/runtime; no timing transfer. |
| R21, NASA NAS-2015-04, sections 6.5.1-6.5.2 pp.7-8 | Separate synchronization construct overhead from scheduling overhead; regular-work baseline and imbalance remain different questions. | P2/P3 untested as local application gains. P6's local grouped-barrier regression cannot be replaced by external EPCC results. |
| R22, Dolbeau rev.1.40, sections II-III pp.1-7 | Control physical addresses and core pairs, then test communication/barrier designs. Physical placement is an experimental variable, not a portable page-color formula. | P4 confirmed for local padding; P6's replacement contradicted by the real runtime comparison. knc-characterization.md C11 explicitly withdraws universal ring-distance/page-color conclusions. |
| R23, Lang thesis, section 4.3 p.33 (PDF p.41) | Inspect residual OpenMP time after high-level kernel transformations; use application profiling to decide the next effort. | D1/P2 are methods; the thesis's wait fraction and perf availability are untested on our workload. No local gain inferred. |
| R24a/b/c, glibc-2.21 snapshots, allocator symbols and x87 log entry | Implementation references, not KNC optimization recipes. Existing audit separates reservation, resident use and deployed library identity. | M10 untested for installed allocator performance. The log source does not identify the local libm symbol; pitfalls retain the runtime-identification requirement. |
| R25a/b, MPSS 3.6.1 SCIF interface/implementation | API/lifetime and completion constraints, not a measured throughput ranking. Use registration/reuse and completed transfer accounting without pretending a different driver implements an identical path. | P7 untested as a new local speed result; source-level completion is a correctness constraint. |
| R26a, MKL 11.3 Update 4, Memory Allocation; Data Alignment and Leading Dimensions; Number of Threads; OpenMP Thread Affinity; TBB Facilities | For the named library/mode: consider pages and retained offload allocations, FFT alignment/padded leading dimensions, size-dependent teams, affinity and TBB partitioning. These are conditional controls, not an order for arbitrary loops. | M9 confirms local explicit mappings, not this library's gain. P8/P11 are not applicable as native GCC controls. M10's performance remains untested. Later MKL balanced-affinity advice differs from R02 p.168's routine-specific compact/scatter suggestions. |
| R26b, ICC 18.0 release notes, Support Removed | Compatibility gate: this release removes KNC. It is not the missing historical option-guide documentation. | Not applicable as a KNC tuning compiler; do not infer IMCI support from newer Xeon Phi names. |
| R27, ISA 327364-001, pp.30-33,39,55-56,297-310,379-398,624-627,641-656 | Instruction semantics constrain any candidate: masks, conversion, completion, store eligibility/order and hint meaning. No timing or general optimization sequence. | V14/M3 confirmed for measured local GEMV/store configurations; M6/M8 remain untested locally. P9 remains a gate. The ISA supplies no production queue/service constants. |

## What order the evidence supports

The sources do not agree on one unconditional list of knobs. The portable
entrypoint therefore uses: measured hot work; model/bound; dominant term;
matching practice; correct card comparison; stop. It calls model-first rather
than creating a second detailed modeling framework. It calls installed
knc-twin for supported one-core work and preserves status, assumptions and
unsupported forms. Full-card rates are not obtained by multiplying a simulated
core rate. The worked example uses existing S11-09 full-card evidence only.

Before selecting an instruction optimization, inspect profitability and
legality, then remove avoidable issue/bridge/control work. Corrected C9 favors
register-resident recurrences over trying to hide memory chains by unrolling.
Before selecting a memory knob, reduce avoidable bytes or occupied lines and
then diagnose the delivery gap. Before selecting a runtime knob, identify
imbalance, synchronization and actual team placement. Before offloading, count
completed transfers and host serial work.

The source-backed input table is copied from `knc-machine.yaml`, with its
unknowns and qualifications. It does not fill missing 3120 or smaller-card
bandwidth values from memory. Stops at the bound, within noise or below the
ticket's remaining-gain threshold are workflow policy, not new measured
hardware limits. The method creates no permission to use the card.

## Disagreements and precedence

| Question | Resolution |
| --- | --- |
| SSDG edition and timing | Use recovered R01 328207-001EN, not the unidentified shorter guide's pages. R12 controls applicable errata; production local timing controls our measured instruction paths. R01's internally inconsistent L2 wording does not yield an isolated service rate. |
| Thread density | R16 slide 51 suggests intermediate densities; R08 slide 24 and R09's STREAM recipe favor sparse workers in their settings. Local S11-06 triad and S11-09 int8 GEMV have opposite responses. No edition wins globally; match workload, compiler, hints and placement. |
| Prefetch distances and units | R09 p.4 describes cache-line distances, far then near. R02 p.161 describes vectorized iterations; R18 p.71 describes its experiment's iterations. Current GCC parameters are lines per stream. No number transfers without the emitted stream step. C5 corrected rows supersede its aliased/noisy original claims; S11-09 overrides any belief that deeper always helps. |
| Cache eviction | R16 slide 54's early default and R09 p.4's tuned no-eviction recipe differ. Local long RMW comparisons lack a matched no-eviction case. Verdict untested, not a universal adoption of either policy. |
| THP | R09 p.5 really does contain later THP-stack results; the obsolete claim that all results precede THP is already corrected in the digest/index. Local explicit huge-page success supersedes the old local no-huge-pages snapshot; ordinary malloc promotion remains unknown. |
| FP policy | R04/R27 define architectural semantics, not permission to use ICC's fast defaults. Current gcc-knc-flags.md documents correctly-rounded FP64 divide/sqrt since S10-09. Source presence is not a replacement for numerical qualification. |
| PMU | R10 and event definitions take precedence over R01's overview and R16's mislabeled lane-use ratio. Installed access remains untested. |
| MKL affinity | R02 p.168 suggests routine-specific compact/scatter choices. R26a's later 11.3 Update 4 page recommends balanced across domains. Use the documentation for the actual library version, then measure; neither sets libgomp affinity. |
| First touch and physical locality | R19's second edition identifies the NUMA example as a Xeon host. KNC private-cache locality does not imply socket-local page allocation. R22 controls physical address as well as core pairs; local C11 cannot prove ring distance irrelevant. |

## Locator corrections from this pass

- `knc-best-practice-review.md`, indirect-prefetch row: Rahman's relevant
  passage is chapter 10 p.161, PDF p.160, not the broad chapter 11 citation.
  The ICC GUID in that row remains reported until its original is supplied.
- `knc-optimization-sources.md`, ISA no-read-store locator: the two NR forms
  occupy R27 pp.388-392; pp.388-391 omitted the continuation of the fp32 form.
  The historical text is retained with the corrected range.
- R02 chapter 10's printed pages are not related to PDF pages by the early
  chapter's offset. The method table records pp.153-169 as PDF pp.152-168.
  R19 pp.261-265 are PDF pp.287-291. These are new precise locators, not a
  global offset rule for either book.
- R16 slide 52's lane-use label has a total-instruction denominator in the
  original PDF. This is a source formula problem, not an extraction or page
  error. The skill flags it instead of reproducing a misleading metric;
  the correct active-lanes interpretation follows R10 event definitions.
- Existing R09 p.5, R19 first-touch and R01 edition corrections were confirmed
  and retained; they were not rediscovered local performance results.

No vendor prose, tables, example code or pseudocode were copied into these
artifacts. The automatic overlap test covers the ticket's R01/R16/R27 texts;
it is a limited lexical check, not proof of research completeness.

## Missing originals and remaining review

The two supplied directories were inventoried, including a recursive search
for guide/GUID names. Their R26 files are the MKL tuning page and ICC release
notes. The following separate ICC pages are cited by the earlier review but
have no recovered original in those directories and no individual R entry:

| Reported interface | GUID suffix in knc-best-practice-review.md | Treatment here |
| --- | --- | --- |
| Gather/scatter unroll | 9AE10FC5-BB6C-4F22-A346-E84CDD79BF33 | Indirect-prefetch mechanism uses R02/R05/R27; exact option not advertised as verified. |
| Allocator controls | D0078E73-2EAA-4944-8D67-81E7D2D7CD26 | Native allocator performance remains untested; no compiler allocator default invented. |
| Dynamic alignment | C00A2B11-E69B-4822-890F-5A35E60F5F45 | Legal alignment/versioning uses R13 and current GCC documentation. |
| Prefetch/vector pragmas | 3A086451-4C82-4BB1-B742-FF93EBF60DA3; 2B528C72-29B4-4DBC-8B91-EE4D1A03A850 | Version-specific interface remains reported. |
| MIC predefined macro | 401EDB00-AD07-4085-97EB-7C68BA42A713 | No unsupported macro-compatibility promise added. |
| Accuracy controls | 8B4176A9-E645-4581-AF32-CEF3F2054EF3; 0ADDE233-4E78-4AEC-B35A-79C580D70316; 1D11B099-72A0-4DD0-A0F7-BA050887B639 | Only R04's general FP-mode facts used; no guessed exact option mapping. |
| FTZ | 3A5C3E47-250D-4178-A0D4-6C4ACDDA5EB8 | R04 supplies the numerical qualification; no new timing claim. |
| Safe padding | 0543CD1D-3E04-45F0-A546-555C7B1C52E0 | Historical interface is independently discussed in R02/R13; separate GUID page still unrechecked. |
| Streaming eviction | 44E1F4AB-6749-4DD6-9553-75A89AC01769 | R16/R09 establish the conflict; no guessed later default. |
| Scalar alignment | 7E3E5C78-3F3B-4746-8C2D-A912EE1D6B38 | No unqualified vendor restriction imported; local C13 is labeled not run. |

The host/Phi folder also contains additional sources registered under the
playbook's separate B/C/H/T/R namespaces, including a family datasheet and
partial MPSS extracts. They are not new R-numbered sources in
`knc-references.md`. This pass uses the playbook as project evidence and does
not introduce unsourced hardware constants from those extra files. Its host
BIOS, Haswell, MPI-cluster and modern host software recipes are outside this
KNC code-tuning skill's default actions. A broader original-source sweep of
that register needs the lead to clarify scope and assign R entries where
required by AGENTS.md.

Remaining question for the lead: supply/index the missing ICC originals, or
confirm that the available R02/R04/R13/R16/R26/R27 coverage with explicitly
reported GUID gaps is the intended acceptance scope. The skill and host
checks can be reviewed independently of that source-acquisition decision.

## Host validation

The ticket's six artifact checks have each passed. The initial Cygwin run
passed structure/frontmatter, practice evidence, portability and links, but
the overlap check stopped on the ISA extraction's Windows-1252 bytes. R01 and
R16 decode as UTF-8. The test now tries strict UTF-8, then strict Windows-1252;
it neither drops bytes nor changes tokenization or the shared-run threshold.
Only that failed check was rerun, and it passed against all three originals.

- Artifact run: `S14-42-green`; log
  `.work/_state/logs/S14_42_green-20261116-164425.log` (five passes, one encoding error).
- Corrected overlap check: `S14-42-overlap`; log
  `.work/_state/logs/S14_42_overlap-20261116-164625.log` (pass).
- Installer smoke: `S14-42-install`; log
  `.work/_state/logs/S14_42_install-20261116-164646.log` (pass, relative staged root).
  The earlier absolute-path attempt failed in Cygwin's parent-directory access;
  it did not install the skill in the user's home.

All checks used the project Cygwin Python via `tools/run.py`. No passing check
was repeated. The install copy is temporary and is removed after inspection;
the lead retains responsibility for the default user installation after review.
