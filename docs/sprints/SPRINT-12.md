# Sprint 12: remove measured whole-program costs (Milestone M4, part 2)

**Status:** planned 2026-11-12, revised from the senior scope review (S11-13). Tickets are written from Sprint 11's
baseline and profile (S11-15); the profiles choose the themes, not this list.

**Goal:** the development corpus runs measurably faster under GCC-KNC than GCC 5.1.1 at strict `-O2`, from at most
three implementation themes chosen by removable wall time and coverage, each proven by a shape test and a paired
whole-program A/B on the 7120 and under the 3100 and 5100 profiles (a gain must hold on all three), with no development program more than 5% slower without a known cause.

Order:
1. **Complete E7-03:** profiles of every development program, the removable-time ranking, and the three themes.
2. **Up to three themes**, each split into bounded stories with their own proof. Likely candidates, in the review's
   provisional order (replace with the measured ranking):
   - scalar addressing, alignment, branches, calls and code size (E7-13, focused E7-04);
   - loop locality and scalar replacement (legal interchange, blocking, invariant hoisting, predictive commoning)
     where existing GCC passes suffice;
   - scheduling with register pressure (E7-15 split: x87 reservation/stack pressure; vector scheduling at 1-2
     threads per core), and density-aware unroll (E7-12) after it;
   - class-specific prefetch (E7-06), causally confirmed first: a matched baseline, density and page-mode controls,
     a compiler-generated corpus loop, and no-regression cache-resident cases. NGO store choice and eviction are
     separate changes; no blanket eviction or automatic thread downsizing;
   - scalar FP in zmm (diagnosis/prototype only), sparse prefetch (E7-09), alignment for long loops (E7-10), short
     tails (E7-19) only if the profiles show them.
3. **PGO on development programs (E7-08 reuse):** qualify the existing atomic-profile train/use workflow on complete
   programs with separate training and evaluation inputs; a donor PGO build if PGO competitiveness is claimed; never
   train on held-out programs. Reported as its own track.
4. **`-mphinix` screen (E7-14):** a bounded development-only `-O2`/`-O3`/current `-mphinix` screen early, contents
   frozen at the end of the sprint; strict and `errno`-relaxed results kept apart.
5. **OpenMP runtime (E6-09)** only for proven runtime loss, after separating barrier cost from late arrival, imbalance
   and fork/join.
6. Batch check: development-corpus regression scan at the integrated head; x86 and portability for every shared change.

**Out of scope:** software pipelining, Graphite, LTO, intrinsics (E6-05), autotune (E7-18), new library or loop-pass
projects without a measured blocker. **Cap:** two weeks from the first implementation ticket.
