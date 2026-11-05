# ADR-0009: Tune the whole optimizer around the KNC core, with `-march=knc` defaults that follow KNC best practice

**Status:** Accepted 2026-11-05 at the owner's direction: "our whole optimization approach needs
to tune around it so software and hardware are executed in pure harmony. We need to make sure
our gcc-knc flag is the best practice follower for knc besides ICC."
**Decider:** the owner (direction); Claude (lead) for the engineering below.

**Sources:**
- M. Klemm, *The Intel Xeon Phi Coprocessor*, Intel, 2014-12-11 (LMU seminar). The owner calls
  it the reference for KNC short of hardware design detail.
- Intel 330991-001 (x100 registers) and 327364-001 (ISA).
- The facts and slide numbers are collected in `docs/research/knc-microarch.md`.

## Context

So far the project has made KNC code *correct*: M1, then Sprints 4-5. Sprint 6 (Milestone M2)
makes it *fast*. A generic x86 cost model and scheduler would treat KNC as a narrow out-of-order
core, and it is not. Throughput on KNC is decided by a few hard rules, all stated in Klemm's
slides:
- a core issues from a thread at most every other cycle, so at least 2 threads are needed;
- most vector operations have 4-cycle latency and 1-cycle throughput, matching 4-thread round
  robin;
- only the U-pipe takes vector and x87 instructions, while scalar instructions pair on V;
- there is a 3-cycle address-generation interlock;
- L1 is 32 KB, 8-way, 64-byte lines, and has no hardware prefetcher;
- L2 is 512 KB, 8-way, with a streaming hardware prefetcher, and there is no L3;
- memory is reached across a ring with distributed tag directories, at about 275 ns;
- streaming (no-read) stores add more than 30% of bandwidth.

## Decision

1. **The KNC machine model is a first-class input to every optimization decision.** In Sprint 6 and
   after, the cost model, scheduler, unroller, prefetcher and vectorizer heuristics are designed
   from these rules and measured against them, not ported from an x86 tuning. Each optimization
   ticket states which rule it serves and how the card measurement shows the effect.
2. **Thread density is a parameter, not an afterthought.** Code is tuned for 2-4 threads per core,
   4 by default, as in production HPC use. Kernels are measured at 1, 2, 3 and 4 threads per core
   (E5-01). Where the best code depends on density, the default favours 4 threads per core, and a
   documented option targets fewer.
3. **Latency hiding:** recurrences and reductions get as many independent accumulators as the
   thread density leaves exposed. That is 4 / (threads per core) chains of 4-cycle latency, so one
   at 4 threads and up to four at one thread.
4. **Pipe and interlock awareness in the scheduler (E5-05):**
   - pair a scalar instruction (address, counter, branch) with each vector instruction;
   - keep x87 out of vector loop bodies;
   - separate a pointer update from its use as an address by at least 3 cycles.
5. **Memory hierarchy (E5-07, E7-06, and a new streaming-store item):**
   - software prefetch at two distances: `vprefetch0` for L1 and `vprefetch1` for L2, with
     `vprefetche*` ahead of stores;
   - no-read streaming stores for write-only output that covers whole lines;
   - 64-byte alignment of vector data the compiler controls (stack slots, statics, `malloc`
     guidance in the docs);
   - versioning a loop for alignment where the cost model shows a gain.
6. **`-march=knc` (with `-mtune=knc`) carries the best-practice defaults.** Like ICC's `-mmic`,
   it should give good KNC code without users knowing these rules. The defaults set:
   - a KNC `processor_costs` table;
   - the cache parameters (L1 32 KB/8-way/64 B, L2 512 KB/8-way);
   - the prefetch parameters;
   - the vector cost model;
   - unrolling;
   - code and loop alignment.

   Each default is chosen by card measurement in exclusive windows, with ICC-built references as
   the bar where available (the M2 kernels compare against hand-written IMCI and x87).
7. **Floating-point semantics stay as ADR-0003 defines them; this is the one place we deliberately
   differ from ICC.** ICC defaults to `-fp-model fast=1`. That reassociates and contracts, and
   approximates some operations.
   - GCC-KNC keeps IEEE semantics by default, as GCC does everywhere.
   - It documents the option set that matches ICC's fast default: `-ffast-math`, or a narrower
     set the M2 report names, together with the approximate division and square root of
     ADR-0003 point 5 once built.
   - The owner may overrule this point.
8. **Published guidance:** a short "GCC-KNC flags" page lists, with measured evidence:
   - the recommended flags;
   - what `-march=knc` already implies;
   - the ICC `-mmic` equivalents.

## Consequences

- E5-01 to E5-07 are written against points 1-6. The M2 review judges the kernels against this
  model and the M2 criterion.
- A new backlog item covers streaming stores (E5-08), and another covers the `-mtune=knc` cost and
  parameter tables (E5-09). Both measure on the card.
- Measurements need exclusive card windows, which the owner arranges with the WRF work.
- Correctness tickets in Sprint 5 are unaffected. Their output is the input to this tuning.
