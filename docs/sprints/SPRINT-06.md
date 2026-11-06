# Sprint 6: measure, then tune around the KNC core (Milestone M2, part 3)

**Status:** started by the owner on 2026-11-06 ("Can we start sprint 6"). Runs need no per-run
approval, card jobs and timed benchmark windows included ("Yes, same as S5").

**Who implements (owner, 2026-11-06):** Codex sessions through `tools/dispatch.py`, at normal speed,
with the model chosen by ticket depth in `harness/policy.json` (deep `gpt-6-astra` high, standard
`gpt-6.1-sol` medium, light `gpt-6-luna` low), as from S5-07. The owner first chose Claude subagents
and then switched back to Codex, which keeps `.work/_shared/gcc-build` Codex-owned. Gcc tickets run
one at a time. Tickets that wait on the lead's x86 or card runs sit in `lane: lead`, which the
dispatcher does not run.

**Card:** shared with the PhiWeather session under the round-robin protocol (S5-19). Correctness
runs are ordinary jobs. Every timing run is a `--benchmark` job: exclusive, whole card, queued and
taken in turn with that session's timed jobs. Only the lead runs card jobs (`AGENTS.md`, S5-20).

**Goal (Milestone M2):** answer "does generated code justify continuing?" with measurements. The
M2 criterion (`docs/PROJECT_PLAN.md`): at L2 working sets and production thread density, the FP32
affine kernel reaches at least 50% of the gain of a hand-written IMCI reference kernel, and is
never more than 5% worse than x87 at any tested length. Every optimization ticket names the
ADR-0009 rule it serves and shows its effect on the card.

Order: measure first, then tune.
1. A measurement method that gives repeatable numbers on KNC (S6-01).
2. The M2 kernels with IMCI and x87 references, measured at today's head: the baseline (S6-02).
3. The machine characterization tables (S6-03).
4. Tuning from those tables: `-mtune=knc` costs and the vectorizer cost model (S6-05), and the
   scheduler (S6-06).
5. Per-loop reports (S6-04) and the first `gcc.dg/vect` baseline (S6-07), which need no timing.
6. Streaming stores and software prefetch only if time remains (backlog E5-08, E5-07).
7. Batch checks and the M2 evidence note.

**Out of scope:** FP64 vector division and square root (Sprint 5 left them scalar), the
approximate division of ADR-0003 point 5, two-level prefetch (E7-06), runtimes.

**Cap:** two weeks from start. Unfinished tickets return to the backlog.

**Rules carried from Sprint 5:**
- Shared i386 changes take ADR-0006 forms only; lines and hunks are reported.
- x86 assembly stays identical; the lead runs the x86 check (`portability-claude`).
- Batch checks after every 2-3 gcc merges.
- Each gcc ticket gets its own card check after merge.
- Timing figures are recorded only from `--benchmark` windows.

## Tickets

| Ticket | What it delivers | Depth | Lane | Needs |
|---|---|---|---|---|
| S6-01 | Measurement method on KNC: clock, pinning, thread density, working sets, repetitions and noise, with a card probe; ADR-0010 input | deep | research | |
| S6-02 | M2 kernels: FP32/FP64 affine, stencil, short-loop and small-matrix, each as GCC-KNC vector, x87 and hand-written IMCI builds, with a timing driver | deep | bench | S6-01 |
| S6-03 | Machine characterization corpus (E5-01): latency and throughput per instruction class at 1-4 threads per core, cache and memory levels, gather, masked moves, spills | standard | bench | S6-01 |
| S6-04 | Per-loop KNC reports (E5-03): vector factor, peel and tail choice, masks, helper calls, spills and rejection reasons | standard | gcc | |
| S6-05 | `-mtune=knc` costs and vectorizer cost model v1 from S6-03's tables (E5-09, E5-02) | deep | gcc | S6-03 |
| S6-06 | KNC scheduler v0 (E5-05): U/V pipes, 4-cycle vector latency, 3-cycle AGI, measured at 4 threads per core | standard | gcc | S6-03 |
| S6-07 | First `gcc.dg/vect` baseline for KNC: compile scans on the host, execution on the card | standard | tools | |
| S6-08 | Mid batch check | standard | gcc | S6-04, S6-05 |
| S6-09 | ICE fix: `expand_vec_series_expr` (8 vect tests) | standard | gcc | S6-07 |
| S6-10 | ICE fix: `ffsll` conditional move, and constant -1 into a k register (7 vect tests) | standard | gcc | S6-07 |
| S6-11 | ICE fix: FP64 `fmax`/`fmin` loops in `expand_fn_using_insn` (S5-15 follow-up, 2 vect tests) | standard | gcc | S6-07 |

Later in the sprint, if time remains: streaming stores (E5-08), software prefetch (E5-07), the
final batch check and the M2 evidence note.

## Batch check results

(none yet)

## Sprint exit

- [x] ADR-0010 (measurement method) accepted
- [ ] The M2 kernels measured at the sprint head against x87 and IMCI references, at L1, L2 and
  memory working sets and 1-4 threads per core
- [ ] Every gcc ticket merged and proven on the card
- [ ] Final batch check: x86 identical, drill conflicts textual, 0 ICE in both sweeps, the full
  execute suite and all `s*_` fixtures on the card
- [ ] M2 evidence note with the go/no-go recommendation; `CURRENT_STATE.md` updated; retro written
