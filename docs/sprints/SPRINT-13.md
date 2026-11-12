# Sprint 13: defaults by measurement, PGO, and the M4 decision (Milestone M4, part 3)

**Status:** planned 2026-11-12.

**Goal (Milestone M4):** answer "do gains reach whole programs?" with the corpus. M4 criterion
(`docs/PROJECT_PLAN.md`): across the corpus, the median whole-program speedup over GCC 5.1.1 is at least 1.25x, and
no program is more than 5% slower without a known cause. Otherwise fix the top corpus-wide cause, one retry, then
release with documented limits.

Order:
1. **`-mphinix` contents by measurement (E7-14):** the flag set with the best corpus median and no program more than
   5% slower than `-O2` without a known cause, valid on 3120, 5110P and 7120 models.
2. **Instrumented PGO on the card (E7-08):** libgcov for k1om, atomic profile updates, `.gcda` under `/tmp`; measured
   on the corpus programs where Sprint 12's profiles show branchy hot code.
3. **`knc-autotune` (E7-18), if time allows:** build one program with candidate settings and keep the fastest.
4. **Remaining MPSS libm hazards (E7-21):** check the other long double entry points for `cbrtl`'s table-offset
   fault and guard any that fail, the way S10-13 guarded `cbrtl`.
5. **M4 corpus comparison (E7-05):** the full corpus including the held-out programs (PolyBench adi and durbin,
   bzip2), both compilers, frozen inputs, paired launches; the lead's recommendation and the owner's go / adjust /
   stop decision; `work/milestones.json` and a local milestone commit and tag on go.

**Out of scope:** the program corpus widening (llama.cpp E8-01, WRF E7-20) belongs to M5.

**Cap:** two weeks.
