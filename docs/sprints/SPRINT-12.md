# Sprint 12: remove measured whole-program costs (Milestone M4, part 2)

**In plain words:** We will finish with compiler improvements that make complete programs faster without
changing their answers. This comes after measurement so we can choose useful work and keep it affordable.
We are done when comparisons show that the changes help, checks for unintended slowdowns are complete,
and the combined compiler is ready for the final test.

**Status:** planned; adjusted by S11-19, 2026-11-12. Scope: [M4 definition](../M4-DEFINITION.md).
**Goal:** deliver bounded, general compiler improvements with measured development-program benefit and an integrated
candidate ready for qualification. This sprint does not promise that the unseen 17-vote gate will pass.
**Why now:** S11 supplies a valid donor baseline, profiles, runtime readiness and affordable candidates. Turn those
observations into code before S13 freezes choices ([first review], findings 3-7 and Proposed revised sprint outline).

## Theme A - select up to five broad implementation themes in one round, and prove each change

**What and why this sprint:** finish missing E7-03 development profiling before selecting affected work; rank by
removable strict-serial wall time, coverage, risk and build and card cost. Use only the 14 development programs;
held-out timings, profiles and diagnostics remain sealed. Owner 2026-11-12: one improvement round only (no repeated
rounds); three themes is the target, up to five if three cannot cover the corpus broadly; fewer is acceptable.
**Breadth is the selection rule:** prefer the themes whose benefit reaches the widest range of code styles, from
tuned professional code to naive amateur code (plain nested loops, pointer arithmetic without `restrict`, arrays of
structs, calls inside loops, globals, `double` everywhere, unhelpful loop order), using S11-20's coverage study and
the development profiles; a theme that helps one program style a lot ranks below one that helps many styles.

- Candidates: scalar addressing, branches, calls and code size (focused E7-04 and E7-13); legal locality and scalar replacement
  using existing passes; scheduling with pressure (split E7-15), then unroll (E7-12); class-specific prefetch and stores
  (E7-06). Sparse access, scalar FP regions, alignment and tails enter only if hot.
- Before coding, name the general code property, mechanism, removable time, affected programs, two unaffected
  controls and bounded experiments. Preserve strict FP order and visible spill, call and transfer costs.
- Prefetch and stores need matched page and resource controls, a compiler-generated corpus loop and cache-resident and reuse
  controls. NGO stores and eviction are separate changes; no blanket eviction or automatic team downsizing.

**Exit:** each accepted change passes correctness and generated-code checks. Paired GCC-KNC comparisons before and after the change
show whole-program benefit on affected programs and no regression on two unaffected controls, across all three settings. Report uncertainty
and failures. Keep donor comparisons separate: beating the donor does not prove this change helped. The integrated
development scan retains regressions and requires a known cause for confirmed slowdowns above 5%; unresolved
evidence cannot support an improvement claim ([first review], findings 4-5; [ADR-0015]).

## Theme B - qualify optional modes before choices freeze

**What and why this sprint:** use S11-17's feasibility result to reuse E7-08's atomic PGO training and use path on complete
development programs. Separate training and evaluation, report profile mismatches and build donor PGO for any PGO
competitiveness claim. A feasibility blocker limits this track instead of creating a new infrastructure project.
Run E7-14's bounded `-O2`, `-O3` and current `-mphinix` screen early; fix candidate count and budget first. Strict
`-O2` changes pass A; optional errno and FP behavior stays labelled. OpenMP E6-09 work requires measured runtime loss,
separating barrier cost, late arrival, imbalance and fork and join. It earns no serial credit, cannot create a fourth
implementation theme and cannot consume reserved qualification windows.
**Exit:** record each mode's frozen flags, semantics and results or explicit blockers by sprint end, without held-out
training or selection. Disclose the donor's absent OpenMP runtime; never substitute mixed runtimes
([first review], findings 6-7; [ADR-0015], Frozen comparison and eligibility).

## Theme C - integrate and hand S13 a qualified candidate

**What and why this sprint:** run the development-corpus regression scan at the integrated head; wins from isolated comparisons
can interact. Finish known correctness repairs before candidate freeze. Book the lead's native ABI and runtime batch,
x86 identity and sprint-end forward-port drill; shared changes get targeted non-KNC coverage in that batch.
**Exit:** compiler, library and runner revisions, flags, development comparisons, regression causes and batch results
are ready for S13, with unresolved failures marked as blockers. Supply final-gate duration estimates and booked
windows; an older batch or staged script does not qualify this head ([first review], finding 9; [ADR-0006], Decision 5-7).

## Capacity and boundary

**Cap:** two weeks from the first implementation ticket. The lead budgets rebuilds, installs, reviews and comparison
runs in all settings before committing to themes, reserves the integrated batch and sets an optional-work cutoff.
Defer over-budget or unsupported themes; retain the measured candidate and state its limitations.
Profiles model cores and memory on a 7120, not clock or per-core bandwidth or native 3120 or 5110 performance.
Donor headlines remain strict serial `-O2` with the disclosed SQLite donor assembly exception; only the identical
authorized HPCG fix changes corpus source. Optional panels never replace primary results.
**Out of scope:** new large passes, software pipelining, Graphite, LTO and new library projects without a measured
blocker and bounded admission; intrinsics, autotune, WRF, llama.cpp, corpus expansion and held-out tuning.

[first review]: ../reviews/2026-11-12-s11-s13-scope-review.md
[ADR-0015]: ../adr/0015-m4-scoring-and-measurement.md
[ADR-0006]: ../adr/0006-portable-shared-i386.md
