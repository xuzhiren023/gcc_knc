# Sprint 11: measure (Milestone M4, part 1)

**Status:** started 2026-11-12; adjusted by S11-19. Scope: [M4 definition](../M4-DEFINITION.md).
**Goal:** a valid experiment and an honest baseline/profile of all 14 development programs, sufficient to select
at most three S12 themes. The three held-out programs expose only readiness/pass-fail until choices freeze.
**Why now:** kernel wins and the compile survey do not establish whole-program donor gains. Measure first so S12
removes demonstrated costs ([first review], Evidence boundary and findings 1-3, 8).

**Binding decisions:** [ADR-0015] fixes 17 serial votes, strict `-O2` versus `-O2` with the SQLite donor assembly
exception disclosed in every headline, and the identical one-line HPCG fix. Every benchmark/A-B covers full 7120
and `card_run --profile 3100` / `--profile 5100`; gains must hold on all three. Profiles model cores/memory,
not clock or per-core bandwidth; they are not native 3120/5110 measurements. GCC-KNC-only OpenMP, PGO,
`-O3` and `-mphinix` are labelled panels, never replacements for primary votes.

## Theme A - make both sides trustworthy

**Achieve / why now:** finish S11-11's harness with S11-14's contract and S11-18's integration before collecting
evidence used to choose optimizations. Staged binaries and host tests are not native readiness.

- Freeze sources, equal work/inputs sized for the smallest profile, checks, SQLite level and the HPCG fix.
- Verify each compiler's installed/linked C/C++/Fortran/math runtimes and loader environment on card; never mix
  incompatible objects/runtimes. The donor's absent OpenMP runtime remains a labelled panel limitation.
- Lead verifies access controls before any held-out build/check/run; diagnostics and full-corpus scores stay sealed.
- Exercise independent correctness checks and corrupted-result controls; retain failed/blocked rows.

**Exit:** all 17 programs have native readiness status for both compilers and all settings, with equal valid work
and passing checks before timings are usable. A primary blocker blocks this exit; recording it is not completion
([ADR-0015], Frozen comparison, Timed boundaries, Correctness, Held-out access).

## Theme B - explain the baseline and choose affordable work

**Achieve / why now:** S11-15 delivers pilot-quality donor comparisons and hot-cost profiles for all 14 development
programs, using A's verified runner and C's relevant hazard results. First pilot existing cycle/timer IP sampling
on one development program, checking symbol attribution and overhead; if unavailable, use bounded compiler
instrumentation in diagnostic builds without corpus source edits. Record uncertainty; diagnostic times never replace primary
latency. No AutoFDO recorder project: [S9-19] section 2 leaves sampling availability unproven. An inadequate method
is a profiling blocker, not permission to infer time shares from assembly. Rank removable serial time from hot
functions/loops, vectorization, x87/vector transfers, spills, code size and setup/runtime costs. OpenMP wait stays
in its separate panel.
**Exit:** `docs/research/m4-baseline.md` has 14 development rows across all settings, uncertainty/causes, the profiler
decision and at most three general mechanisms with expected benefit, cost and controls. No held-out timings or
17-vote aggregate appears there ([S11-15], Scope; [first review], findings 3, 5, 8).

## Theme C - close hazards before trusting results

**Achieve / why now:** run S11-16's bounded long-double libm probe alongside A; a fault can invalidate the baseline
or its oracle. Guard/fix reproduced hazards before affected measurements; record untested coverage. S11-08's
completed `cbrtl` repair belongs here. S11-12 qualifies the final integrated head after repairs.
**Exit:** no known relevant fault remains unguarded; native ABI/runtime/prefix checks, lead-run x86 identity and
the sprint-end forward-port drill have recorded results. Failures remain blockers, not "green"
([first review], findings 7, 9; [ADR-0006], Decision 5-7).

## Side track - bounded feasibility and owner priorities

**Achieve / why now:** S11-17 checks the existing PGO train/use path on one complete development program with separate
training/evaluation inputs so S12 can decide whether to reuse it. Success or a documented blocker is its exit;
it does not delay the serial baseline. S11-13 and this review supply planning evidence, not extra experiments.
S11-02 qualifies DMA integration and SSH fallback; S11-05/-06/-09 finish bandwidth/GEMV analyses for later work.
Their exits are their own correctness/results reports, not an M4 bandwidth target. Staging may use the working
fallback; research enters S12 only through M4's admission rule ([first review], findings 3, 6).

## Capacity and handoff

**Cap:** two weeks from 2026-11-12. The lead owns builds/card jobs and records pilot-derived hours and exclusive
windows for A/C readiness, B profiling, final batch, optional PGO and research before booking. S11-18's staged
468-launch estimate is 4-7 hours, not a validated baseline duration ([S11-18], 17:12 note). Protect primary
readiness/baseline and final batch; run the hazard probe before affected measurements. The owner still needs to
allocate corpus versus side-work hours; defer side work rather than borrow protected windows. At the cap, report
unmet exits and a smaller justified S12 scope; never infer missing evidence or promise a pass.
**Out of scope:** performance implementations (S12), new profiling infrastructure, hardware/MPSS changes, intrinsics, autotune.

[ADR-0015]: ../adr/0015-m4-scoring-and-measurement.md
[ADR-0006]: ../adr/0006-portable-shared-i386.md
[first review]: ../reviews/2026-11-12-s11-s13-scope-review.md
[S9-19]: ../research/s9-19-auto.md
[S11-15]: ../../work/tickets/S11-15.md
[S11-18]: ../../work/tickets/S11-18.md
