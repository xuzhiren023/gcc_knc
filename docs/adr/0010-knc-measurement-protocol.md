# ADR-0010: How GCC-KNC measures performance on the card

**Status:** Accepted 2026-11-06 by the lead, under the owner's delegation for engineering decisions.
**Input:** S6-01, `docs/research/knc-measurement.md`, with six exclusive card windows
(`docs/research/card-runs-s6.md`). ADR-0009 sets the production thread density this protocol uses.

## Context

Milestone M2 is decided by timings, and so is every Sprint 6 tuning ticket (ADR-0009 point 1).
Until S6-01 the project had no measured method. The card shares memory and the ring with the
PhiWeather session, the TSC is not proven invariant, and KNC's four hardware threads per core
share L1 and L2.

## Decision

1. **Clock.** Times are wall makespans from `CLOCK_MONOTONIC_RAW`. Serialized `rdtsc` is kept only
   for same-worker tick counts, never across cores. The TSC runs at about 1232.2 MHz on this card,
   but its invariance is not proven (`constant_tsc` and `nonstop_tsc` are absent), so no result
   depends on it. Every launch records the clocksource and power policy.
2. **Placement.** Production density is **60 cores (0-59), 4 threads per core, 240 workers**
   (ADR-0009 point 2). Worker `c*d+t` is pinned to sibling `t` of core `c`, with each worker
   setting and checking its own single-CPU affinity; the OS core's CPUs are never used. Densities
   1, 2 and 4 are measured. **Density 3 is excluded from comparisons** until its instability is
   explained: S6-01 saw two sustained regimes about 11% apart with fixed placement.
3. **Working sets.** Arrays are page-aligned with a fixed per-sibling stagger (amendment 1).
   Per-worker lengths are chosen from S6-01's per-density table to fit L1, L2 or memory, counting
   every sibling's live arrays.
4. **Repetitions.** Pinned first touch, then a pilot sized to about 100 ms per batch, then five
   groups of three warm-up and 21 timed batches. The figure is the median of the group medians.
   A launch is valid only if its batches are 50-200 ms and `(max - min) / median` of its five group
   medians is under 2%. Results come from five independent launches; their range is reported, and
   decisions use every launch (amendment 1). Every sample is kept.
5. **Isolation.** Every timing run is a lead-run `card_run --benchmark` job: exclusive whole card,
   programs staged before the clock starts, taken in round-robin turns with the PhiWeather
   session's timed jobs (S5-19). Correctness runs never share a window with timing.
6. **M2 arithmetic.** For each kernel, length and working set, with identical inputs, placement,
   work and FP semantics:
   - speedup over x87 = `T_x87 / T_build`;
   - **gain fraction** = `(T_x87/T_gcc - 1) / (T_x87/T_imci - 1)`, where `gcc` is GCC-KNC's
     vectorized build and `imci` the hand-written IMCI reference;
   - M2 passes when, at L2 working sets and production density, the FP32 affine gain fraction is at
     least 0.5 **in every launch**, and `T_gcc <= 1.05 * T_x87` at every tested length **in every
     launch**. The gain fraction is computed within each launch, where all three builds share the
     same buffers.
   Tested lengths, in elements per worker: 15, 16, 17, 255, 256, 257, 1023, 1024, 1025, 4096,
   16384 and 262144, plus the working-set rows, at 1 core and at 60 cores. Build orders alternate
   between launches.

## Consequences

- S6-02 (M2 kernels) and S6-03 (characterization) follow this protocol, and their drivers print
  every sample.
- A tuning ticket's card evidence is a before-and-after pair under this protocol.
- Density 3 needs its own investigation before any result at 3 threads per core is quoted.
- If the TSC is later shown invariant, point 1 may allow cross-core tick counts.

## Amendment 1 (2026-11-06): every launch must pass

**Status:** Accepted by the owner ("Every launch must pass"), on the lead's recommendation.

**Why.** The first full M2 block (`docs/research/card-runs-s6.md`) found two problems. (1) A pilot
batch that stalled sized every batch to 4-9 ms, where the 240-thread barrier dominates; two such
runs still passed the spread check. (2) At the L2 working set, GCC-KNC and IMCI times moved 18-21%
between launches while each launch was steady within 2%. Page-aligned, staggered buffers removed the
variation at length 1024 but not at L2. The card gives user programs no huge pages (THP reports
`always`, yet `AnonHugePages` stays 0; `nr_hugepages` is 0), so each launch gets different physical
4 KiB pages and the physically indexed L2 sees different set conflicts. Real programs see the same.

**Changes.**
1. Batches are re-sized until a check batch is 50-200 ms; a launch whose median batch is outside
   50-200 ms is invalid.
2. Buffers are page-aligned, x and y 512 bytes apart and each sibling thread 1 KiB further on.
3. Five launches instead of three. The 2% rule applies within a launch only. The range across
   launches is reported with every result, never hidden.
4. M2's two conditions must hold in every one of the five launches (point 6).
5. Fixed physical placement (reserved huge pages, which needs root on the card) is the owner's call
   and would allow a cross-launch rule again.

## Amendment 2 (2026-11-06): spread is a flag, decisions use confidence bounds

**Status:** Accepted by the owner ("approved recommendation setting"), on the lead's recommendation
from the gate review (`docs/research/m2-gate-review.md`) and the noise diagnosis
(`docs/research/m2-noise-diagnosis.md`), both by the lead's subagents. Card confirmation of the
mechanism is pending (`claude-s6-m2diag.sh`).

**Why.** The within-launch 2% rule (point 4) fired in 23 of 86 sized launches on 2026-11-06, in 18
cases on the build timed first, on a 10-22% step between two performance states that also
explains the cross-launch range. The discarded launches gave the same M2 verdict as the kept
ones. Discarding and rerunning launches on that criterion is a selection on an outcome, which the benchmarking
literature (Hoefler & Belli 2015 rules 5-7; Kalibera & Jones 2013; Abedi & Brecht 2017) replaces
with full reporting, repetition at the level where variance lives, and confidence intervals around
the decision statistic. See `docs/research/m2-gate-review.md`.

**Changes.**
1. Point 4, validity: a launch is valid when the correctness gate passed before timing, every
   build's median timed batch is 50-200 ms, every worker's pin check passed, density is not 3,
   card_run reports no overlapping job and no foreign workload, and the clock policy records are
   identical at start and end. Nothing else invalidates a launch. Every sample is kept.
2. Point 4, reporting: for each build the five group medians are printed in chronological order
   with their spread; a spread of 2% or more is reported as a **regime step** flag with the build,
   its position in the launch order and the step size. Flags are counted per block and reported
   with the result. A flagged launch counts like any other.
3. Point 6, M2 decision, at the L2 working set and production density over five valid launches:
   (a) the FP32 affine gain fraction is at least 0.5 in every launch; (b) the one-sided 95% lower
   confidence bound of the mean gain fraction, mean - t(0.95, n-1) * sd / sqrt(n), is at least
   0.5; (c) T_gcc <= 1.05 * T_x87 at every tested length in every launch. If (a) or (b) fails
   while the mean is at least 0.5, exactly five more launches are run and the three clauses are
   applied to all ten; otherwise M2 fails. Launches are never repeated or dropped for spread, and
   the number of launches is fixed before the block starts.
4. Point 6, reporting: with each M2 figure, the five (or ten) launch values, their range, the
   minimum, the lower bound in (b), a bootstrap percentile 95% interval of the median gain
   fraction, and the regime-step count.
5. Build order: rotated so that each build is timed first in at least one launch of five (the
   present alternation never times x87 first). If the driver is changed to interleave builds by
   group (one group of each build per round, order drawn per round), the gain fraction is also
   computed per round and the per-round values are reported; this is the design the tuning rule
   in point 7 requires.
6. Amendment 1's items 1, 2 and 5 stand; its items 3 and 4 are replaced by the above.
7. **Point 7, tuning evidence** (new):
   Before and after are two GCC-KNC builds of the same kernel in the
   same process, on the same buffers, timed in interleaved rounds (one group of each per round,
   order drawn per round, five rounds or more), in at least three launches so that at least two
   performance states are seen. The statistic is the per-round ratio T_after / T_before; the
   figure is the median ratio with a bootstrap percentile 95% interval over all rounds of all
   launches (Kalibera & Jones' effect-size interval). A change is accepted when the interval excludes 1 and
   its near end is beyond the ticket's stated minimum effect, at every working set the ticket names.
   A result whose sign differs between launches is reported as placement-dependent, not accepted.
   Per Mytkowicz et al., code layout differs between the two binaries; a claimed effect under 2% is
   additionally checked with the two builds linked in the opposite order.
8. **Correction to amendment 1's reason.** The diagnosis finds that the cross-launch L2 range comes
   from straggler workers in a slow regime early in a launch (worker 0's own time moves about 2%),
   not from physical page placement. The page-aligned placement (amendment 1 item 2) stays: it
   removed real variation at length 1024.

