# Sprint 13: qualification and the M4 decision (Milestone M4, part 3)

**Status:** planned; adjusted by S11-19, 2026-11-12. Scope: [M4 definition](../M4-DEFINITION.md).
**Goal:** a defensible M4 pass or documented miss on the frozen experiment, followed by the owner's decision.
**Why now:** S12 supplies a measured, integrated candidate and frozen optional modes. Test whether those choices
transfer to all 17 programs; new optimization projects would consume the independent check
([first review], findings 8-9 and Proposed revised sprint outline).

## Theme A - freeze and qualify the actual candidate

**Achieve / why this sprint:** close previously identified correctness repairs before freeze; record compiler,
libraries, installed/linked runtimes, flags, runner/scorer, inputs, checks and schedule. Preserve S11's frozen work
and scoring policy. Book and complete the final batch before optional panels or gate interpretation.
**Exit:** native ABI/runtime checks and x86 identity at the final candidate head; a forward-port drill on refreshed
upstream master/release refs; trunk with the port built and passing T1/T2. Record portability findings. A textual
merge or older head's pass is insufficient; unresolved qualification failures block readiness
([ADR-0006], Decision 5-7; [first review], finding 9).

## Theme B - run the complete frozen gate

**Achieve / why this sprint:** E7-05 measures all 17 votes, including adi, durbin and bzip2 after choices freeze.
Use strict serial `-O2` GCC-KNC versus the donor, **disclosing SQLite's frozen donor assembly-level exception**.
The identical one-line HPCG fix is the only corpus source change. No successful-row-only score is permitted.

- Apply [ADR-0015]'s six balanced independent launch pairs per program/setting, card-side launch-to-exit timing,
  independent correctness and retained raw attempts/validity reasons. Pilot times never enter the gate.
- Score full 7120, `--profile 3100` and `--profile 5100` separately: each 17-vote median needs a one-sided 95%
  lower bound of at least 1.25x. Every program passes correctness/regression review; confirmed slowdowns above 5%
  need a lead-reviewed diagnostic cause. Missing/invalid data or unresolved regression evidence cannot pass.
- Use the predeclared six-pair extension across every program/setting only when ADR-0015's interval rule triggers
  it; retain all twelve pairs. This sampling extension is distinct from the one compiler-repair retry.

**Exit:** complete results, per-program/family diagnostics, uncertainty, every failure/regression and its cause;
labelled `-O3`, `-mphinix`, PGO and GCC-KNC-only OpenMP results or explicit unavailable-panel status.
Profiles model cores/memory, not clock or per-core bandwidth: no native 3120/5110 speed claim follows
([ADR-0015], Launch schedule, Arithmetic, Held-out access; [first review], findings 1-2, 8).

## Theme C - one bounded repair opportunity, then an honest decision

**Achieve / why this sprint:** diagnose an actual gate failure and, if needed, use the owner's one bounded repair
retry on the same corpus/protocol. A repair invalidates the old candidate: freeze the new head, refresh affected
qualification including final-head x86 evidence, and rerun the complete gate. A held-out-triggered repair is an
**exposed-set confirmation**, never fresh held-out validation. Infrastructure recovery follows ADR-0015's recorded
lead decision and complete replacement-block rule; preserve aborted results, never relabel correctness failures.
**Exit:** the lead presents evidence/recommendation; the owner records go / adjust / stop. On a pass, the lead
records the milestone and local tag. A miss after the permitted retry means release with documented limits,
not a pass, a changed threshold or removed votes ([ADR-0015], Arithmetic and decision).

## Capacity and boundary

**Cap:** two weeks. Before the first gate, the lead books exclusive card windows and build/review capacity for
qualification, the initial gate, possible sampling extension and one repair/requalification cycle.
The primary block is 612 launches (17 x 3 x 6 pairs x 2 executables); extension makes 1,224. A complete repair retry
needs its own block and possible extension. Use S11/S12 measured durations for hours; these counts exclude
correctness, profiles, batches and optional panels. Protect primary/repair windows before optional panels.
If capacity cannot cover the plan, surface the shortfall to the owner before running; never silently reduce samples.
**Out of scope (M5):** new optimization themes, new PGO/AutoFDO infrastructure, autotune, intrinsics, llama.cpp, WRF
and corpus widening. End with a decision, not an open-ended pursuit of 1.25x.

[first review]: ../reviews/2026-11-12-s11-s13-scope-review.md
[ADR-0015]: ../adr/0015-m4-scoring-and-measurement.md
[ADR-0006]: ../adr/0006-portable-shared-i386.md
