# KNC optimization sources: six documents checked against ADR-0009 (2026-11-07)

**S12-13 edition/status correction (2026-11-14).** This is a historical
review; proposals and “today” statements are not a current feature list.
Use [knc-references.md](knc-references.md) for new citations. Original SSDG
page citations below are **superseded as usable current locators**: the
163-page PDF's edition is unidentified. Recovered R01 is 328207-001EN,
November 2012, **201 pages**. 328207-002 (June 2013, reported by R22 p.8)
and 488596 rev.2.03 are separate, unrecovered editions.

| Topic in the old SSDG citations | Verified replacement locator and qualification |
| --- | --- |
| Latency, prefixes, AGI and hardware prefetch | R01 p.19; typical latency is not every instruction's latency; also R02 pp.32–34,56 |
| L2 capacity/banks/access rate | R01 pp.19,22: 512 KiB; bank count and duty-cycle descriptions disagree internally, so no unqualified port constant follows |
| TLB structure | R01 pp.22–23: 64 small-page plus eight large-page first-level data entries; the second level is not 64 additional small-page translations |
| Ready buffers and alternate-cycle issue | R01 pp.19,23–24; no modern decoded-loop-cache claim follows |
| PMU overview | R01 p.24's counter count is superseded by R10 pp.5–7,11 and R11a `knc_pmu`: two 40-bit counters per hardware thread; access remains unverified |

Instruction semantics below use R27. Other unrecovered section/page references
remain historical citations, not silently remapped to R01.

Research note for the lead (owner's request: check six documents, update the optimization approach
where they add something). Nothing here is applied yet: ADRs, backlog and code are unchanged.
Tags: **[fact]** documented hardware or ISA behaviour; **[vendor]** Intel or PRACE recommendation or
reported measurement; **[inference]** this note's reasoning. "Card" means our own measurements
(`knc-characterization.md`, `card-runs-s6.md`, `wrf-input-2026-11-06.md`).

## Sources and access

| # | Document | Read from | Status |
|---|---|---|---|
| 1 | Intel Xeon Phi System Software Developer's Guide (SSDG), 163 pp. | the Liverpool URL (PDF fetched, text extracted outside the repo) | Read: ch. 2.1 (core, caches, TLB, threads), 2.1.9, 4.2.12. Ch. 7 (vector architecture) only points to the ISA manual. Edition date not on the pages read |
| 2 | Intel 327364-001 ISA reference | the local text `.work/_shared/intel-327364-001-xeon-phi-isa.txt` (same document number); the LSU link was not fetched | Read the prefetch, clevict, NR/NGO store and EH-hint sections |
| 3 | apc-llc/gcc-5.1.1-knc | GitHub commit list (HEAD `af7cc04`, matching `donor-inventory.md`) plus `git show af7cc04:` in the local donor checkout | Read `knc_cost`, the `"knc"` processor entry, option override and `x86-tune.def` |
| 4 | Tian et al., *Practical SIMD Vectorization Techniques for Intel Xeon Phi Coprocessors*, IPDPSW 2013, pp. 1149-1158 | the KFUPM URL (PDF) | Read in full |
| 5 | Intel, *Recognizing and Measuring Vectorization Performance* | the Intel URL (HTML) | Read through a summarising fetch only, not verbatim |
| 6 | PRACE *Best Practice Guide Intel Xeon Phi* **v2.0, 2017-01-31** | the PRACE URL (PDF) | Read ch. 2.1, 4, 6.1.2, 13.1, 15.1 (KNC parts). v2.0 is newer than the v1 (2013) some people cite; the KNC sections look the same |

No document was unreachable. Fetched PDFs were saved by the fetch tool under
`~/.claude/projects/.../tool-results/`, not in the repo.

## 1. What each document gives a compiler

1. **SSDG.** p.16 (§2.1.1): integer and mask latency 1, vector latency 4 at throughput 1; dependent
   store-to-load about 12 clocks; the decoder is a two-cycle unit, so one context cannot issue in
   consecutive cycles. The prefixes 66 (operand size), 67 (address size), lock and REP take 2 decode
   cycles; 62, c4, c5, REX and 0f take none. "Kunit" (L1) bank conflicts cost 2 dead clocks.
   p.17 (§2.1.3): AGI of at least 3 clocks; L2 has a streaming prefetcher with **16 streams**, each
   limited to a **4 KB page**, and up to 4 requests once a direction is seen. About **38 outstanding
   requests per core**. A load miss suspends only its own thread. p.19: L2 can be accessed only every
   other clock. p.21 (§2.1.4): **L1 dTLB 64 x 4 KB (256 KB reach)** plus 8 x 2 MB; L2 TLB 64 entries,
   used as a PDE cache for 4 KB pages; iTLB 32 x 4 KB only. p.22 (§2.1.5): each thread has a 2-bundle
   ready buffer, and a branch to a target outside it refetches.
2. **ISA 327364-001.** VPREFETCH (p.641): **the hardware drops a VPREFETCH that hits L1**, so a
   prefetch cannot warm L2 for a line already in L1. Prefetches never fault. The MVEX form scales disp8
   by 64. The hint table gives 0/NTA to L1, 1/2 to L2, an E variant for exclusive, and 2/NTA non-temporal.
   VMOVNRAPS/PD (pp.388-391): the no-read saving applies **only on a cache miss, only unmasked, and only
   without down-conversion**. VMOVNRNGOAPS/PD (pp.393-398) are weakly ordered "to increase the
   throughput", and need a fence (`lock add [rsp],0` or `xchg`) before other threads read.
   CLEVICT0/1 (pp.624-627) evict from L1 or L2, never fault, and are not broadcast.
3. **Donor GCC 5.1.1.** `-march=knc` is `PROCESSOR_PENTIUM` (`i386.c` ≈3426), so the donor inherits
   Pentium (P5, in-order U/V) tuning flags and `pentium.md` scheduling. `knc_cost`: L1 and L2 size
   fields 8 and 8 (wrong; probably copied), prefetch block 0, 0 parallel prefetches, so no software
   prefetch. FP add/mul 3, fdiv 39, fsqrt 70, imul 11, idiv 25. memcpy/memset use a loop up to 32 bytes,
   `rep movsq` up to 8 KB, then libcall. It disables CMOV and inter-unit moves. The donor has no packed
   vectorizer patterns, so it offers no vectorizer, prefetch or alignment tuning to inherit.
4. **Tian et al. (ICC's KNC vectorizer).**
   - §III: ICC vectorizes peel, remainder and short loops with masks. Remainder masks are never empty,
     so they need no zero-mask check.
   - §IV: alignment peeling plus multi-versioning. Unmasked unaligned accesses use unpack/pack. Masked
     or converting unaligned accesses use **gather/scatter for fault safety**, because masked IMCI
     accesses fault on masked-out lanes; only gather/scatter do not.
   - `-opt-assume-safe-padding` assumes 64 bytes of padding after every object and allows unpack plus
     blend instead (+10% on BlackScholes and MD kernels).
   - §V: 2-D vectorization of 4x4 matrices with swizzles, shuffles and broadcast loads.
   - §VI: Fig. 6.2, masked short-loop vectorization lifts 31-element loops from 2.89-3.32x to
     3.28-7.68x over scalar. A 7-iteration DP loop goes 2-5x faster. Fig. 6.3, known alignment is worth
     1.32-1.45x. Fig. 6.4, conventional vectorization of 4x4 matmul is **about 50% slower than scalar**;
     2-D vectorization gives 1.15x single and 5.42x paired. ICC 13, native, `-mmic -openmp`.
5. **Intel article.** Vectorization intensity = `VPU_ELEMENTS_ACTIVE / VPU_INSTRUCTIONS_EXECUTED`
   (about 8 is good for DP, 16 for SP; 1-3 is poor). KNC VPU counters overcount, so low values are
   conclusive and high values only suggestive. ICC reported one loop as vectorized that ran about 10x
   slower than scalar. The ICC compiler "makes extensive use of explicit prefetch". It uses
   `-qopt-report=3`.
6. **PRACE BPG.**
   - §2.1.1: at least 2 threads per core are needed to fill the vector pipe.
   - §4: software prefetch is on by default from `-O2` (`-opt-prefetch=n`).
   - §6.1.2 and §9: "highly tuned" code may saturate at 2 threads per core, but in general 3-4 are
     needed. Make threads per core a parameter.
   - §13.1.1: Fortran `-align array64byte` and `-align rec64byte`, and `__assume_aligned`.
   - §15.1.1, STREAM: static arrays beat `malloc`. `-opt-prefetch=4 -opt-prefetch-distance=64,32`
     (L2 at 64 iterations, L1 at 32) helped all four kernels. Streaming stores barely moved Triad
     (134.9 to 135.2 GiB/s).
   - §8 mentions `MIC_USE_2MB_BUFFERS` (MKL only).

## 2. New insights

Each entry lists: the claim, its source, what the card says, and the consequence.

**I-1. NR stores: we measured the wrong instruction for the streaming case.**

**Status superseded, S12-13:** C1 subsequently measured NGO including
completion, and `imci.md` implements NGO with `knc_storent_fence`. The
completed-worker estimate is 204.5 GB/s, distinct from the 226.1 worker-median
aggregate; later sweep 2 reports 169.74 GB/s best write under different work.
R27 pp.393–398 remains the eligibility/ordering authority. The earlier
measurement request below is history, not outstanding acceptance.
- **Claim:** `vmovnraps` saves the read only on a miss, only unmasked and only without
  down-conversion. The weakly ordered `vmovnrngoaps` exists to raise store throughput and needs a
  fence. [fact, ISA pp.388-398] PRACE saw almost no gain on STREAM at full card. [vendor]
- **Card:** S6-03's `*.store_stream` rows use `vmovnraps` (`.work/_shared/S6-03/kernels.s` ≈9199), not
  the NGO form. On one core they are slower: 157 vs 38 cycles per line in memory, and 27-36 vs 2-25
  in cache. The in-cache rows are expected, since NR helps only on a miss. The memory row says nothing
  about NGO or about bandwidth at 60 cores.
- **Consequence:** E5-08 must compare `vmovaps`, `vmovnraps` and `vmovnrngoaps` plus one fence, at 1
  core and 60x4, on memory-sized write-only output. Only the NGO form is a serious candidate. Its
  weak ordering is an ABI/memory-model issue: the compiler must emit a fence after the loop, before
  any store that publishes the data and before any call or return (so OpenMP barriers are covered).
  Never use NR or NGO under a mask or with down-conversion; that gives no benefit. Card check C1.

**I-2. The L1 dTLB covers only 256 KB, half of L2, and our card has 4 KB pages only.**

**“4 KB pages only” and the keep-512 policy below are superseded (S12-13).**
R09 p.4 documents card-side THP in a named MPSS update; the later local
bandwidth sweep obtained actual huge pages in 48 configurations. Ordinary
malloc promotion remains unknown. R01 pp.22–23 supports the translation
distinction. Current `knc_processor_costs` uses **256 KiB effective L2** while
physical capacity is 512 KiB. S12-12 G08 checks real mappings before any retune.
- **Claim:** 64 x 4 KB L1 dTLB entries, with the L2 TLB acting as a PDE cache for 4 KB pages.
  [fact, SSDG p.21]
- **Card:** we have no huge pages. Our "L2 working set" rows (M2 L2 rows; `l2.*` in the
  characterization) may include L1 dTLB misses, depending on how many pages the four siblings touch.
  Not separated so far.
- **Consequence:** [inference]
  - Blocking and interchange heuristics should treat about **256 KB per core (64 KB per thread at 4
    threads)** as the effective L2 tile when pages are 4 KB. Keep the `l2-cache-size` parameter at 512
    (it is a fact), but have E5-07 and loop blocking use the TLB-limited figure.
  - The M2 L2 row should note it.
  - Card check C4.

**I-3. The L2 hardware prefetcher is narrow: 16 streams per core, never across a 4 KB page.**
- **Claim:** 16 streams, each limited to a 4 KB page, up to 4 requests per stream. [fact, SSDG p.17]
  No L1 hardware prefetcher is described (Klemm says none). [fact]
- **Card:** WRF: about 29 arrays per point, and `vprefetch0` two rows ahead gave 2.4x. That fits:
  4 threads x 29 streams overwhelms 16 streams. The single-thread memory load rate (37 cycles per line
  against 357 latency) shows the prefetcher works for one stream.
- **Consequence:** E5-07 needs a stream-count trigger [inference]. Loops with more than about
  16/(threads per core) concurrent streams, so 4 at 4 threads, get L2 software prefetch even when the
  stride is unit. Loops with few unit-stride streams may need only `vprefetch0`.

**I-4. Our prefetch parameters are off by the density factor.**

**Historical parameter proposal, superseded (S12-13).** Current
`ix86_knc_prefetch_distances` uses 16/32-line near/far defaults with a
stream×density footprint rule; `simultaneous_prefetches=1024` is pass
bookkeeping. Neither 4, 8 nor 1024 measures a hardware queue (R01 p.19;
R06 Table V p.55:19 is a different, pre-production experiment).
- **Claim:**
  - About 38 outstanding requests per core. [fact, SSDG p.17]
  - A thread issues at most every other core cycle, and every 4th at 4 threads. [fact]
  - ICC's tuned STREAM distances were 64 (L2) and 32 (L1) iterations. [vendor, PRACE §15.1.1]
- **Card / tree:** `i386-options.cc` sets `prefetch-latency=360` ("instructions") and
  `simultaneous-prefetches=4`. GCC counts the latency in **instructions of this thread**. 360 core
  cycles is about 90 thread issues at 4 threads, or about 180 at 2. And 38/4 gives about 9 per thread,
  not 1.
- **Consequence:** set `prefetch-latency ≈ 360 / threads-per-core x (issues per cycle ≈ 1-2)`, derived
  from `--param=knc-threads-per-core`, and `simultaneous-prefetches ≈ 8`. [inference] E5-07 sweeps
  them (C5).

**I-5. A prefetch that hits L1 is dropped, so only staggered distances work.**
- **Claim:** a prefetch that hits L1 is dropped. [fact, ISA p.641]
- **Consequence:** issue the far `vprefetch1` before the near `vprefetch0` for the same line, with the
  L2 distance strictly larger than the L1 distance (ICC: 64/32). Never issue `vprefetch1` for lines
  that the loop has just touched. Do not use prefetch as a cheap "warm L2" in loops that fit in L1
  (ADR-0009 point 5 and E7-06 already say "none for loops that fit in cache"). [inference]

**I-6. Masked tails: ICC's safe forms are aligned masks or gather/scatter, never masked unpack.**
- **Claim:** masked IMCI accesses fault on masked-out lanes; gather/scatter do not. [fact, Tian §IV,
  matching our S3-03 probe and ADR-0007/0008] For an unaligned masked tail ICC emits
  `vgatherdps`/`vscatterdps`; with `-opt-assume-safe-padding` it uses unpack plus blend.
  A non-empty remainder mask needs no zero check. [vendor]
- **Card:** M2 length 17 runs at 0.084 ns per element against 0.040 for IMCI; length 15 is GF 0.45.
  Our gather on one line costs 7 cycles per core (two lines about 14), against about 1 cycle per
  element for x87 tail elements (add) and more for loads and stores.
- **Consequence:** E4-04 has three safe tail strategies, in this order:
  1. a masked **aligned** tail when the base is known to be 64-byte aligned;
  2. a masked vector peel to alignment, then aligned body and aligned masked tail (safe because every
     aligned line holding a valid element is mapped);
  3. a gather/scatter tail for unknown alignment.

  An opt-in `-mknc-assume-safe-padding` (with GCC padding its own statics) is a later option. Card
  check C6 sets the length crossovers.

**I-7. Masked short-loop vectorization is ICC's main KNC lever.**
- **Claim:** 7-iteration DP loops ran 2-5x faster; 31-element loops went from about 3x to up to 7.7x.
  [vendor, Tian §III and §VI-D]
- **Card:** WRF rows are 7-9 cells (46% lane use).
- **Consequence:** confirms the Sprint 8 masked-tail item as the top weak spot.
  - Add whole-loop masking (no scalar loop at all) for trip counts below the VF: GCC's
    `vect-partial-vectors-usage=2` path for KNC, once its masked loads are aligned or gathers.
  - E5-06 should report length 7 and 9.

**I-8. Small matrices: plain loop vectorization can be slower than scalar.**

**S12-13 qualification:** the blanket lane-use rejection proposed below is
superseded by the later diagnosis in `knc-small-matrix.md`. R13 §V pp.1153–1154
describes one transformation, not a universal 25% threshold. Static lane or
instruction counts alone do not establish a bottleneck or removable time.
- **Claim:** 4x4 matmul vectorized conventionally runs about 50% slower than scalar. [vendor, Tian
  Fig. 6.4]
- **Card:** mat8 has about 2% of the IMCI gain and mat16 about 26%.
- **Consequence:**
  - The cost model must reject inner-loop or outer-loop vectorization whose lane use is ≤ 25%. That is
    the 4-way-in-16 case Tian names. In those cases prefer full unroll plus SLP. [inference]
  - Consider pulling "small-matrix 2-D vectorization" out of Parked into E7, as an SLP pattern with
    swizzle and broadcast-load (`{4to16}`) [inference]. Tian reports 5.4x on the paired kernel.

**I-9. Known alignment is worth 1.3-1.45x, and ICC gives users flags for it.**
- **Claim:** known alignment gives 1.3-1.45x [vendor, Tian Fig. 6.3]. ICC offers Fortran
  `-align array64byte` and `rec64byte` [vendor, PRACE §13.1.1]. On STREAM, static arrays beat `malloc`
  [vendor, §15.1.1].
- **Consequence:** `-march=knc` should give 64-byte alignment by default to:
  - static and global arrays of 64 bytes or more (`DATA_ALIGNMENT`);
  - local arrays (`LOCAL_ALIGNMENT`);
  - gfortran `ALLOCATE` with a vectorizable element type, through libgfortran's allocation (E6-02).

  Check what GCC-KNC already does before ticketing. [inference]

**I-10. Generic x86 tune flags vs the donor's Pentium flags.**
- **Claim:** 66 and 67 prefixes cost 2 decode cycles. [fact, SSDG p.16] The donor tunes as Pentium.
  [fact]
- **Tree:** GCC-KNC uses `PROCESSOR_GENERIC` tune flags (`i386-common.cc:2221`), with its own costs and
  `knc.md`. Generic flags assume an out-of-order Core. S6-06 already had to undo inherited macro-fusion.
- **Consequence:** add a `-mtune=knc` tune-flag audit [inference]:
  - turn off `X86_TUNE_FAST_PREFIX` (promotes HImode to SImode, avoiding 66 prefixes);
  - check `PARTIAL_REG_*`, `READ_MODIFY_WRITE`, `USE_INCDEC`, `AVOID_MEM_OPND`, the macro-fusion
    flags, `SINGLE_PUSH` and `PAD_RETURNS`;
  - choose each on the in-order U/V model, measuring where it matters.

  The Pentium list is a starting point, not an answer: KNC is not P5.

**I-11. Thread density: our characterization and the vendor guidance agree.**
- **Claim:** at least 2 threads per core are needed; "highly tuned" code saturates at 2, most code
  needs 3-4. [vendor, PRACE §2.1.1 and §9; SSDG p.17]
- **Card:** 2 threads reach one vector op per cycle; WRF found 2 per core best.
- **Consequence:** the number of chains is the one density-dependent choice. Two accumulators are
  enough at every density ≥ 2 and cost only registers at 4 threads (32 zmm). So consider making the
  **default accumulator count 2**, independent of the density parameter. [inference] Card check C7
  must show that 2 chains at 4 threads lose nothing. Keep 4 threads per core as the measurement
  density (ADR-0010), and always report 2 next to it.

**I-12. Code size: the iTLB and the ready buffer favour modest unrolling.**
- **Claim:** 32 KB L1I, iTLB 32 x 4 KB (128 KB) with no large pages, 2-bundle ready buffer, and a
  branch outside the buffer refetches. [fact, SSDG p.21-22]
- **Consequence:** keep the vector unroll cap at 2 (`knc-costs.md`). Keep code alignment modest. Treat
  full unrolling as a code-size cost in E7-04. [inference] No card evidence yet.

**I-13. Measuring vectorization intensity.**
- **Claim:** VPU counters give elements per vector instruction; they overcount, so low values are
  reliable. [vendor, Intel article]
- **Consequence:** E5-03 per-loop reports could pair the static VF with a card-measured intensity
  where `perf` or the PMU is reachable. That is optional; whether the card exposes the counters to us
  is unknown.

**Confirmed, nothing new:**
- dependent store-to-load about 12 (SSDG) matches our memory-operand latency 12;
- vector latency 4 at throughput 1 matches;
- AGI "≥3 clocks" (SSDG) matches our measured one issue slot of penalty at one thread;
- unpack/pack beats gather for unmasked unaligned access (Tian), as in our table;
- masks never suppress faults (Tian), as in S3-03.

**Minor conflict:** SSDG gives L2 "raw latency 11 clocks" (and "idle access about 80 cycles", whose
referent is ambiguous). We measure 24-26. Ours is a dependent vector-load chain, including the L1
miss, so it is not a contradiction worth a card run.

## 3. Proposed changes (text the lead can apply)

### ADR-0009 amendment 1 (proposed)

> **Amendment 1 (2026-11-07): sources beyond Klemm.** `docs/research/knc-optimization-sources.md`
> adds the SSDG, the ISA manual, Tian et al. (ICC's KNC vectorizer) and PRACE. Changes:
> 1. Point 5, streaming stores: no-read stores help only on a miss, unmasked and unconverted. The
>    candidate is the weakly ordered `vmovnrngoap*`, which requires a fence before the data is
>    published (at the latest before any call, return or loop exit). Default off until E5-08 shows a
>    gain at 60 cores.
> 2. Point 5, prefetch: the L2 hardware prefetcher tracks 16 streams per core within 4 KB pages, and
>    L1 has none. The far (`vprefetch1`) distance must exceed the near (`vprefetch0`) one, because a
>    prefetch that hits L1 is dropped. Prefetch latency and simultaneous prefetches are expressed per
>    thread and derived from the thread density (about 38 outstanding requests per core).
> 3. Point 5, alignment: with 4 KB pages the L1 dTLB covers 256 KB, so blocking heuristics use the
>    smaller of L2 and the TLB reach. Statics, globals and Fortran allocations get 64-byte alignment by
>    default.
> 4. New point 9, short loops: below the vector length, and for every remainder, the preferred code is
>    masked vector code. Use aligned masked accesses when alignment is known or peeled, and
>    gather/scatter otherwise; never masked unpack/pack without the opt-in safe-padding assumption.
>    Vectorization whose lane use is ≤ 25% is rejected in favour of full unroll and SLP.
> 5. Point 3, chains: two independent accumulators are the density-robust default, subject to C7.
> 6. Point 6: the `-mtune=knc` tune-flag set is chosen for an in-order U/V core, not inherited from
>    generic x86 (I-10).

### Backlog (proposed text)

- **E5-07** (Standard): append: "Distances per ADR-0009 amendment 1 point 2: L2 distance > L1 distance;
  prefetch latency and simultaneous prefetches derived from `knc-threads-per-core`; L2 software
  prefetch also for unit-stride loops with more streams than 16/(threads per core). Sweep against
  ICC's 64/32 iterations (C5)."
- **E5-08** (Standard): replace the measurement clause with: "measure `vmovaps`, `vmovnraps` and
  `vmovnrngoaps` with a fence on memory-sized write-only output at 1 core and 60x4 (C1); NGO needs a
  fence before publication; never masked or converted."
- **E4-04** (Deep): append: "Tail strategies in order: aligned masked tail; masked vector peel to
  alignment; gather/scatter tail for unknown alignment (Tian et al. §IV). Whole-loop masking for trip
  counts below the vector length. Crossovers by C6 at lengths 1-33."
- **E5-12** (new, Standard): "`-mtune=knc` tune-flag audit: `FAST_PREFIX` off (66/67 prefixes cost 2
  decode cycles, SSDG p.16); review partial-register, RMW, inc/dec, memory-operand, macro-fusion and
  push flags for the in-order core; T1 scans plus one card before/after."
- **E5-13** (new, Standard): "Default 64-byte alignment for static, global and local arrays ≥ 64 bytes
  under `-march=knc`, and for gfortran `ALLOCATE` of vectorizable types (with E6-02); measure on the
  M2 short-length rows."
- **E5-02 / E5-11 note:** "Reject vectorization with lane use ≤ 25% when full unroll plus SLP is
  possible (Tian Fig. 6.4: 4x4 matmul vectorized is about 50% slower than scalar)."
- **Parked to E7:** move "Small matrix 2-D vectorization" to **E7-07** (Standard, after M2): "SLP
  patterns for 4x4 and 8x8 fixed-shape kernels with swizzle, broadcast loads and `vpermf32x4` (Tian
  §V: 5.4x paired)."
- **Parked:** "`-mknc-assume-safe-padding` (ICC `-opt-assume-safe-padding`, +10% reported): masked
  unpack plus blend when every object has 64 bytes of mapped padding." Needs an ADR, since it is a
  user-visible correctness contract.

### Sprint 8 tuning block (proposed order)

1. E4-04 masked tails, with the three strategies of I-6 (largest measured gap: length 17 at GF 0.25).
2. E5-07 prefetch, with the I-3 to I-5 parameters.
3. Small matrix: apply the ≤ 25% lane-use rejection first. Expect mat8 to move to full unroll; only
   then consider E7-07.
4. E5-11 as planned.
5. E5-12 (tune flags) if capacity allows; it is cheap.

## 4. Card checks proposed (the lead runs them)

| ID | Question | Measurement it touches |
|---|---|---|
| C1 | Do `vmovnrngoaps` plus a fence beat `vmovaps` on memory-sized write-only output at 60x4? | `memory.store_stream` 157 vs 38 (one core, `vmovnraps` only) |
| C2 | Does `vprefetch0/1` pair with a vector op (V pipe), or take a U slot? | Prefetch cost in the model (unmeasured) |
| C4 | TLB: page-stride loads at 128, 256, 384 and 448 KB per core, 1 and 4 threads | `l2.*` rows and the M2 L2 rows |
| C5 | Prefetch distance sweep (L1 8-64, L2 32-128 iterations) on stream, stencil and short-row kernels at 2 and 4 threads | E5-07 |
| C6 | Tail at lengths 1-33: x87 scalar vs aligned masked vs peel+masked vs gather tail | M2 lengths 15, 17 |
| C7 | Reductions with 1 vs 2 accumulators at 4 threads per core | `knc-costs.md` chain choice |
| C3 | Optional: 16-bit ALU op (66 prefix) vs 32-bit throughput | I-10 |

## Limits of this note

- The Intel article was read only through a summarising fetch.
- The SSDG edition and date were not checked.
- The PRACE guide read is v2.0, not v1.
- ICC's own default prefetch distances for `-mmic` are not stated in any of the six documents; only
  PRACE's tuned 64/32 is.
- Every [inference] item still needs card evidence before it becomes a default.

## Supplement: the Itanium-to-KNC report (2026-11-07)

The input is the lead's summary of an owner-supplied GPT deep-search report, "Itanium-to-KNC Compiler
Optimization Integration Report" (scratchpad `itanium-to-knc-report.md`). It is unverified material,
checked here against the sources above, our ADRs, our measured tables and the GCC 16 tree
(`.work/_shared/gcc`). The report's Itanium descriptions are outside our scope and are not checked.

### Its KNC and GCC claims

| Claim | Verdict | Source |
|---|---|---|
| "8 512-bit vector registers (zmm0-zmm7 in IMCI)" | **Wrong.** There are 32 (`zmm0`-`zmm31`). The report later says 32 itself | SSDG §2.1.9; ADR-0004 |
| 8 mask registers `k0`-`k7` | Correct | ISA 327364; ADR-0007 |
| "32 64-bit general registers per thread" | **Wrong.** x86-64 has 16 GPRs, replicated per thread | SSDG §2.1.5 |
| "IMCI uses VEX-like multibyte prefixes" | **Half right.** Vector instructions use **MVEX** (62h). Only mask and some scalar instructions use the C4/C5 "VEX-like" prefix | ISA §3.1-3.3, p.40 |
| Two pipes; vectors only on U | ~~Correct~~ **Superseded S12-13:** selected vector stores/packstores may use V; the measured pairs do not cover every opcode/encoding | R02 pp.34,56; R10 p.16; old citation SSDG p.16 retained as history |
| "V-pipe handles most scalar"; "some integer ops only on V" | **Wrong as stated.** Scalar integer and mask ops issue on either pipe: two per issue slot, `scalar_add.rt` 1.07 at one thread. The restricted pipe is V ("cannot execute all instruction types"), not U | SSDG p.16; characterization point 2; `knc.md` |
| One thread reaches at most 50% of issue | Correct | SSDG p.17; characterization point 1 |
| 16 SP or 8 DP FMA lanes per cycle per core | Correct | Tian §I; characterization |
| "Hardware prefetching in L1/L2" | **Wrong for L1.** Only L2 has a hardware prefetcher | SSDG p.17; Klemm |
| "Up to 4 concurrent prefetch streams in L2" | **Wrong.** There are 16 streams; "up to 4" is the requests per detected stream | SSDG p.17 |
| Memory latency "~100+ cycles" | **Wrong by about 3.5x.** We measure 357-366 cycles; Klemm gives about 275 ns | characterization point 8; ADR-0009 |
| CMOV for small cases and scalar if-conversion | **Wrong.** KNC has no CMOV and no FCMOV/FCOMI | SSDG §4.2.18.2, §4.2.18.6; ADR-0002 |
| `prefetchnta` / `prefetch0` | **Wrong mnemonics.** PREFETCH is not supported; KNC has `vprefetchnta`, `vprefetch0/1/2` and `vprefetche*` | SSDG §4.2.12; ISA p.641 |
| `lfence` | **Wrong.** SFENCE, LFENCE and MFENCE are not supported; ordering uses a LOCK-prefixed instruction or CPUID | SSDG §4.2.18; E2-04 |
| Vectorizer emits `vblendvpd` and `vpcmpgtps` | **Wrong.** These are SSE4.1/AVX-style names, and `vpcmpgtps` exists nowhere. IMCI uses `vblendmps/pd` with a mask, `vcmpps/pd` with a predicate into a mask, and `vpcmpgtd` for int32 | ISA pp.129, 149, 470; ADR-0007 |
| Example `vmulpd %zmm2 {k0}, [x], [y]` | **Wrong.** IMCI arithmetic takes at most one memory operand. `k0` cannot be a write mask (it means "no mask"). The example also mixes an SP compare with a DP multiply | ISA §3; ADR-0007 |
| "Two memory ops cannot pair on U and V" | Unverified. Not measured (our `pair.*` rows cover vector, scalar and mask ops, not load+load) | none |
| Branch misprediction "~30 cycles" | Unverified. Not measured; `knc-costs.md` keeps generic branch estimates | none |
| No scalar predication; masks only for vectors | Correct | ISA; ADR-0007 |
| No rotating registers, register stack or ALAT | Correct | ISA |
| Files `config/i386/knights.c`, a `.sched` file, `x86/tstops.md`, `ipa-pg` | **Do not exist** in GCC 16 or the donor. The donor's additions are in `i386.c` and `knc.md`, with no scheduler (0 reservations). GCC-KNC's are `i386-knc.cc` and `knc.md` (DFA, S6-06). GCC scheduling models are `define_automaton` in `.md` files; there is no `.sched` type | `.work/_shared/gcc/gcc/config/i386/`; donor `af7cc04` |
| "Modulo scheduling is not enabled by default on i386, so add it" | **Misleading.** SMS needs a `doloop_end` pattern (`modulo-sched.cc:339-351`, `doloop_register_get`), and i386 defines none. `-fmodulo-sched` therefore does nothing on x86 and KNC today; turning on the flag is not enough | `gcc/modulo-sched.cc`; `doloop_end` is defined for aarch64, rs6000, s390, ia64 and others, but not i386 |
| PGO "fully applicable" | **Partly.** Instrumented PGO needs no PMU, but it needs libgcov on the card and `.gcda` output from threaded runs, neither tested. AutoFDO needs `perf` sampling, not established for us | BACKLOG Parked (PGO); I-13 |

### Useful ideas, judged against our model

**(a) Swing modulo scheduling: not now. [inference]**
- **Cost:** SMS needs a `doloop_end` expander for i386. That means a new loop-counter RTL form in
  shared i386 code (ADR-0006 hook rules), plus SMS's own maintenance risk.
- **Benefit (historical overgeneralization, superseded S12-13):** at the production density of 4, our tables show latency hidden. At 2 threads per core
  (WRF's best), a thread issues every other cycle. A 4-cycle vector chain then needs 2 independent
  operations, and a 12-cycle memory-operand chain about 6. Unroll by 2, multiple accumulators
  (ADR-0009 point 3) and the haifa scheduler with `knc.md` supply that for reductions and simple
  streams.
  **Correction:** four ready siblings cover a four-cycle arithmetic chain,
  not every 6/7-cycle or memory dependency (R02 pp.32–33; R17 slide 12).
- **Where SMS would add something:** long load-compute-store chains without a reduction, at 1-2
  threads per core.
- **Plan:** measure first (C9). Adopt only if unroll+schedule leaves a gap.

**(b) Software pipelining vs multiple accumulators.** For reductions, accumulators are software
pipelining of the recurrence. For other loops, the equivalent is unroll by U, then schedule: GCC's
unroller plus sched1 interleaving, which also gives modulo variable expansion (the rotating-register
substitute). The knob that matters is U as a function of density, given the 12-cycle memory-operand
latency. This is a cost and default choice (E5-09), not a new pass. [inference]

**(c) PGO and AutoFDO.** Instrumented PGO is feasible without hardware counters. It needs libgcov for
k1om (whether our libgcc build produces it is unverified), `.gcda` written under `/tmp`, and
`-fprofile-update=atomic` (lock-prefixed RMW exists; no `mfence` needed). AutoFDO waits until `perf`
sampling works on the card. [inference]

**(d) Itanium practice that maps onto KNC.**
- **Predication becomes masks:** already E4-01 and ADR-0007.
- **Scalar if-conversion without CMOV:** GCC's noce path falls back to store-flag (`setcc`, `sbb`,
  `and`/`or`) sequences, governed by `BRANCH_COST`. Ours is a generic estimate. Measure the
  misprediction penalty (C10), set it, and check that short diamonds become setcc sequences.
- **FP selects:** without FCMOV, they stay branches or move to lane 0 of a `zmm` with a masked
  `vblendmps`. That is a point for E5-04 (source-format scalar in `zmm`).
- **Control speculation:** the non-faulting memory forms are `vprefetch*` and `clevict*` (ISA p.641,
  p.624) and masked-off gather lanes (ADR-0008). Hoist a prefetch, not the load, above a guard. The
  gather tail (I-6) is the speculative-vector-load substitute.
- **Data speculation (ALAT):** the substitute is runtime alias versioning, which the vectorizer
  already does.

**(e) Benchmarks.** Its list against our corpus (`corpus-and-coverage.md`):

| Its benchmark | Our corpus or M2 |
|---|---|
| STREAM triad | `stream.c` 5.10 (C1, C5) |
| Sparse update | HPCG (conditional) |
| DGEMM | PolyBench gemm, plus the M2 small-matrix kernels |
| 7-point stencil | PolyBench heat-3d / jacobi-2d, plus the M2 stencils |
| FFT | NPB FT, which does not compile yet |
| N-body | **Missing.** Tian also uses it, and its `rsqrt`/division makes it a natural judge for E4-03 and E7-02 |

### Proposed backlog text

- **E5-09 addition** (Standard, M2 follow-up): "Unroll factor as a function of
  `knc-threads-per-core`, covering the 4-cycle vector and 12-cycle memory-operand latencies at that
  density (C9)."
- **E7-04 addition** (Standard, M4): "Measure the branch-misprediction penalty (C10). Set
  `BRANCH_COST` and the KNC branch costs from it. Check that scalar if-conversion uses setcc/sbb
  sequences (no CMOV). Evaluate `vblendmps` lane-0 FP selects with E5-04."
- **E7-08** (new, Standard, M4, after E6 runtimes): "Instrumented PGO on the card: libgcov for k1om,
  `-fprofile-update=atomic`, `.gcda` under `/tmp`; one corpus program before and after
  `-fprofile-use`. AutoFDO stays parked until `perf` sampling on the card is shown." This replaces
  the Parked PGO row.
- **Parked** (new row): "Swing modulo scheduling: needs an i386 `doloop_end` (shared code, ADR-0006).
  Revisit only if C9 shows loops latency-bound at 1-2 threads per core after unroll and schedule."
- **E8 corpus addition:** "N-body (SP, with `rsqrt`) once E4-03 lands."

### Card checks

| ID | Question |
|---|---|
| C9 | At 1 and 2 threads per core, how far is GCC-KNC from IMCI on the M2 affine and stencil kernels with unroll factors 1, 2, 4? A remaining gap would justify SMS |
| C10 | Branch-misprediction penalty: random vs predictable branch in a scalar loop, at 1 and 4 threads |

### Verdict

Low value as a source.
- Most of its KNC facts are wrong or garbled: register counts, CMOV, fences, mnemonics, prefetch
  streams, memory latency, pipe roles.
- The GCC files it names do not exist, and its central recommendation (turn on `-fmodulo-sched`)
  cannot work on i386 without a `doloop_end` pattern.
- What survives is generic and already planned (masks, prefetch, U/V model, OpenMP), plus three small
  additions: a density-aware unroll factor, a measured `BRANCH_COST` with CMOV-free if-conversion,
  and instrumented PGO.
- Its roadmap should not be used.
