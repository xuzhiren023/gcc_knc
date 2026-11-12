# Second roadmap review: M4 and Sprints 11-13

2026-11-12 ? S11-19 ? Senior GCC back-end review ? Documents adjusted directly

**Verdict:** measure / improve / decide is coherent once handoffs distinguish native readiness, development tuning
and final qualification. The edits preserve owner scoring decisions; they neither predict a pass nor assert native
results. Only the definition, three sprint pages and this change log were changed.

## Changes and repository evidence

| Edited location | Change and reason | Evidence (file and section) |
|---|---|---|
| M4, question and pass rule | Define breadth as whole-program, mixed-cost, general compiler behavior; remove universal completeness and new-work-in-every-category implications. Bound external claims; disclose SQLite/HPCG and profile limits. | [R], Evidence boundary, findings 5, 7, 8; [A], Frozen comparison, Arithmetic, Held-out access |
| M4, admission rule/table | Separate experiment/qualification, primary improvements and optional modes; infrastructure and correctness need not show speedup. Require general code properties, hot costs, budget and before/after evidence; donor competitiveness does not prove a new change helped. | [R], findings 2-7, Proposed revised sprint outline; [A], Frozen comparison |
| M4, side work | Keep optional modes outside serial credit; retain the theme cap/M5 boundary. Remove transient peak/link-limit numbers that do not define M4 or qualify rollout. Working staging is required; DMA and bandwidth aspirations are not gates. | [R], findings 3-6, Memory bandwidth and LLM decode; [A], Timed boundaries |
| S11, goal/A | Use 14 development profiles and sealed held-out readiness. Require actual donor/runtime linkage, independent checks, equal work and access controls. A recorded primary blocker does not complete readiness. | [A], Frozen comparison, Correctness, Held-out access; [H], items 2-4 and owner 17:00 note; [B], Scope |
| S11, B | Add the profiling-tool decision, attribution/overhead checks and bounded diagnostic-instrumentation fallback; keep diagnostic timing separate, OpenMP wait outside serial ranking, and no AutoFDO project. | [B], Scope; [R], findings 3, 5, 6; [F], section 2 (sampling availability unproven) |
| S11, C/side track | Run libm probes before affected baseline/oracle use; classify cbrtl as correctness. PGO feasibility produces a decision or blocker, not a serial critical-path dependency. Retain independent transport/research exits; replace stale state tables with deliverables. | [R], findings 3, 6, 7, 9; [P], scope; [H], 17:12 note (staged, native pending) |
| All sprint budgets | Require exclusive windows, measured hour estimates and build/review capacity; preserve two-week caps, protect primary/batch/retry time and defer optional work first. Label S11-18's estimate as unvalidated; state the exact final primary launch count. | [R], finding 9, Proposed revised sprint outline; [H], 17:12 note (468 launches, 4-7h estimate); [A], Launch schedule (17 x 3 x 6 x 2 = 612) |
| S12, A | Make the candidate list at most three profile-selected themes, with controls and causal comparisons. Preserve strict semantics, separate prefetch/store causes, allow fewer themes instead of speculative quota filling. | [R], findings 4-5, Proposed revised sprint outline; [A], Frozen comparison |
| S12, B/C | Freeze optional modes before S13; optional OpenMP has no serial credit and stays within the theme/budget cap. Add integrated regressions and a qualified candidate handoff. | [R], findings 6-7, 9; [A], Frozen comparison; [D], Decision 5-7 |
| S13, A-C | Use the accepted six-pair schedule, distinct extension/repair rules, lower bound and resolved regression review. Requalify repaired heads; label exposed-set confirmation and distinguish release with limits from an M4 pass. | [A], Launch schedule, Arithmetic and decision, Held-out access; [D], Decision 5-7; [R], findings 8-9 |

## Decisions still needed, through the lead

1. **Capacity allocation:** the owner must allocate exclusive card hours between corpus/qualification and transport,
   bandwidth/GEMV and optional panels. The lead supplies measured durations, rebuild cost and proposed windows;
   the roadmap protects primary/batch/retry work but does not invent an approved hour budget. If two-week caps
   cannot cover mandatory work, the owner must choose a schedule/scope response before capacity is overcommitted.

No scoring decision is reopened: serial primary, 17 votes, SQLite's assembly exception, HPCG's identical fix, three
resource settings, uncertainty/regression rules, exposed-set retry and release with limits are settled in [A].
Profiler selection and donor-environment verification are readiness work, not new owner policy questions.
Any discovery requiring a scoring change must follow [A]'s explicit amendment rule.

## Follow-through outside this ticket's edit scope

The lead should align S11-15/S11-17 draft dependencies with S11-18 native readiness and relevant S11-16 hazard
results, assign profiling/capacity decisions, and carry these handoffs into S12/S13 tickets.
No ticket, acceptance suite, ADR, scoring code or milestone criteria were edited. No GCC build or card job was run.

[R]: 2026-11-12-s11-s13-scope-review.md
[A]: ../adr/0015-m4-scoring-and-measurement.md
[D]: ../adr/0006-portable-shared-i386.md
[H]: ../../work/tickets/S11-18.md
[B]: ../../work/tickets/S11-15.md
[P]: ../../work/tickets/S11-17.md
[F]: ../research/s9-19-auto.md
