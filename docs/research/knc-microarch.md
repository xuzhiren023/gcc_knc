# KNC core microarchitecture facts for the cost model, scheduler and prefetch (Sprint 6 input)

Sources:
- the owner's core block diagram (2026-11-05), labelled "x86 specific logic < 2% of core+L2 area";
- Intel, *Xeon Phi Coprocessor x100 Product Family: Registers*, 330991-001, December 2014 (the
  owner's link resolved to this document).

Anything marked *(to measure)* is not stated in either source. E5-01 must measure it on the card,
in an exclusive window.

## Issue and pipes

- **Four hardware threads per core, in order.** The diagram shows the fetch mux taking the T0-T3
  instruction pointers (330991 p.14).
- **At most two instructions per clock, one on the U-pipe (pipe 0) and one on the V-pipe
  (pipe 1).** Simultaneous execution follows pairing rules, and the V-pipe cannot execute every
  instruction type (330991 p.14). Decode is 16 B/cycle (diagram).
- **The diagram shows the VPU register file and the x87 register file fed from pipe 0 only.**
  Pipe 1 feeds only the scalar register file. Taken together, this means vector and x87
  instructions issue only on the U-pipe, and a V-pipe slot can only take a scalar instruction
  (address arithmetic, loop counter, compare-and-branch).
  - For the scheduler (E5-05), interleaving scalar loop overhead with vector instructions fills
    the V-pipe for free.
  - x87 and vector code compete for the same pipe, which matters for mixed loops with an x87
    remainder.
  - *(to measure)* the exact pairing rules: which scalar instructions pair, and whether a vector
    instruction with a memory operand pairs.
- *(to measure, and widely reported, but in neither source)*: one thread cannot issue on two
  consecutive cycles, so a core needs at least two threads to reach its issue rate. That would
  make per-thread throughput depend on thread density, which the M2 criterion already asks for.

## Caches, TLBs and prefetch

- **L1: 32 KB instruction and 32 KB data per core, each 8-way set associative** (330991 p.14).
  Each has its own L1 TLB, plus a shared L2 TLB and a TLB miss handler (diagram).
- **L2: 512 KB per core** (diagram). The MCA address register has a 4-bit L2 way field (330991
  p.16), which suggests up to 16 ways *(to confirm)*.
- **Cache line: 64 bytes.** DMA descriptor rings "align the base to a cacheline" with the low 6
  bits zero (330991 p.53).
- **The hardware prefetcher (HWP) sits at the L2 controller** (diagram), with no L1 hardware
  prefetcher drawn. `TUNE_PREFQ` (MSR 0x337, 330991 pp.17-18) can disable:
  - the HWP as a whole;
  - its prefetches on code reads;
  - its prefetches on non-RFO data reads;
  - its prefetches on RFO (store) reads.

  Its bit 4, `SW_PREF_ENABLE`, lets the HWP start new prefetches from software prefetch requests
  (`vprefetch0`, `vprefetche0`); its default is 0.
  - For E5-07 and E7-06: L1 has only software prefetch, so `vprefetch0` (and `vprefetche0` before
    stores) at an L1 distance is the main lever. L2 streams are covered by the HWP for regular
    access, which leaves `vprefetch1` for irregular or gathered data.
  - Whether `SW_PREF_ENABLE` is set on the card is *(to read)*: MSRs need ring 0 or the msr
    driver.

## Memory

- **8 memory controllers (GBOX), each with 2 channels of 32 bits, GDDR** (330991 p.39).

## Measurement hooks

- Each thread has two 40-bit performance counters (`PERFCNT0/1`, event selectors `EVSEL0/1`,
  330991 pp.35-37), and there is a core time-stamp counter (`TMEL/TMEH`).
- E5-01 can count cycles and events per kernel through these, if the card's MPSS exposes them
  (`/dev/cpu/*/msr` or a perf driver) *(to check)*.

## What this changes in the plan

- **Cost model v1 (E5-02):** price vector and x87 instructions on one issue port (U), and scalar
  overhead as able to pair (V). Count a 64-byte line as one L1 access, and an unaligned
  load/store pair as two.
- **Scheduler v0 (E5-05):** pair a scalar instruction with each vector instruction where the
  dependencies allow, and measure at 1-4 threads per core.
- **Prefetch v1 (E5-07):** start with `vprefetch0` at an L1 distance for streaming loads, and
  `vprefetche0` for stores. Rely on the L2 HWP before adding `vprefetch1`.
