# Sprint 13: qualification and the M4 decision (Milestone M4, part 3)

**Status:** planned 2026-11-12, revised from the senior scope review (S11-13).

**Goal (Milestone M4):** answer "do gains reach whole programs?" with the frozen experiment. M4 passes if the median
of the 17 per-program speedups (strict `-O2` GCC-KNC over GCC 5.1.1, measured on the 7120P and under the 3100 and 5100 card_run profiles) is at least 1.25x on each of the three models under
the uncertainty rule frozen in Sprint 11, and no program is more than 5% slower without a known cause.

Order:
1. **Freeze** compiler, libraries, flags and runner; record revisions.
2. **Final batch first, booked before any optional work:** x86 identity on the final head, refreshed upstream refs,
   forward-port drill and trunk checks (ADR-0006), native ABI and runtime qualification.
3. **E7-05 corpus comparison:** all 17 programs including held-out (PolyBench adi and durbin, bzip2), at least 5
   paired launches each, every failure and regression reported; `-O3`, `-mphinix` and PGO published alongside and
   labelled.
4. **One bounded retry** if the gate fails: diagnose the actual cause, fix, rerun; a held-out-triggered retry is
   labelled an exposed-set confirmation. Only E7-21 repairs already identified may still land before the freeze.
5. **Decision:** the lead's recommendation and the owner's go / adjust / stop; on go, `work/milestones.json` and a
   local milestone commit and tag. On a miss after the retry, release with documented limits (PROJECT_PLAN section 6).

**Out of scope (M5):** llama.cpp (E8-01), WRF (E7-20), intrinsics (E6-05), autotune (E7-18), corpus widening.

**Cap:** two weeks.
