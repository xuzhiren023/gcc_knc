# Sprint 11: make the M4 experiment valid; transport at the link limit; bandwidth for LLM decode (Milestone M4, part 1)

**Status:** started 2026-11-12; revised the same day from the senior scope review
(`docs/reviews/2026-11-12-s11-s13-scope-review.md`, S11-13), owner: "Yes, revise it".
Engineers: Codex through `tools/dispatch.py`; the lead builds GCC and runs every card job (owner 2026-11-12).

**Goal (M4 critical path):** a frozen, valid M4 experiment and its first development-corpus baseline.
1. **Scoring contract frozen before any tuning (S11-14).** The owner's decisions of 2026-11-12: strict matched
   `-O2` vs `-O2` (GCC-KNC vs GCC 5.1.1) decides M4, `-O3`, `-mphinix` and PGO published alongside and labelled; 17
   program units, one vote each; all hardware threads of the card or profile primary for OpenMP (240 on the 7120), one and two per core as side panels, one pinned worker for
   serial programs; no exclusions after results; HPCG required unless its unchanged source truly cannot build (then
   the owner decides the fix before tuning); a held-out-triggered retry is labelled an exposed-set confirmation;
   every benchmark and A/B runs on the full 7120 card and under the `card_run --profile 3100` and `--profile 5100` models, and a gain counts only if it holds on all three (owner 2026-11-12: "simulate 3120 and 5110 card hardware spec on 7120 to make sure the gain is universal"; profiles model cores and memory, not clock or per-core bandwidth, stated with every result); a miss after the one retry means release with documented limits. Donor build failures (owner 2026-11-12): the six OpenMP programs vote serial vs serial, GCC-KNC's OpenMP results a separate labelled panel; SQLite uses the donor's highest optimization level that assembles; HPCG gets one documented `default(none)` fix applied to both compilers.
   Plus the protocol: timed boundaries, at least 5 paired AB/BA launches, per-program ratio median, uncertainty
   rule, correctness checks with a corrupted-result control.
2. **The corpus builds, checks and runs (S11-11),** with a runtime-prefix consistency record, HPCG's eligibility
   classified, and held-out access separation (engineers see only readiness and pass/fail for held-out programs).
3. **First baseline and profile of the development corpus (S11-15),** donor and GCC-KNC, top functions and loops,
   x87/vector bridges, spills, runtime wait time; held-out programs excluded.
4. **Early correctness:** bounded long-double libm hazard audit (S11-16, E7-21) before the correctness oracles
   freeze; PGO feasibility on one complete development program (S11-17).
5. **Batch check (S11-12).**

**Owner priorities with their own criteria (not M4 prerequisites):**
- **Transport at the link limit** (owner: "as long as we proven to max out pcie 2.0x4, we are good"): DMA measured
  in both directions at the PCIe Gen2 x4 limit (about 1.6-1.7 GB/s), then S11-02 puts it into `card_run` and
  `run_suite` with SSH fallback. Card to host is at the limit (1.67 GB/s); host to card 1.35 GB/s, link-max run
  in progress.
- **Bandwidth for LLM decode:** finish the bounded S11-09 GEMV study and the S11-06 sweep-3 analysis in separately
  booked card windows; a separate result table per weight format. 264-299 GB/s is a research aspiration, not an exit
  requirement; only generally applicable findings move into Sprint 12, through the corpus gate.

| Ticket | What | State (2026-11-12) |
|---|---|---|
| S11-01, -03, -04, -07, -10 | Transport study and tool fixes | done |
| S11-02 | Transport into card_run/run_suite | waits for link-max numbers; lead writes acceptance |
| S11-05, -06 | Bandwidth research and sweeps 1-2 | done; sweep 3 staged |
| S11-09 | GEMV for LLM decode | sweep staged |
| S11-08, S11-13 | cbrtl pragma; scope review | done |
| S11-11 | Corpus build/check/run harness (re-specified) | doing |
| S11-14 | M4 scoring contract and measurement protocol | new |
| S11-15 | First development-corpus baseline and profile (E7-03 part 1) | new, after S11-11/14 |
| S11-16 | Long-double libm hazard audit (E7-21) | new |
| S11-17 | PGO feasibility on a complete development program | new |
| S11-12 | Batch check | new, last |

**Card windows, in order of protection:** corpus pilot and baseline (S11-11/15), then transport (S11-02), then the
staged GEMV and sweep-3 runs. **Out of scope:** hardware changes (x16 slot), ECC/clock/MPSS changes, intrinsics,
autotune, new loop passes. **Cap:** two weeks from 2026-11-12.
