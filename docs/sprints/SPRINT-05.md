# Sprint 5: conversions, gather/scatter, permutes, reductions, correct division and square root (Milestone M2, part 2)

**Status:** closed 2026-11-06 at GCC `knc` `ba973dc285b`. Started by the owner on 2026-11-05 ("Start! Your! Engine! For sprint 5"). Runs need no
per-run approval.

**Who implements (owner, 2026-11-05):** Claude Code subagents started by the lead, as in Sprint 4.
GPT runs on paid credit until about 2026-11-12. Deep tickets and research use Opus at high
effort; standard and light tickets use Sonnet. Each subagent works as the engineer under
`AGENTS.md`. The lead reviews and merges as before, and records each subagent's token use on its
ticket.

**Change (owner, 2026-11-05, at 9% of the weekly Claude usage):**
- From S5-07 on, engineers are Codex sessions started through `tools/dispatch.py`, at normal speed
  (no priority tier).
- The model is chosen per ticket depth in `harness/policy.json`:
  - deep: `gpt-6-astra`, high effort;
  - standard: `gpt-6.1-sol`, medium;
  - light: `gpt-6-luna`, low.
  - A ticket's `model:` field overrides this.
- The engineer prompt asks for no narration.
- S5-06 and S5-09 finish as the Claude subagents they started as.

**Card (owner, 2026-11-05):** we coordinate card time with the PhiWeather "WRF 4.8.0 Xeon Phi
performance tuning" Claude session. Rules agreed with that session the same day:
- We never start a job while one of its `"timingValid": true` jobs is open in the shared ledger.
  Those are whole-card timed runs.
- It announces each block of timed runs and its end.
- Any longer job of ours (for example an exhaustive FP32 square-root check) is booked with that
  session first.
- No start row of ours may stay open through a slow upload (S5-04).

**Goal:** the loop shapes that Sprint 4 still leaves scalar vectorize correctly on `zmm`:
- int and FP conversions;
- indexed loads and stores (gather and scatter);
- reversed and interleaved access (permutes);
- sum, min, max and logical reductions under an explicit FP ordering contract;
- byte and word data through IMCI's up/down conversions, as far as the design allows;
- vector division and square root, but only where a correctly rounded sequence is proven
  (ADR-0003 point 4); otherwise they stay x87 and the report says why.

Roadmap row S5 in `docs/PROJECT_PLAN.md`; backlog E4-02, E4-03, E4-05, E4-06 and E4-07.

**Out of scope (Sprint 6, Milestone M2):**
- machine characterization;
- cost model v1, the scheduler, per-loop reports, and the vect testsuite baseline;
- k-register mask logic (`kand`/`kor` in scalar code; deferred in Sprint 4 for the
  scalar-pattern risk);
- reusing one mask across guards (S4-05's finding that each guard re-`kmov`s its mask), which is
  a cost question.

**Cap:** two weeks from start. Unfinished tickets return to the backlog.

**Rules carried from Sprint 4:**
- Shared i386 changes take ADR-0006 forms only. Lines and hunks are reported (no cap).
- x86 assembly stays identical.
- Per-head checks run as batch checks after every 2-3 gcc merges.
- The card is for validating built programs only, on cores 40-59, under the coordination above.
- Each gcc ticket gets its own card check after merge.

## Plan

1. **Research in parallel (tools lane, read only):**
   - S5-01: gather, scatter, permutes, reductions, FP min/max;
   - S5-02: conversions, up/down conversions;
   - S5-03: division and square root.
   The two probes from S5-01 and S5-02 run on the card, by the lead.
2. **ADR-0008** (lead) settles gather/scatter, conversions, permutes and reductions. An ADR-0003
   amendment settles division and square root.
3. **Acceptance fixtures** (lead), written before the gcc tickets start, in `tests/acceptance/s5_*`:
   - exact references across lengths 0-65 and every element offset, inside guard pages;
   - index patterns with duplicates and out-of-order indices;
   - reductions checked against a declared ordering;
   - MPFR or exact references for division and square root.
4. **Gcc tickets one at a time** (the build tree is shared), ordered by ADR-0008. Expected:
   conversions, then permutes and reductions, then gather and scatter, then byte and word data,
   then FP32 division and square root. Batch checks follow after the second and the last.

## Tickets

| Ticket | What it delivers | Depth | Lane | Needs |
|---|---|---|---|---|
| S5-01 | Research: gather/scatter forms, partial completion and fault footprint, GCC 16 indexed-access entry points, permutes, reductions and the FP ordering contract, FP min/max; card probe | deep | research | |
| S5-02 | Research: IMCI int/FP conversions against C semantics, GCC 16 pack/unpack optabs, up/down-converting memory forms, byte and word data design; card probe | deep | research | |
| S5-03 | Research: correctly rounded FP32 and FP64 division and square root from `vrcp23ps`/`vrsqrt23ps` and FMA; proof and test plan with MPFR; card time needed | deep | research | |
| S5-04 | `card_run` shares the card with the PhiWeather tuning session: project tag, own-budget memory count, refusal while a timed job is open, a staging limit, packed S3-10 batch | standard | tools | |

| S5-05 | `knc_lint` accepts the decoded `%ymm` source of `vcvtdq2pd`/`vcvtudq2pd`/`vcvtps2pd` (found by S5-02) | light | tools | |
| S5-06 | KNC `vec_perm_const`: swizzle, `vpermf32x4`, `vpshufd`, `valignd`, blend, one and two `vpermd` | deep | gcc | |
| S5-07 | Reductions: `vpermf32x4` and swizzle trees, no stack accumulator | deep | gcc | S5-06 |
| S5-08 | Same-width int/float conversions; the ADR-0008 named-insn exception | standard | gcc | S5-05 |
| S5-09 | Card probe of `vrcp23ps`/`vrsqrt23ps`/`vgetmant` (S5-03 P1a-e) | light | research | |
| S5-10 | Correctly rounded FP32 vector square root | standard | gcc | S5-08 |
| S5-11 | Correctly rounded FP32 vector division and `cond_div` | deep | gcc | S5-10 |

ADR-0008 was accepted on 2026-11-05 and amended the same day with the card probes. All of its
probe-dependent points resolved the permissive way (`docs/research/card-runs-s5.md`). Still to
write, in order, as the gcc lane frees up:
- float/double-width conversions;
- 16-lane gather/scatter;
- 8-lane gather/scatter;
- FP min/max;
- byte and word data;
- two batch checks.

FP64 division and square root stay scalar this sprint (S5-03).

## Batch check results

- **S5-17 (mid, `9690ac8906a`):** x86 identical (1,962 files at `-O2` and `-O2 -mavx512f`); drill
  conflicts textual; 0 ICE in both sweeps (1,968 pass, 33 compiler errors, 2 user asm); execute
  suite 1,681/1,681; `s4_masks` and `s5_ops` pass.
- **S5-18 (final):** x86 identical at `656cb9ef096` and again at `ba973dc285b` after S5-21; drill:
  upstream master 5 files with 7 textual hunks, `releases/gcc-16` none; 0 ICE in both sweeps;
  shared i386 code 546 lines in 107 hunks, KNC-only `i386-knc.cc` 1,466, `i386-knc.h` 99,
  `imci.md` 1,860, `linux-k1om.h` 72. Card: execute suite 1,680/1,680 (`pr109040` then failed to
  compile, fixed by S5-21), `s4_masks`, `s5_ops` at three levels, S5-16's page-end byte loop,
  S5-21's donor cross-links, and all 14 S3-10 rows at `ba973dc285b`
  (`docs/research/card-runs-s5.md`).

## Sprint exit

- [x] S5-01 to S5-03 accepted; ADR-0008 accepted; ADR-0003 amended for division and square root
- [x] Every gcc ticket merged and proven on the card with its acceptance fixture
- [x] Final batch check: x86 identical, every drill conflict textual, 0 ICE in both sweeps, shared
  lines and hunks reported with the KNC-only files beside them
- [x] Card part at the sprint head: the full execute suite, all `s4_masks` and `s5_*` fixtures, and
  the S3-10 rows (torture row covered by the suite run)
- [x] `CURRENT_STATE.md` updated; retro written

## Retro

Written 2026-11-06 by the lead. **Sprint 5 is closed** at GCC `knc` `ba973dc285b`.
1. Kept: every gcc ticket was proven on the card right after merge, and the hard FP work was
   proven exhaustively or near it: FP32 sqrt over all 2^32 inputs, FP32 division over 1.8 billion
   hard and random cases in all four rounding modes, flags included. Red-first review caught test
   bugs (S5-13's mask regex) as well as code bugs.
2. Design errors were the lead's, and the engineers caught them: ADR-0008 point 7 gave V16HI a
   128-bit home and whole-register spills, and its "reject the new modes" ABI rule broke
   `pr109040`, which had worked. Lesson: when a type gains a mode, check what ABI it had before.
3. Cost: Codex used several million input tokens on standard tickets, and two tickets ran out of
   budget after finishing; the lead submitted them. Sandbox limits cost rounds: it cannot delete
   what it creates in a worktree, so stray files got committed twice (now in `.gitignore`).
4. Process gaps fixed during the sprint: an engineer tried a card job (card is now lead-only, S5-20);
   the dispatcher's headless lead approved S5-18 before the lead's evidence (its prompt now
   escalates); a `timeout` on `pm.py approve` left a stale board lock.
5. Card sharing with the PhiWeather session worked without a clash, through messages and the
   S5-19 ledger rules, across many timed blocks on both sides.
