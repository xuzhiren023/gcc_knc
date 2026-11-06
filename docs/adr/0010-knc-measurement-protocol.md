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
3. **Working sets.** Arrays are 64-byte aligned. Per-worker lengths are chosen from S6-01's
   per-density table to fit L1, L2 or memory, counting every sibling's live arrays.
4. **Repetitions.** Pinned first touch, then a pilot sized to about 100 ms per batch, then five
   groups of three warm-up and 21 timed batches. The figure is the median of the group medians.
   A result is accepted only if `(max - min) / median` is under 2% both across the five group
   medians and across three independent launches. Every sample is kept.
5. **Isolation.** Every timing run is a lead-run `card_run --benchmark` job: exclusive whole card,
   programs staged before the clock starts, taken in round-robin turns with the PhiWeather
   session's timed jobs (S5-19). Correctness runs never share a window with timing.
6. **M2 arithmetic.** For each kernel, length and working set, with identical inputs, placement,
   work and FP semantics:
   - speedup over x87 = `T_x87 / T_build`;
   - **gain fraction** = `(T_x87/T_gcc - 1) / (T_x87/T_imci - 1)`, where `gcc` is GCC-KNC's
     vectorized build and `imci` the hand-written IMCI reference;
   - M2 passes when, at L2 working sets and production density, the FP32 affine gain fraction is at
     least 0.5, and `T_gcc <= 1.05 * T_x87` at every tested length.
   Tested lengths, in elements per worker: 15, 16, 17, 255, 256, 257, 1023, 1024, 1025, 4096,
   16384 and 262144, plus the working-set rows, at 1 core and at 60 cores. Build orders alternate
   between launches.

## Consequences

- S6-02 (M2 kernels) and S6-03 (characterization) follow this protocol, and their drivers print
  every sample.
- A tuning ticket's card evidence is a before-and-after pair under this protocol.
- Density 3 needs its own investigation before any result at 3 threads per core is quoted.
- If the TSC is later shown invariant, point 1 may allow cross-core tick counts.
