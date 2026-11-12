# Milestone M4: what "broad optimization" means for GCC-KNC

**Status:** adjusted by S11-19, 2026-11-12. [ADR-0015] is the accepted scoring authority.
This page defines engineering scope without changing that contract.

## The question M4 answers

M1-M3 established scalar/ABI, vector and language/runtime capabilities. M4 asks whether those capabilities
deliver useful whole-program speedups over MPSS GCC 5.1.1. Kernel gains alone cannot answer that question
([first review], Evidence boundary and findings 1, 8).

**Broad optimization means general compiler improvements evaluated across a fixed mix of programs:**

1. **Whole programs:** 17 votes spanning numeric, stencil, sparse, integer, compression and database work,
   timed from launch to exit. Sources stay unchanged except the authorized, identical HPCG shared-list fix.
2. **Different costs:** consider scalar/control flow, addressing, FP, calls, code size, memory, runtime setup
   and vectors. Profiles choose the work; M4 does not require a new feature in every category.
3. **Transferable improvements:** select by code properties and costs, never benchmark names, fixed dimensions
   or source rewrites. Preserve correctness, strict FP and ABI; account for spills, calls and transfers.

This is a bounded milestone, not proof of broad production performance: eight votes are PolyBench. Publish
family diagnostics alongside the unchanged program median; MPI and LLM decode need later evidence
([first review], findings 5, 7, 8).

**Pass rule:** strict serial `-O2` GCC-KNC versus GCC 5.1.1, **with the SQLite donor assembly exception**:
the donor uses its highest assembling level, frozen before timing; every headline discloses it.
On each of full 7120, `--profile 3100` and `--profile 5100`, the median of all 17 program speedups needs a
one-sided 95% lower bound of at least 1.25x. Correctness must pass; a confirmed slowdown above 5% needs a
lead-reviewed known cause. Missing/invalid data or unresolved regression intervals prevent a pass.
Profiles model cores/memory, not clock or per-core bandwidth: these are 7120 resource-profile results,
not native 3120/5110 measurements. `-O3`, `-mphinix`, PGO and GCC-KNC-only OpenMP remain labelled panels.

## What work belongs in M4

Classify each proposed ticket before accepting it:

- **Enable or qualify the experiment:** identify the readiness, correctness, measurement or portability obligation
  it closes. Acceptance proves that obligation; a harness, oracle or ABI repair need not demonstrate speedup.
- **Improve primary performance:** name a hot cost in the 14 development programs, a general mechanism,
  expected removable whole-program time and a bounded implementation/measurement budget. Require correctness
  and code-shape evidence, paired before/after GCC-KNC benefit on affected programs, and no-regression evidence on two controls,
  across all three settings. Keep donor-relative competitiveness separate from the causal effect of a change.
- **Qualify an optional mode:** name the panel, its proof and budget. It cannot rescue the serial score or displace
  required qualification. Held-out diagnostics never select ordinary tuning.

| Work | Admission and exit evidence | Boundary |
|---|---|---|
| Harness, donor/runtime setup, profiles (S11) | Frozen equal work, independent checks, sealed held-out data, usable profiles | Infrastructure enables tuning; no speedup required |
| Scalar, locality, scheduling/pressure, prefetch/stores, unroll, calls/code size (S12) | Profile-selected general remedy; correct shape and paired whole-program benefit with controls | At most three implementation themes; no kernel-only justification |
| Strict defaults (S12) | Same proof as a primary performance change | No implicit fast-math, FTZ or reassociation |
| PGO, `-mphinix`, OpenMP (S11 feasibility, S12 qualification) | Labelled semantics/resources and measured panel results; separate PGO training/evaluation | No primary credit; donor PGO required for PGO competitiveness |
| Libm/ABI/prefix hazards and batches (S11-S13) | Reproducer or contract obligation, correctness/portability evidence at the relevant head | Bounded repairs, not a replacement library/runtime project |
| Final measurement and decision (S13) | Complete ADR-0015 gate, regression causes and owner decision | One repair retry; no changed denominator or threshold |

New large passes, Graphite, software pipelining, LTO or new library coverage are not committed M4 projects.
A measured blocker permits bounded investigation, not automatic admission of a large implementation; the lead
must fit it within the themes and sprint cap. Intrinsics, autotune, WRF, llama.cpp and corpus widening stay in M5.
These rules follow [first review], findings 3-9; [ADR-0006] governs shared-backend qualification.

## Work beside M4 and sprint handoffs

Transport rollout and bandwidth/GEMV research retain separate outcomes and card windows. Working staging is
required, but DMA rollout or a bandwidth target is not: transfers are outside primary timing. Research enters M4
only through the admission rules ([ADR-0015], Timed boundaries; [first review], finding 3).

- **S11 - measure:** valid experiment, sealed held-out readiness, development baseline/profiles and budgeted shortlist.
- **S12 - improve:** at most three measured themes, integrated regression evidence and frozen optional modes.
- **S13 - decide:** final-head qualification, complete gate, at most one repair retry and owner decision.

[ADR-0015]: adr/0015-m4-scoring-and-measurement.md
[ADR-0006]: adr/0006-portable-shared-i386.md
[first review]: reviews/2026-11-12-s11-s13-scope-review.md
