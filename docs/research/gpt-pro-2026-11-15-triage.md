# GPT Pro essays (2026-11-15): triage by scope, plan stage only

Input: two owner-provided GPT Pro essays, outlined item by item in `docs/research/inputs/gpt-pro-2026-11-15-outline.md`
(item ids E1.x, E2.x). Owner request (2026-11-15): sort them into the right scopes and size them; nothing pre-empts
M4. Every row below is a proposal. Evidence status: **verified** (our measurement, our source tree, or an R-number
read for this claim), **reported** (a cited source says so, not checked by us on our card), **unverified**,
**contradicted** (our evidence disagrees). R-numbers: `docs/research/knc-references.md`.

Effort: S under one ticket-week of engineer sessions, M one deep ticket, L several tickets or an ADR.

## Fact check of the KNC claims

| Claim (outline id) | Status | Our evidence |
| --- | --- | --- |
| Four contexts per core; one context never issues in consecutive cycles (E1.2a) | verified | R01, R16; measured S6-03; `gcc/config/i386/knc.md:6-11` |
| Dual issue U/V; at most one vector instruction per core cycle (E1.2b) | reported, partly qualified | Our model puts all vectors on U (`knc.md:12-17`); R02 pp.33-34 lists V-eligible vector store classes; S12-14 N01/B03 open |
| 32 zmm per context; 512 KiB L2 per core (E1.2c) | verified | R27, R01 |
| A demand miss blocks the issuing context; prefetches overlap and complete out of order (E1.2e, E2.1b) | reported | R06; not measured by us |
| 4-cycle vector add/mul/FMA latency; peak with 4 threads x 1 chain or 2 x 2 (E1.4c) | verified | S6-03; `knc.md:6-11`; ADR-0009 am.3 (K02) |
| L1 prefetch slots far fewer than L2 (E1.5a) | reported | R06 (research chip); S12-10 found our earlier slot claim overstated; our prefetch slots=10 unmeasured (S12-14 B08) |
| Streaming bandwidth may peak below four contexts (E1.5c) | reported | R08; our S11-05/06 sweeps measured thread counts for bandwidth |
| IMCI masks merge, no zero-masking; gather/scatter completion loops (E1.3e) | verified | R27; implemented in `imci.md` |
| No dependable KNC mispredict penalty (E1.3g) | contradicted in part | C10 measured +5.05 ticks per pseudorandom branch at one thread, +10.74 at four (`docs/research/knc-characterization.md:450`); miss rate not separated (S12-12 G07) |
| Pairing restricted by instruction length and addressing form (E1.4g) | reported | R02 p.56; S12-14 B03/E02 open |
| VPMADD231D: 16 int32 MAC lanes with load up-conversion (E1.7b) | reported | R27 (page not checked yet) |
| VPERMD: arbitrary selection among 16 dwords (E1.7c) | reported | R27 (page not checked yet) |
| SMS needs a doloop pattern and bails without `code_for_doloop_end` (E1.9c) | **verified** | `gcc/modulo-sched.cc:347` returns NULL when `!targetm.code_for_doloop_end`; no `doloop_end` pattern anywhere under `gcc/config/i386/` (grep, fork at knc b2ce6a9eebf). So `-fmodulo-sched` is a no-op on KNC today |
| GCC hooks for the KNC pipeline (E1.9b) | verified, partial | `knc.md:19-99`: automaton, units U/V/FP, 12 `define_insn_reservation`; `x86-tune-sched.cc:42` issue rate 2; `x86-tune-sched.cc:304-311` adjust_cost adds AGI and divides by density; KNC pair hook `x86-tune-sched.cc:608-688`, `i386-knc.cc:277` (S12-31). **No `define_bypass`, no KNC `TARGET_SCHED_VARIABLE_ISSUE`** |

## GCC-KNC compiler

| Item | Proposal | Evidence | Already covered by | Effort | Milestone | Deps |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | Make software pipelining (SMS) possible: KNC counted-loop pattern, then check which loops SMS transforms and whether final post-RA code is faster (E1.4e, E1.9c) | verified gap (row above) | none | S probe, L if adopted | M5 s14 probe | none |
| C2 | Complete the scheduler model: `define_bypass` for load-to-use and vector chains, pairing by length/addressing, cost of folded memory operands vs explicit loads, post-RA (sched2) checks (E1.4g, E1.9b, E2.4a) | partial (row above) | S12-14 B03/B04/E02 (open findings), ADR-0009 am.3 | M | M5 s14 | S12-14 E02 data |
| C3 | Latency-covering independent chains and unroll for scalar/strict loops, N >= ceil(L*R) (E1.4c, E1.4f) | verified basis | **S12-27** (deferred to M5) | M | M5 | S12-21 data |
| C4 | Strict reductions: interleave independent sums, vectorize across outputs instead of splitting sums (E1.4f) | consistent with ADR-0009 K02 | S12-27, S12-30/S12-40 (sparse) | - | M5 | - |
| C5 | Branch cost and if-conversion thresholds from measured branch loss, judged by cycles (E1.3d, E1.3g) | C10 measured; G07 pending | S12-12 G07 (staged), C10 note | S | M5 s14 | G07 result |
| C6 | Guarded specialization: unswitching, alias/stride/alignment versioning, tail separation, on unmodified N code (E1.3a, E1.6a) | GCC passes exist; KNC firing unverified | partly S12-19 triage tool | S measure, M fix | M5 | C9 cases |
| C7 | Devirtualization and indirect-call promotion; does LTO work for k1om (E1.1d, E1.6b) | unverified for k1om | S12-02 Q1 (ray tracer) as a case | S/M | M5 | C9 cases |
| C8 | Two-distance prefetch tuned jointly with tile size and context count (E1.5a-c) | reported | S11-05/06 (bandwidth), S12-22, S12-30 (deferred), S12-14 B08/B09 | - | M5 with S12-30 | - |
| C9 | AoS/SoA layout transformation (E1.6a) | research | none | L | later | - |
| C10 | Generated arithmetic: size sweep for spills and code size (E1.6c) | unverified | none | S (as cases in C9 row of corpus table) | M5 | - |
| C11 | Never insert NOPs for latency; schedule useful work (E1.9b) | practice | current practice | - | - | - |

## GCC-KNC runtime libraries

| Item | Proposal | Evidence | Already covered by | Effort | Milestone | Deps |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | Per-region thread density and persistent pinned workers (E1.5c, E2.4c) | reported/measured | **S13-02** (deferred to M5), ADR-0009 am.3 | M | M5 | - |
| R2 | Calibration stage that picks kernel variants, tiles, contexts, prefetch distance (E1.9d) | unverified | none (libknc_vmath has a fixed binding, ADR-0014) | M | M6 or later | R1 |
| R3 | Helper/prefetch threads per core (E1.5d) | research | none | L | later | R1 |
| R4 | AMAC-style interleaving of independent pointer chains, compiler or library (E1.5e, E2.3b) | reported (non-KNC) | none | M/L | later | C9 cases |
| R5 | Compiler-emitted checks plus calls into a linked runtime (E2.6a) | exists | libgomp, ADR-0014 vmath binding | - | - | - |

## Compute libraries and LLM kernels (GCC-KNC study; model work is PhiChat's)

| Item | Proposal | Evidence | Already covered by | Effort | Milestone | Deps |
| --- | --- | --- | --- | --- | --- | --- |
| L1 | Multi-row quantized GEMV reusing activation preparation; lanes across reduction vs across output rows (E1.7a) | unverified on KNC | partly S11-09 (weight-streaming GEMV bandwidth) | M | M5 s14 | S11-09 harness |
| L2 | Int32 MAC path with VPMADD231D and exact integer subtotals, K max abs(q) max abs(r) < 2^31 (E1.7b) | reported (R27) | none | S inside L1 | M5 | L1 |
| L3 | T-MAC-style VPERMD lookup-table kernel (E1.7c) | reported (R27), non-KNC results | none | M inside L1 | M5 | L1 |
| L4 | Turn library-vs-compiler gaps into compiler work when general (E2.4b) | method | none | - | M5 | L1 |

## PhiNix (OS and runtime)

| Item | Proposal | Evidence | Already covered by | Effort | Milestone | Deps |
| --- | --- | --- | --- | --- | --- | --- |
| P1 | Keep the existing KNC Linux kernel first; kernel work only for a measured limit (E1.10g, E2.5a) | method | owner moonshot plan | - | PhiNix | - |
| P2 | Four separate schedulers; a user-space runtime layer owns workers and variant choice (E2.0a, E2.1) | design input | none | - | PhiNix design | - |
| P3 | Affinity, page preparation, huge pages, interrupt placement via existing OS controls first (E2.2a, E2.5a) | reported | S12-16 playbook, hugepage note in for-the-other-agent | S | PhiNix | - |
| P4 | Check which KNC PMU events the installed MPSS exposes (E1.10c, E2.5a) | partly verified | S12-12 G06, R10, R11a-c | - | done/ongoing | - |
| P5 | Four agent tracks: compiler, compute library, runtime, measurement/platform (E2.4) | method | agent-team skill | - | PhiNix team setup | - |

## PhiChat (hand off only; its folder is read-only)

| Item | Proposal | Evidence | Already covered by | Effort | Milestone | Deps |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | Resolve quant format, shapes, strides, alignment at load/dispatch (E1.3b) | method | - | S | PhiChat | - |
| Q2 | Reuse activation prep across Q/K/V and gate/up; multi-row kernels (E1.7a) | unverified | GCC-KNC L1 study | M | PhiChat | L1 |
| Q3 | RMSNorm-then-linear reordering (FlashNorm) (E1.7d) | reported | - | S | PhiChat | - |
| Q4 | Tiled online-softmax attention for prefill; separate decode kernel; LFM2.5 conv/state profiling (E1.7e) | reported | - | M | PhiChat | - |
| Q5 | Exact speculative decoding, host draft model, hybrid-state rollback (E1.8a) | reported | - | L | PhiChat | - |
| Q6 | Lookahead decoding; continuous batching with separate latency reporting (E1.8b-c) | reported | - | M | PhiChat | - |
| Q7 | Time split: activation prep, unpack, accumulate, attention/state, sync, dispatch (E1.10d) | method | - | S | PhiChat | - |

## PhiWeather (WRF)

| Item | Proposal | Evidence | Already covered by | Effort | Milestone | Deps |
| --- | --- | --- | --- | --- | --- | --- |
| W1 | Profile WRF hot regions by the seven properties, not by "science" as one class (E1.1f-g) | method | S12-26 classification | S | PhiWeather | M1 |
| W2 | Vectorize strict column reductions across independent cells, never split sums (E1.4f) | consistent with ADR-0009 | S12-26, S12-27 | - | PhiWeather/M5 | - |

## Z840 host

| Item | Proposal | Evidence | Already covered by | Effort | Milestone | Deps |
| --- | --- | --- | --- | --- | --- | --- |
| H1 | Compare KNC with an optimized dual E5-2690 v3 path, same algorithms and numerical contract; apply host-benefiting changes to the host first (E1.10f) | none measured | S12-11 (setup research), S12-16 (tuning playbook) | M | M5 s15 (after the Z840 is running) | owner hardware |

## M4/M5 corpus and measurement method

| Item | Proposal | Evidence | Already covered by | Effort | Milestone | Deps |
| --- | --- | --- | --- | --- | --- | --- |
| M1 | Seven properties per hot region (control uncertainty, dependency depth, independence, memory behaviour, visibility, numerical contract, runtime overhead) drive optimization; classes drive coverage (E1.1g) | method | partly S12-19 triage tool, code-style-coverage section 2 | S | M5 s14 | - |
| M2 | Report four outcomes separately: unmodified-source compiler gain, runtime-assisted, algorithm/layout redesign, relaxed numerics (E1.10b) | method | none | S | M5 s14 | - |
| M3 | Per-region lower bound T >= max(dependency path, bytes/bandwidth, max work_r/capacity_r) (E1.2g) | method | code-style-coverage section 2 (removable fraction F) | S/M | M5 s14 | lead's model-first skill research (parallel) |
| M4 | Measure one context, one core, whole card, whole application (E1.10c) | method | ADR-0015 covers card and profiles only | S | M5 | - |
| M5 | Paired source-form cases for N, C, G (ordered reduction with uncertain aliases, AoS escaping/not, bad traversal order, pointer/iterator/functor/function pointer/virtual, generated arithmetic size sweep, generated state machine traces, one vs many traversals) (E1.10a) | method | partly S12-02 (Q1 virtual dispatch, Q2 AoS, Q4 traversal variants, Q5 recursion, Q6 generated lexer) | M | M5 s14 | - |
| M6 | PolyBench is regular-kernel evidence, not tuned-library evidence (E1.1b); split G into arithmetic and control flow (E1.1c) | agreed | code-style-coverage (H/S rows, G row already names both extremes) | - | duplicate | - |
| M7 | Expand M4 itself with these cases (E1.10a) | conflicts | ADR-0015 freezes the M4 set | - | M5 only | - |

## Out of scope or duplicate

| Item | Proposal | Reason |
| --- | --- | --- |
| X1 | Software thread-level speculation with buffered state (E1.8d) | Low expected value on KNC before cheaper items; later research |
| X2 | Value prediction with recompute validation (E1.8d) | Essay itself ranks it low; dropped |
| X3 | Instruction-level software reorder buffer (E1.5f) | Essay itself rejects it; dropped |
| X4 | Parallel prefix over parser state machines (E1.6c) | Research beyond M6 |
| X5 | Itanium lessons (E1.4b) | Background only |
| X6 | PGO of GCC itself vs of the application (E2.6b) | Already our model (one-flag application PGO) |
| X7 | "Middle end keeps information long enough" (E1.9a) | Too general to act on; covered case by case by C1-C7 |

Counts: compiler 11, runtime 5, compute/LLM 4, PhiNix 5, PhiChat 7, PhiWeather 2, Z840 host 1, method/corpus 7,
out or duplicate 7 (49 rows).

## Top 10 by expected value per effort

1. M2 + M1: four-outcome reporting and per-region properties in the M5 protocol (S): makes every M5 claim honest and
   says which layer to work on.
2. C1: SMS probe (S first): verified that pipelining is impossible on KNC today; an in-order core gains most from it.
3. C2: scheduler model completeness (M): no bypasses or folded-operand cost today; every scheduled loop depends on it.
4. M5: paired N/C/G source-form cases (M): the evidence gap behind the "broad support" claim.
5. H1: KNC vs host with equal algorithms (M): needed before any "faster through KNC" claim; Z840 arriving.
6. C5: branch cost from measured data (S): C10 already measured; only G07 is missing.
7. L1-L3: quantized GEMV kernel study, FP vs int32 MAC vs VPERMD table (M): owner's LLM-decode priority; shows
   compiler gaps.
8. M3: per-region lower bound (S/M): tells us when to stop; ties to the model-first skill research.
9. R1: per-region libgomp density (M): already ticketed as S13-02.
10. C7: devirtualization and LTO on k1om (S/M): the C class has almost no evidence today.

## Dropped and why

X2, X3 (the essay rejects them), X1 and X4 (research with no near-term KNC case), X5-X7 (informational or already
our practice), M7 (would change the frozen M4 set; moved to M5).

## Judged wrong or risky for KNC

- E1.3g says no dependable mispredict cost exists: we measured one (C10); what is missing is the miss rate (G07).
- E1.10a would expand M4; ADR-0015 freezes the M4 corpus, so these are M5 cases.
- E1.9c is right that SMS cannot run, but adding `doloop_end` is not enough: i386 has no rotating registers, so SMS
  needs modulo variable expansion and register pressure stays a risk with 8 x87 and 32 zmm registers; probe first.
- E1.5c ("fewer contexts for streaming") is a tuning result, not a rule against our all-threads test runs.
