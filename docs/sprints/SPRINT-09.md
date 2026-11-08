# Sprint 9: runtimes, part 2 - OpenMP and C++ (Milestone M3)

**Status:** prework started by the lead on 2026-11-08 under the owner's overnight blanket
approval. The two research tickets (S9-01, S9-02) are read-only and run now, in parallel with
Sprint 8. Their notes end with implementation plans; the lead writes the implementation tickets
from them, and those join the gcc chain after Sprint 8's gcc tickets (one GCC checkout and build).
Engineers: Claude Code through `tools/dispatch.py`.

**Goal (Milestone M3, part 2):** OpenMP programs built by GCC-KNC run on the card with GCC-KNC's own
`libgomp` (ring-aware barrier, sibling-aware spin, physical-core affinity, padded per-thread data),
and C++ programs with its own `libstdc++` (exceptions, RTTI, threads, atomics), both installed in
the private directory beside `libgcc_s` and `libgfortran`, one OpenMP runtime per process.

Order:
1. Research: libgomp (S9-01), libstdc++ (S9-02).
2. Implementation tickets from their plans: libstdc++ S9-03 to S9-05 (plan landed first), then libgomp from S9-01, all after Sprint 8's gcc chain.
3. Batch check.

**Out of scope:** MPI bindings (E6-04) and the IMCI intrinsics header (E6-05), Sprint 10;
narrow generic vectors by value (E6-07), only on demand.

**Cap:** two weeks from start of the implementation tickets.
