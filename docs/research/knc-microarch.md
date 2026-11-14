# KNC core microarchitecture facts for the cost model, scheduler and prefetch (Sprint 6 input)

**Source update, S12-13 (2026-11-14).** New citations use
[knc-references.md](knc-references.md). The 330991-001 register manual below
was not recovered by S12-10; its unique register details remain **reported**.
R01 is the recovered 201-page November 2012 SSDG; R17 is the 2014 Klemm deck.

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
  **The following inference and its free-slot consequence are superseded (S12-13).**
  Pipe 1 feeds only the scalar register file. Taken together, this means vector and x87
  instructions issue only on the U-pipe, and a V-pipe slot can only take a scalar instruction
  (address arithmetic, loop counter, compare-and-branch).
  - For the scheduler (E5-05), interleaving scalar loop overhead with vector instructions fills
    the V-pipe for free.
  - x87 and vector code compete for the same pipe, which matters for mixed loops with an x87
    remainder.
  - *(to measure)* the exact pairing rules: which scalar instructions pair, and whether a vector
    instruction with a memory operand pairs.
  **Correction:** R02 pp.33–34 lists selected vector stores/packstores among
  V-pipe candidates; R10 p.16 defines a V-pipe VPU event. Ordinary vector
  arithmetic remains distinct from those classes. Pairing also depends on
  instruction length, displacement/immediate combination and prefixes (R02
  p.56). A scalar neighbor is not automatically free. The current `knc.md`
  abstraction needs S12-08's opcode/operand experiment before any change.
- **Confirmed (Klemm slide 11): a core cannot issue from the same thread in adjacent cycles.** The
  decoder is a fully pipelined 2-cycle unit, so a core needs at least two threads to use all its
  cycles. Scheduling is "smart" round robin, with 2 prefetched instruction bundles per thread
  (slide 10).
- **Scalar: dual-issue on U and V, 1-cycle latency, 64-bit data path** (slide 10).

## Caches, TLBs and prefetch

- **L1: 32 KB instruction and 32 KB data per core, each 8-way set associative** (330991 p.14).
  Each has its own L1 TLB, plus a shared L2 TLB and a TLB miss handler (diagram).
- **L2: 512 KB per core, 8-way, 64-byte lines, 8 banks, pseudo-LRU, MESI, 11-cycle raw latency,
  with a streaming hardware prefetcher. There is no L3** (Klemm slides 13-14). This corrects an
  earlier guess here of up to 16 ways from 330991's 4-bit way field.
- **L1 data: 8 banks, pseudo-LRU, 1 access per clock (read or write), about 38 concurrent accesses
  per core.** Access time is given as "1 cycle" on slide 13 and "2 cycle" on slide 14
  *(to measure)*. There is a **3-cycle address-generation interlock** (slide 13).
  **Qualification (S12-13):** R01 p.19 describes about 38 combined read/write
  requests across L1/L2, not 38 L1 miss slots. R06 Table V p.55:19 measures
  different resources on an engineering sample. R01 pp.19/22 also disagree
  on L2 banks and p.22 on duty cycle; neither inconsistency is resolved by
  importing one number into the scheduler. Physical L2 is 512 KiB; the current
  `knc_processor_costs` uses 256 KiB as a small-page translation heuristic
  (R01 pp.22–23), not a different hardware capacity.
- **Memory: GDDR5, 16 channels of 32 bits at up to 5.5 GT/s, about 275 ns access latency; the ring
  carries 180 GB/s, and a distributed tag directory reduces snoop traffic** (slide 13). Up to 61
  cores and 244 threads (slide 9).
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

## Vector unit (Klemm, "The Intel Xeon Phi Coprocessor", Intel, LMU seminar 2014-12-11, slide 12)

- 32 zmm registers and 8 mask registers per thread.
- The ALUs do int32 and float32 operations, float64 arithmetic, and **int64 logic only**, which
  matches the ISA (no V8DI multiply or compare; S4-04's carry add).
- They have ternary operations including FMA, and broadcast, swizzle and float16 up-conversion.
- **Most vector operations: 4-cycle latency, 1-cycle throughput**, which matches the 4-cycle round
  robin of the integer unit.
- Consequences:
  - ~~With four threads, each thread issues every 4th cycle, so a dependent chain never stalls.~~
    **Superseded (S12-13):** this only describes a four-cycle chain with four
    ready siblings. R02 pp.32–33 distinguishes longer swizzle/EMU and cross-pipeline
    paths; local characterization reports 6/7-cycle families and longer memory
    chains. R17 slide 12 says typical latency, not every dependency.
  - With one or two threads, a single accumulator stalls on its own latency. **The scheduler and
    cost model (E5-02, E5-05) must account for this, for example with several vector accumulators
    in reductions** (GCC's partial-sum splitting) when fewer than 4 threads run per core.
  - **The 3-cycle address-generation interlock:** a pointer register updated within 3 cycles of
    its use as an address stalls, as on the Pentium. Scheduler v0 should move pointer increments
    away from the accesses that use them.
    **Qualification (S12-13):** R01 p.19's three-clock setup is not three
    intervening instructions. Local characterization point 7 measured about
    one extra tick in its adjacent one-thread case; `ix86_adjust_cost` adds
    one before converting core latency to thread issue opportunities.
- On the same deck's case study (slides 33-37): loop interchange to a long unit-stride inner loop
  gave about 50% speedup, and an aligned multi-versioned loop (`vector aligned`) about 15% more.
  This supports versioning for alignment in the cost model.

## Ring and streaming stores (owner's images, 2026-11-05, from Intel slides)

**Status correction (S12-13):** the compiler proposals in this historical
section are implemented for eligible NGO stores with a publication fence
(`imci.md`, `knc_storent_fence`). C1 later measured completed NGO stores;
see characterization C1. R27 pp.388–398 defines NR/NGO eligibility and ordering.
The earlier images' gains are reported results, not a current universal gain.

- **The cores sit on a bidirectional ring.** Each core and its L2 has a tag directory (TD) stop on
  the ring, and the GDDR memory controllers sit on the ring between groups of cores. So an L2 miss
  goes to the TD that owns the line's address, which may be on the far side of the ring. The latency
  depends on distance *(to measure)*.
- **Streaming stores.** Intel's silicon data shows bandwidth more than 30% higher with streaming
  stores than without, at 50 cores (2 address/acknowledge rings, no ECC). Bandwidth keeps rising
  up to about 50 cores, so a bandwidth-bound loop needs most of the card to saturate memory.
- On KNC, the streaming store is the no-read-hint store (`vmovnrapd`/`vmovnraps`, and the
  `vmovnrngoap*` form with relaxed ordering). It writes a whole 64-byte line without first reading
  it from memory (no RFO).
  - **For the compiler:** a vectorized loop that overwrites whole aligned lines of an output array
    that it does not read could emit the NR form instead of `vmovaps`. That is the
    `-fopt-info`/cost-model work of Sprint 6, or a new backlog item (E5-08, "streaming stores for
    write-only full-line output, measured"). It is only legal when the whole line is written, so
    S4-05's masked epilogues and the misaligned split must keep the normal store.
  - *(to check in the ISA manual)*: the exact mnemonics, alignment rules and memory ordering
    (whether an `sfence`/`lock` is needed before another thread reads the data).

## Measurement hooks

- Each thread has two 40-bit performance counters (`PERFCNT0/1`, event selectors `EVSEL0/1`,
  330991 pp.35-37), and there is a core time-stamp counter (`TMEL/TMEH`).
  **Verified replacement citation (S12-13):** R10 pp.5–7,11 and R11a
  `knc_pmu` establish two 40-bit counters **per hardware thread**. R01 p.24's
  conflicting four-counter overview is superseded for this purpose. Neither
  counter availability nor RDTSC establishes permission or a wall clock.
- E5-01 can count cycles and events per kernel through these, if the card's MPSS exposes them
  (`/dev/cpu/*/msr` or a perf driver) *(to check)*.

## What this changes in the plan

**Historical proposals, superseded as a current inventory (S12-13).** Read
the bullets below with the pairing correction above and
[the digest](knc-digest-2026-11.md). Two-level prefetch already uses 16/32 lines
with a stream/density footprint rule; R01 p.19 and R09 p.4 constrain its
interpretation, not a universal replacement distance.

- **Cost model v1 (E5-02):** price vector and x87 instructions on one issue port (U), and scalar
  overhead as able to pair (V). Count a 64-byte line as one L1 access, and an unaligned
  load/store pair as two.
- **Scheduler v0 (E5-05):** pair a scalar instruction with each vector instruction where the
  dependencies allow, and measure at 1-4 threads per core.
- **Prefetch v1 (E5-07):** start with `vprefetch0` at an L1 distance for streaming loads, and
  `vprefetche0` for stores. Rely on the L2 HWP before adding `vprefetch1`.
