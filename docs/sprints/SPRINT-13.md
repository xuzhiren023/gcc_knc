# Sprint 13: qualification and the M4 decision (Milestone M4, part 3)

**In plain words:** We will finish with a clear result: the compiler meets the agreed milestone or falls short.
We test now because the improvements are finished and the reserved programs can provide an independent check.
Completion requires all agreed measurements and correctness checks, an explanation of failures, and the
owner's decision. If a repair is needed, we allow one retry and report that the reserved programs are now known.

**Status:** planned; adjusted by S11-19, 2026-11-12. Scope: [M4 definition](../M4-DEFINITION.md).
**Goal:** a defensible M4 pass or documented miss on the frozen experiment, followed by the owner's decision.
**Why now:** S12 supplies a measured, integrated candidate and frozen optional modes. Test whether those choices
transfer to all 17 programs; new optimization projects would consume the independent check
([first review], findings 8-9 and Proposed revised sprint outline).

## Theme A - freeze and qualify the actual candidate

**What and why this sprint:** close previously identified correctness repairs before freeze; record compiler,
libraries, installed and linked runtimes, flags, runner and scorer, inputs, checks and schedule. Preserve S11's frozen work
and scoring policy. Book and complete the final batch before optional panels or gate interpretation.
**Exit:** native ABI and runtime checks and x86 identity at the final candidate head; a forward-port drill on refreshed
upstream master and release refs; trunk with the port built and passing T1 and T2. Record portability findings. A textual
merge or older head's pass is insufficient; unresolved qualification failures block readiness
([ADR-0006], Decision 5-7; [first review], finding 9).

## Theme B - run the complete frozen gate

**What and why this sprint:** E7-05 measures all 17 votes, including adi, durbin and bzip2 after choices freeze.
Use strict serial `-O2` GCC-KNC versus the donor, **disclosing SQLite's frozen donor assembly-level exception**.
The identical one-line HPCG fix is the only corpus source change. No successful-row-only score is permitted.

- Apply [ADR-0015]'s six balanced independent launch pairs per program and setting, card-side launch-to-exit timing,
  independent correctness and retained raw attempts and validity reasons. Pilot times never enter the gate.
- Score full 7120, `--profile 3100` and `--profile 5100` separately: each 17-vote median needs a one-sided 95%
  lower bound of at least 1.25x. Every program passes correctness and regression review; confirmed slowdowns above 5%
  need a lead-reviewed diagnostic cause. Missing or invalid data or unresolved regression evidence cannot pass.
- Use the predeclared six-pair extension across every program and setting only when ADR-0015's interval rule triggers
  it; retain all twelve pairs. This sampling extension is distinct from the one compiler-repair retry.

**Exit:** complete results, per-program and family diagnostics, uncertainty, every failure and regression and its cause;
labelled `-O3`, `-mphinix`, PGO and GCC-KNC-only OpenMP results or explicit unavailable-panel status.
Profiles model cores and memory, not clock or per-core bandwidth: no native 3120 or 5110 speed claim follows
([ADR-0015], Launch schedule, Arithmetic, Held-out access; [first review], findings 1-2, 8).

## Theme C - one bounded repair opportunity, then an honest decision

**What and why this sprint:** diagnose an actual gate failure and, if needed, use the owner's one bounded repair
retry on the same corpus and protocol. A repair invalidates the old candidate: freeze the new head, refresh affected
qualification including final-head x86 evidence, and rerun the complete gate. A held-out-triggered repair is
a check on programs already seen, not an independent test on reserved programs. Infrastructure recovery follows ADR-0015's recorded
lead decision and complete replacement-block rule; preserve aborted results, never relabel correctness failures.
**Exit:** the lead presents evidence and a recommendation; the owner records proceed, adjust or stop. On a pass, the lead
records the milestone and local tag. A miss after the permitted retry means release with documented limits,
not a pass, a changed threshold or removed votes ([ADR-0015], Arithmetic and decision).

## Capacity and boundary

**Cap:** two weeks. Before the first gate, the lead books exclusive card windows and build and review capacity for
qualification, the initial gate, possible sampling extension and one repair and requalification cycle.
The primary block is 612 launches (17 x 3 x 6 pairs x 2 executables); extension makes 1,224. A complete repair retry
needs its own block and possible extension. Use S11 and S12 measured durations for hours; these counts exclude
correctness, profiles, batches and optional panels. Protect primary and repair windows before optional panels.
If capacity cannot cover the plan, surface the shortfall to the owner before running; never silently reduce samples.
**Out of scope (M5):** new optimization themes, new PGO or AutoFDO infrastructure, autotune, intrinsics, llama.cpp, WRF
and corpus widening. End with a decision, not an open-ended pursuit of 1.25x.

[first review]: ../reviews/2026-11-12-s11-s13-scope-review.md
[ADR-0015]: ../adr/0015-m4-scoring-and-measurement.md
[ADR-0006]: ../adr/0006-portable-shared-i386.md
