# KNC optimization sources: six documents checked against ADR-0009 (2026-11-07)

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
