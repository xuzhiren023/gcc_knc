# GCC-KNC project plan

**Status:** Kickoff, 2026-11-01. **Current position:** see [CURRENT_STATE.md](../CURRENT_STATE.md).

## 1. Mission

Build a reproducible cross-toolchain, based on a modern GCC, that compiles ordinary
C, C++ and Fortran into native, correct and profitable Knights Corner programs,
replacing x87-first builds and assembly translation.

### How success is measured

Three outcomes are reported separately, because none of them substitutes for another.

| Outcome | Measure | First target |
|---|---|---|
| **Coverage:** does it compile and run correctly? | Pass rate of GCC's `gcc.c-torture/execute`, `gcc.dg/vect` and `gfortran.dg` subsets, native on the card, with zero ISA lint violations | Agreed at Milestone M2 from the first full baseline |
| **Kernel efficiency:** is the generated code good? | Auto-vectorized kernels against x87 and against existing hand-written IMCI, across lengths and thread densities | See Milestone M2 |
| **Programs:** does it reach real software? | A public corpus of unmodified C, C++ and Fortran programs: how many build and run correctly, and whole-program speed against GCC 5.1.1 | See Milestones M3 and M4 |

This is a general-purpose compiler project, independent of any one application. Work is
prioritized by benefit across the corpus and never tuned to a single program. That
includes integer and branch-heavy code, not only floating-point loops.

## 2. Scope

**In scope:** a KNC subtarget of GCC's i386 backend, scalar and IMCI code generation, auto-vectorization, a measured cost model and scheduler, matching C, Fortran, OpenMP and C++ runtimes, a small vector math library, optimization reports and packaging.

**Out of scope for now:**

- Modern x86 intrinsics or AVX code working unchanged
- Offload to the card
- A new parser, vectorizer or driver
- A general assembly translator
- Replacing libc, or sanitizers
- LTO (blocked by the assembler)
- Implicit precision changes
- Application-specific tuning or source changes

## 3. Roles

| Role | Who | Responsible for | Does not do |
|---|---|---|---|
| Product owner | You | Priorities, milestone decisions, card time, pushes, outward actions | Writing code or tests |
| Implementer | GPT (Codex) | Code, story tests, tools, build scripts, measurements and ticket notes | Editing `tests/acceptance/` or ADRs; merging; changing milestone exit criteria |
| Tech lead and reviewer | Claude | Backlog, tickets, acceptance fixtures, ADRs, reviews, consulting and merging to local `main` | Routine implementation |
| Research | Astra | Further research on request, feeding specs | Implementation |

Claude's budget is the scarce one, so it goes where a mistake is expensive. See
[review depth](DEVELOPMENT_CYCLE.md#7-review-protocol). The agents work without anyone relaying
context between them; see [COLLABORATION.md](COLLABORATION.md) and [HARNESS.md](HARNESS.md).

## 4. Decisions already made

- [ADR-0001](adr/0001-base-repo-and-toolchain.md): GCC 16 branch, permanent private fork, separate source repository, existing binutils, card-derived sysroot
- [ADR-0002](adr/0002-imci-separate-isa.md): IMCI has its own ISA flag and `imci.md`; KNC never sets AVX-512 or SSE flags
- [ADR-0003](adr/0003-fp-defaults-and-division.md): x87 scalar through M3, no implicit fast-math, correctly rounded vector division or none

These rest on the [research review](reviews/2026-11-01-research-review.md), which also
lists where this plan departs from the research report.

## 5. Roadmap

Sprints are goal-based and capped at two weeks. A sprint closes as soon as its goal is
met, with no waiting for a calendar. Later sprints are deliberately coarse and are
refined when they come near.

| Phase | Sprint | Goal: what is demonstrably true at the end | Milestone review |
|---|---|---|---|
| **M0** Foundation | **S0** | The test loop works end to end against the donor, the fixture is red for the right reason, and donor inventory and value estimate exist | |
| | **S1** | GCC 16.2 is configured for `k1om-mpss-linux`, and `cc1` emits lint-clean assembly for integer C | **M0** |
| **M1** Mixed native code | **S2** | Native scalar C runs on the card: x87 FP, `zmm`-lane ABI, varargs, libgcc, interop with GCC 5 objects | |
| | **S3** | Ordinary loops auto-vectorize on `zmm`; `m1_affine` passes at all lengths, offsets and at guard pages | **M1** |
| **M2** Useful vector target | **S4** | Masks, compares, if-conversion and cheap masked tails | |
| | **S5** | Conversions, gather/scatter, permutes, reductions, and correct division and square root | |
| | **S6** | Machine characterization, cost model v1, scheduler v0, per-loop reports, first GCC vect testsuite baseline | **M2** |
| **M3** Runtimes | **S7** | Shared libgcc and a libgfortran slice | |
| | **S8** | Tuning block: the M2 weak spots (short lengths, prefetch, mat8/mat16, code-shape wins) | |
| | **S9** | libgomp and libstdc++ on the card (exceptions, RTTI, threads, atomics) | **M3** (accepted 2026-11-11) |
| | **S10** | 512-bit vector ABI, libknc_vmath v0/v1a/v1b and loops calling it, correctly rounded V8DF div/sqrt, card-only vmath fixes, safe `cbrtl` | |
| **M4** Broad optimization | **S11–13** | Host-card transfer best practice; optimization ranked by corpus-wide profiles, scalar and vector (scheduling, prefetch, alignment, PGO, `-mphinix`), compared with GCC 5.1.1 | **M4** |
| **M5** Program corpus | **S14–15** | The full corpus built and run, with matched benchmarks, and the corpus widened (llama.cpp, WRF) | |
| **M6** Release | **S16** | Packaging, documentation, known-limits list and update procedure | |

Updated 2026-11-12 to match `work/milestones.json`: Sprint 8 became a tuning block, the runtimes ran through Sprint 10, and later sprints moved by one.

M2 to M4 can overlap where dependencies allow. Runtime investigation, for example, can
start before S6 ends.

## 6. Milestones and exit criteria

Each milestone ends with a short review and a decision, by the owner on Claude's recommendation. It records the
evidence and one of **go**, **adjust** or **stop**. The thresholds below are my starting
judgment. They are not derived from data, and each milestone can reset the next one's numbers.

| Milestone | Question | Go if | Otherwise |
|---|---|---|---|
| **M0** | Can GCC 16 be our base, on this host? | `cc1` builds for `k1om`; emits assembly accepted by the 2.22 assembler; incremental rebuild plus T1 takes ≤ 5 min | Record the blocker. Bridge to 14.4 only if it is specific to 16. If only the loop is slow, ask for WSL2 |
| **M1** | Is the i386 subtarget still cheaper than a separate backend? | `m1_affine` fully green, ABI cross-check included; ≤ 300 changed lines in shared i386 files outside the KNC hooks, with no SSE-assumption ICE class still open | Compare costs of a separate backend, using the real inventory, before S4 |
| **M2** | Does generated code justify continuing? | At L2 working sets and production thread density: FP32 affine kernel ≥ 50% of the gain of a hand-written IMCI reference kernel, and never more than 5% worse than x87 at any tested length | Fix the top cost-model finding, one retry; then revisit scope with the owner |
| **M3** | Can runtimes coexist on the card's old system? | Fortran, OpenMP and C++ integration tests pass natively, and required symbols and syscalls are all accounted for | Adapt or formally exclude the feature |
| **M4** | Do gains reach whole programs? | Across the corpus, median whole-program speedup over GCC 5.1.1 is ≥ 1.25×, and no program is more than 5% slower without a known cause | Fix the top corpus-wide cause, one retry; then release with documented limits rather than chase M5 |

## 7. Forecast

**Low confidence, and reset at Milestone M1.** Nothing has been built, and the estimate
depends on GPT throughput, card availability and how deeply i386 assumes SSE.

| Through | Cumulative range |
|---|---|
| Milestone M0 | 2–4 weeks |
| Milestone M1 | 6–10 weeks |
| Milestone M2 | 3–5 months |
| Milestone M3 | 5–8 months |
| Milestone M4 | 7–11 months |

M2 and the runtime stages carry most of the uncertainty. These are planning ranges and
do not impose waits.

## 8. Tracking

`CURRENT_STATE.md` carries these, updated at each sprint close:

| Metric | Why it matters |
|---|---|
| T1 and T3 test counts and pass rates, and the regression ratchet | Are we moving forward? |
| Incremental rebuild plus T1 time | TDD stops working if this grows |
| Card minutes per sprint | Keeps the shared card usable |
| Changed lines in shared i386 files | Rebase cost, and the Milestone M1 input |
| Review rounds per story and escaped defects | Are specs and tests good enough? |
| Fixture status (`m1_affine`, later kernels) | The plain answer to "does it work?" |

## 9. Top risks

| Risk | Early signal | Response |
|---|---|---|
| i386 backend assumes SSE or AVX more deeply than a subtarget can absorb | Repeating ICEs; shared-file line count rising faster than features | Milestone M1 comparison with a separate backend |
| Typical programs spend too little time in vectorizable loops | S0-07 corpus estimate | Shift effort to scalar code quality, scheduling and inlining; owner decides early |
| Tuning to the benchmarks regresses other programs | Held-out programs slow down | Keep a held-out part of the corpus; narrow rules or use a conservative default |
| No correct and competitive vector division | E4-03 results | Division stays scalar in those loops, or explicit opt-in |
| Scalar and vector transitions eat the gain | Spill and memory-transfer counts in reports | Region-based lowering, cost-model penalties |
| Card contention with other work on this machine | Runner refuses to start | Host-side tiers first; batch native runs |
| Masked forms fault at page boundaries | E3-01 probe | Tail by aligned load or scalar, with cost reflected |
| Old assembler rejects something GCC 16 requires | Milestone M0 build | Configure off or emit an equivalent; forward-port only as a last resort |
| glibc 2.21 or kernel 2.6.38 cannot support a modern runtime feature | Missing symbols or syscalls in T2 | Adapt or exclude explicitly |
| Tests pass without proving anything (implementer writes both) | Weak fixture review; escaped defects | Reviewer-owned acceptance, seeded-bug checks, independent oracles |
| Process grows heavier than the work | Stories wait on reviews or receipts | Retros cut steps; one evidence note per story |

## 10. Owner decisions needed

| Decision | Needed by | My recommendation |
|---|---|---|
| ~~Create a private GCC fork repository~~ **Created 2026-11-01:** `xuzhiren023/gcc_16_knc` | Before S1 | Done |
| ~~Confirm `xuzhiren023/gcc_knc` visibility~~ **Owner says private, 2026-11-01** | First push | Done |
| ~~Grant the runner card access~~ **Approved 2026-11-01:** native jobs run only when the card is idle | S0-04 | Done |
| Approve the benchmark corpus | After S0-07 | Mix of integer, floating-point, C, C++, Fortran and OpenMP |
| Enable WSL2, if Milestone M0 shows Cygwin is too slow | Milestone M0 | Decide only with the measured numbers |
