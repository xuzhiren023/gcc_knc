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

