# Sprint 11: measure (Milestone M4, part 1)

**Status:** started 2026-11-12; rewritten the same day as a roadmap (owner: "we didn't have a clear road map").
What M4 is for: `docs/M4-DEFINITION.md`. Scoring: ADR-0015 (accepted). Engineers: Codex; the lead builds GCC and runs
every card job.

**Sprint goal:** at the end of Sprint 11 we know, honestly and reproducibly, how GCC-KNC compares with GCC 5.1.1 on
every corpus program, and where each program spends the time we could remove. Sprint 12 then picks its work from
that evidence instead of from a list of ideas.

**Why this comes first:** M4 is decided on whole programs. Until now the corpus was only compile-surveyed (Sprint 0),
and our evidence is kernel speedups that cannot be multiplied into a program speedup (S11-13 review). Optimizing
before measuring would mean choosing work by guess.

Owner decisions that bind this sprint (2026-11-12): strict serial `-O2` vs `-O2` decides M4; 17 programs, one vote
each, no exclusions after results; every benchmark on the 7120 and under `card_run --profile 3100` and `--profile
5100`, and a gain counts only if it holds on all three (profiles model cores and memory, not clock or per-core
bandwidth); the six OpenMP programs vote serial vs serial, GCC-KNC's OpenMP a labelled panel; SQLite at the donor's
highest level that assembles; HPCG one documented `default(none)` fix for both; a held-out-triggered retry is an
exposed-set confirmation; a miss after the one retry means release with documented limits.

## Theme A - a valid experiment (M4 critical path)

| Ticket | Delivers | State |
|---|---|---|
| S11-14 | Scoring contract ADR-0015 and scorer: strict serial `-O2`, 17 programs, 3 models, paired launches, 95% bound, 5% rule, sealing | done |
| S11-11 | Corpus harness v1: 17 programs built by both compilers, frozen inputs, staged card runs | done |
| S11-18 | Harness v2: card profiles, runtime-prefix record, held-out sealing, stronger correctness checks, donor-failure rule | doing |

**Exit:** the pilot pass runs every program on the card under both compilers and all three models, with every
correctness check passing or a failure recorded with its cause.

## Theme B - the first baseline and profile (M4 critical path)

| Ticket | Delivers | State |
|---|---|---|
| S11-15 | Pilot timings of both compilers, and a profile of each development program: hot functions and loops, x87/vector bridges, spills, code size, OpenMP wait; a removable-time ranking | after A |
| S11-17 | PGO feasibility on one complete development program (S9-18's path) | after A |

**Exit:** `docs/research/m4-baseline.md` with per-program speedups (pilot quality, not the gate), the removable-time
ranking, and the three Sprint 12 themes it implies.

## Theme C - no hidden correctness hazard in the score

| Ticket | Delivers | State |
|---|---|---|
| S11-16 | Long-double libm audit: does any other MPSS entry point fault like `cbrtl`? | probe staged |
| S11-12 | Batch check at the sprint's final head: native suite, x86 identity, forward-port drill, runtime prefix consistency | last |

**Exit:** no known libm fault unguarded, and the batch green.

## Side track - owner priorities that run beside M4 (not M4 exit criteria)

| Work | Status | Remaining |
|---|---|---|
| Host-card transport (S11-01, -03, -04, -07, -10 done) | DMA at the link limit: 1.67 GB/s card to host, 1.46 GB/s host to card (Gen2 x4) | S11-02: card_run and run_suite use DMA, SSH fallback |
| Memory bandwidth and GEMV for LLM decode (S11-05, -06 done; S11-09) | read 189 GB/s; GEMV fp32 125 GB/s, int8 70 G weights/s | S11-09 analysis; sweep 3 analysis; findings become S12 candidates only through the M4 rule |
| S11-08 (`cbrtl` pragma), S11-13 (scope review) | done | none |

**Card time, in priority order:** Theme A/B pilot and baseline runs, then S11-16's probe, then S11-02, then research
sweeps.

**Out of scope:** any optimization change (Sprint 12), hardware or MPSS configuration changes, intrinsics, autotune.
**Cap:** two weeks from 2026-11-12.
