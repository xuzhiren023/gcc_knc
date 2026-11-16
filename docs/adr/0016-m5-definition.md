# ADR-0016: M5 definition - broad and correct

**Status:** Proposed 2026-11-16 by the lead. Waits for the owner's confirmation of the four open choices at the end.
Frozen before Sprint 15 measures anything; changing a rule after any M5 result is seen needs a new owner decision,
recorded here.
**Plan:** `docs/PLAN-M5-M6.md` (M5, Sprints 14-15). **Carries over:** ADR-0015 (measurement), ADR-0010 (kernels).

## What M5 proves

M4 showed GCC-KNC is fast on regular numerical code (median 2.19x, LB 2.16x over GCC 5.1.1 on 17 programs) and weak
elsewhere (bzip2 0.93x, zlib, SQLite, NPB-EP/IS near 1.0x). M5 asks whether it is a general-purpose compiler: correct
on what users write, faster on code styles M4 did not score, and buildable by anyone from the public repos.

## Pass rule

1. **Correctness.** At the M5 head: zero known ICEs and zero known wrong-code at `-O2` and `-O3 -march=knc` on the
   GCC torture and vect suites and on every corpus program; the execute suite passes on the card. A defect found
   during M5 and not fixed fails M5; no exclusions after results are seen (owner rule of M4).
2. **Breadth.** A corpus of at least 25 program units, one vote each: the 17 M4 units, the S11-20 generality set
   Q1-Q6 promoted to scored programs (Q1/Q2 count once, as in S11-20), WRF (one fixed-step case), FFTW through its
   generic-simd path, and one LLM decode kernel (quantized GEMV, S14-08). Every unit has a frozen input and a
   correctness check before any GCC-KNC tuning uses it.
3. **Speed.** Strict matched `-O2`, serial against serial, as ADR-0015 rules 1 and 5 (the SQLite donor exception
   stays and stays labelled). Median speedup over GCC 5.1.1, one-sided 95% lower bound, at least 1.25x on the 7120
   full profile.
4. **Never slower than GCC 5.1.1** (owner 2026-11-14). Every unit's point estimate is above 1.00x and no unit's
   one-sided 95% upper bound is below 1.00x. A unit at parity is a defect with a ticket, not a pass.
5. **Reproducible.** Both repos public; a fresh clone builds on a Linux x86-64 host by `docs/BUILDING.md` to IMCI
   assembly and, with the MPSS sysroot, to card binaries; `card_run` works from that host.

## Measurement

ADR-0015 applies unchanged except where listed here: same timing protocol, repetitions, retry and donor-failure
rules, 240-thread machine state for OpenMP side tracks, length-only checks on host-card transfers. Side tracks
(`-O3`, `-mphinix`, PGO) are published with labels and never replace a failed primary row. Held-out units are sealed
at the M5 head as in ADR-0015; development units may be tuned on.

## Open choices for the owner

- **A. Threshold.** 1.25x LB on the widened corpus (proposed: the new units are where we are weak, so 2.16x will not
  hold), or another figure.
- **B. Card models.** 7120 full profile decides (as M4 after the owner's cancellation); 3100 and 5100 reported, not
  scored (proposed), or all three scored.
- **C. Held-out share.** Proposed: of the new units, Q3, Q5 and FFTW held out and sealed; the rest development.
- **D. WRF.** Scored as one unit against plain GCC 5.1.1 (proposed); the gap to PhiWeather's hand-tuned build (S14-30)
  is reported separately and does not decide M5.
