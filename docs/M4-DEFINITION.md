# Milestone M4: what "broad optimization" means for GCC-KNC

**Status:** lead draft 2026-11-12, for the senior review (S11-19) and then the owner. Scoring rules are already
frozen in ADR-0015; this page says what the milestone is for and what work belongs in it.

## The question M4 answers

M0-M3 proved that GCC-KNC is a **correct and complete** toolchain for the card: native scalar code and ABI (M1),
vector code generation whose kernels can beat x87 and approach hand IMCI (M2), and the C, C++, Fortran and OpenMP
runtimes (M3). None of that shows that an ordinary program, compiled unchanged, runs faster than with the compiler
users have today (GCC 5.1.1 from MPSS).

**M4 asks: do our gains reach whole programs, broadly?** "Broad" has three meanings, and all three must hold:
1. **Across programs, not kernels.** The unit of success is a whole, unmodified program from a fixed public corpus
   (17 programs: dense and sparse numeric, stencil, integer, compression, database; C, C++, Fortran), timed launch to
   exit. A faster kernel counts only through the programs it speeds up.
2. **Across kinds of code, not only vector loops.** The corpus is mostly not long vectorizable loops. A broad
   optimizer improves scalar integer and branchy code, address arithmetic, x87 floating point, calls and code
   size, memory traffic, and runtime overhead, as well as vectorization.
3. **Across the KNC family and without regressions.** Gains must hold on the 7120 and under the 3100 and 5100
   profiles, and no program may get more than 5% slower without a known cause. Correctness, IEEE semantics and
   the ABI are never traded for speed (ADR-0003, ADR-0014); no fast-math by default.

**Pass rule (ADR-0015):** the median of the 17 per-program speedups, strict serial `-O2` GCC-KNC over GCC 5.1.1, has
a one-sided 95% lower bound of at least 1.25x on each model, with the regression rule above. `-O3`, `-mphinix`, PGO
and OpenMP are published beside it, labelled.

## What work belongs in M4

The rule for every M4 ticket: **it is chosen because a whole-program profile shows removable time, and it is accepted
because a paired whole-program A/B shows that time removed** (on the affected programs, with two unaffected controls,
on all three models). Work that cannot show that is not M4 work, however interesting.

| Belongs in M4 | Does not belong in M4 (where it goes) |
|---|---|
| Measuring the baseline: the corpus harness, the scoring contract, profiles (S11) | Single-kernel peak tuning without a corpus program behind it (research) |
| Removing profiled costs: scalar code quality, loop locality, scheduling with register pressure, prefetch and store choice, unrolling, alignment, calls and code size (S12) | New large passes (software pipelining, Graphite, LTO) without a measured blocker (later) |
| Choosing defaults by measurement: `-O2` behaviour, `-mphinix` contents, PGO workflow (S12-S13) | Application-specific tuning or source changes (never) |
| Correctness hazards that would invalidate the score: libm faults, runtime-prefix drift (S11) | Intrinsics, autotune, WRF and llama.cpp builds (M5) |
| Qualification: final batch, x86 identity, the decision (S13) | Hardware changes (owner) |

## Work that runs beside M4 (owner priorities, not M4 criteria)

- **Host-card transport at the PCIe link limit** (S11-01 ... S11-10, S11-02): infrastructure for every later project;
  DMA concluded at 1.67 GB/s card to host and 1.46 host to card on this Gen2 x4 link. It does not change the M4
  score (transfers are outside the timed region) and is not on M4's critical path.
- **Memory bandwidth and GEMV for LLM decode** (S11-05, -06, -09): research for the next project. Findings enter M4
  only as S12 tickets that pass the M4 rule above.

## How the sprints map onto it

- **S11 - measure:** make the experiment valid and get the first honest baseline and profile.
- **S12 - improve:** remove the largest profiled costs, at most three themes, plus defaults and PGO.
- **S13 - decide:** freeze, qualify, run the gate, one bounded retry, owner decision.
