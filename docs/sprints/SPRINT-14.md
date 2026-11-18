# Sprint 14: correct and measurable (Milestone M5, part 1)

**In plain words:** before we make GCC-KNC faster on more kinds of code, we make it correct and set up what M5 is
measured on. A known crash or wrong-code bug fails M5 however fast the compiler is, and every new program needs a
frozen input and a correctness check before anyone tunes against it.

**Status:** in progress; replanned 2026-11-17 after the owner's refocus on general-purpose work (tickets that only
served other projects were closed or deferred). Scope: [ADR-0016](../adr/0016-m5-definition.md).
**Goal:** zero known ICEs and wrong code at -O2/-O3, the widened corpus staged with checks, the measurement method
written, a fresh Linux build, and bzip2 no longer slower than GCC 5.1.1.

| Theme | Tickets | Exit |
|---|---|---|
| A. Correctness | S12-34, S12-38 (known ICEs), S14-58 (full -O3 torture and vect sweep, triage every failure) | no known ICE or wrong code; new failures ticketed and fixed or scheduled |
| B. Never slower than GCC 5.1.1 | S14-16 (bzip2: mask-register costs), S14-17 if S14-16 leaves a gap | bzip2 at or above 1.00x with its noise bound |
| C. Measurable M5 | S14-56 (new corpus units with frozen inputs and checks), S14-04 (measurement method) | every unit builds with both compilers and its checker rejects a corrupted output |
| D. Reproducible | S13-04 (fresh-clone Linux build and card tools) | a clean clone builds on a Linux host by docs/BUILDING.md |
| E. Bound the next speed work | S14-44 (scalar double: best x87 flag set, then lane-0 go/no-go), S14-50 (machine-data reconcile) | a go/no-go with numbers, judged on corpus programs |
| F. Tools | S14-22 (card turn rows), S14-24 (dispatch preflight) | no card window lost to the turn-row bug; no engineer session wasted on an unwritable worktree |

**Order:** correctness first (A), then B and C in parallel, D, E and F as lanes allow.

# Sprint 15: faster on more kinds of code (Milestone M5, part 2)

**Status:** started 2026-11-17 on the Z840 workstation (owner: run many more Codex engineers there), alongside Sprint
14's last tickets. S15-01 adds GCC slots 3-4 so more GCC tickets run at once.

Every item is modelled first (model-first, knc-twin for one-core loops) and built only if its bound clears 5%
whole-program on at least two corpus programs. Then the M5 measurement on the widened corpus.

| Item | Ticket |
|---|---|
| Loop unswitching on loop-invariant tests does not fire | S14-52 |
| Loops shorter than one vector: masked loads/stores instead of gather/scatter, full masking when short (issue #32) | S14-54 |
| 16/32-byte generic vectors in zmm low lanes (needed for FFTW) | S14-01 |
| Per-region thread density in libgomp | S13-02 |
| Scheduler model completeness | S14-03 |
| Branch cost and if-conversion thresholds | S14-06 |
| Sparse indexed reductions (NPB-CG, HPCG) | S12-30 |
| Remaining bzip2 gap, if any | S14-17 |
| Scalar double in zmm lane 0, only if S14-44 says go | S14-44 phase 2 |
| M5 measurement on the widened corpus | new, at the end |

**Deferred to M6 (sprint s16):** S12-03, S12-05, S12-20, S14-05, S14-07, S14-08, S14-09, S14-28, S14-46, S14-48.
