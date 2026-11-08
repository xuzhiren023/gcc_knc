# KNC optimization gaps: what the plans do not cover (2026-11-07)

Consultant note for the lead, answering the owner's question "have we exhausted all possible means
of optimization for KNC?". Inputs: `BACKLOG.md`, ADR-0009 with amendment 1, `knc-optimization-sources.md`,
`imci-vs-avx512.md`, `knc-characterization.md`, `m2-result.md`, `wrf-input-2026-11-06.md`, PhiNix
Track H. Nothing here is measured; **[inference]** throughout unless a card figure is cited. Items
marked *verify* may already be true in the tree: one T1 scan settles each.

## 1. Verdict

**Not exhausted.** The plan covers what Klemm, the SSDG, Tian and PRACE teach: prefetch, masked tails,
alignment, pairing, density, tune flags. What is missing is mostly *policy and accounting*, not new
passes: the U pipe is the single issue resource and every vector load spends one of its slots; most
users compile at `-O2`, where GCC's defaults leave KNC loops scalar; the runtime's waiting behaviour
on a 4-way in-order core; and the TLB, which the card's 4 KB pages make the real L2 ceiling.

| Area | Headroom I believe remains | Confidence |
|---|---|---|
| Compiler code generation | 10-25% on L1/L2-resident vector kernels (the 13-29% gap to hand IMCI is mostly load slots); for `-O2` users, potentially the whole vector gain | medium |
| Memory system | 1.5-2.5x on short-row, many-stream code (prefetch, already planned, plus TLB reach) | medium-low (TLB unmeasured) |
| Threading / runtime | large on barrier-heavy programs (WRF: 54-58% of thread time waiting) | medium |
| Math library | 2-5% of WRF-like programs; more for ML operators (softmax, GELU) | high on bounds, low on size |
| OS / system | one lever worth real money (2 MB data pages); the rest speculative | low |
| Application level | the largest single lever (lane use 46% -> ~90% from tile shape; region fusion), but not ours | high that it exists |

## 2. Gaps, ranked by benefit over cost

| # | Idea | Why it matters on KNC | Benefit (uncertain) | Cost | Owner | Decisive card measurement |
|---|---|---|---|---|---|---|
| G1 | **Memory-operand alternatives for every V16SF/V8DF arithmetic and FMA pattern** (aligned full-width; single-use loads), not only V16SI | Loads are U-pipe ops; a memory-operand form has "throughput as a plain vector op" **[card]**, so folding removes one U slot per load. Load-heavy stencil bodies are U-bound at 4 threads | up to 1.3-1.8x on L1/L2-resident load-heavy kernels; likely most of the 13-29% M2 gap if the IMCI references fold loads | small (`imci.md` alternatives, tie rules) | compiler | T1: separate `vmovaps` loads with one arithmetic use on M2 kernels vs the references; card A/B of an L1-resident FMA kernel at 4 threads |
| G2 | **KNC `-O2` defaults**: `-fvect-cost-model=cheap` or `dynamic` (not `very-cheap`, which refuses loops needing an epilogue); `-fno-trapping-math` (the VPU cannot trap: MXCSR exception-mask bits are reserved per E6-02, so vector FP never raises); `-fversion-loops-for-strides`; predictive commoning (keeps `a[i-1..i+1]` in registers: load slots again). *Verify* each | ICC `-mmic -O2` vectorizes everything; GCC's generic `-O2` leaves most KNC loops scalar and blocks if-conversion of conditional FP | from 0 to the full vector gain at `-O2`; if-conversion of conditional FP for free | trivial | compiler | T1: vectorized-loop count over the corpus at `-O2` before/after; one PolyBench run at `-O2` |
| G3 | **`delay` in every spin-wait** (libgomp barriers and locks, `GOMP_SPINCOUNT` tuned), then futex | Round-robin issue: a spinning sibling is always ready and takes issue slots from the working sibling, so an imbalanced region's last thread runs at 1/2 to 1/4 speed exactly when the team waits for it | 10-30% on barrier-heavy programs; 0 on balanced kernels | small (E6-03 addition; E2-04 names `delay`) | runtime | one core: worker alone vs worker plus 1-3 spinning siblings, with and without `delay` |
| G4 | **2 MB pages for data** (hugetlbfs/`MAP_HUGETLB` exists in 2.6.38; THP later in PhiNix); libgfortran `ALLOCATE` and `malloc` of large arrays fall back to huge pages | dTLB: 64 x 4 KB (256 KB) vs 8 x 2 MB (16 MB). WRF's ~29 streams x 4 threads touch 116 pages at once, above 64 entries; with 2 threads, 58. This may be why WRF was best at 2 threads per core | 1.2-2x on many-stream loops at 4 threads; nothing on code (iTLB has 4 KB entries only) | medium; needs a card kernel with hugetlbfs | PhiNix (kernel), GCC-KNC runtime (allocator) | C4 repeated on hugetlbfs; a 29-stream kernel at 2 vs 4 threads, 4 KB vs 2 MB |
| G5 | **Scalar FP path**: raise E5-04 (scalar in zmm lane 0, compare and branch through a mask and `kortest` instead of `fcom`/`fnstsw`/`sahf`), and a **scalar libm on lane 0** (glibc 2.21 k1om libm is generic C over x87) | x87 mul is 1 per 2 cycles per core, divide 38 unpipelined **[card]**; zmm lane 0 is 1 per cycle. The moonshot (a Linux built with GCC-KNC) is scalar code | 2-4x on scalar-FP-bound code; 2.5-4.7% of WRF is libm | medium (E5-04 exists; libm is new) | compiler, runtime | `expf` call rate, glibc vs lane-0; E5-04's own kernels |
| G6 | **Denormal policy ADR**: the VPU flushes (at least SP) denormals, x87 does not; ADR-0003's "IEEE by default" is not true of vector code today. Decide, document, offer `-mknc-ieee-denormals` (no FP vectorization) as the opt-out | Silent semantic divergence between scalar and vector code and against the x87 baseline (WRF saw it) | trust, not speed | small (ADR amendment, one T3) | compiler | none; a T3 that pins the behaviour |
| G7 | **OpenMP codegen**: `declare simd` clones for KNC (*verify* the simd-clone hooks have a KNC entry; ABI ADR for the mangling); static-schedule chunks rounded to the vector length so each thread's sub-loop starts aligned and needs no peel | Without clones, user functions in `omp simd` loops block vectorization; per-thread peel and tail at 7-9-cell rows is pure overhead | medium for C/C++ codes with elemental functions; small for chunking | medium | compiler | T1: a `declare simd` function gets a 16-lane clone; card on a parallel-for with and without rounding |
| G8 | **LTO and IPA verified for k1om** (`lto-plugin` with ld 2.22, `-fipa-cp` of bounds and strides into callees) | An in-order core cannot schedule across calls; known trip counts and strides remove peels, tails and stride versioning. Distros build with LTO | 0-10% on multi-TU programs; a correctness risk if untested | small to verify | compiler | one corpus program with and without `-flto` |
| G9 | **Many-stream address pressure**: IVOPTS address costs for MVEX `disp8*64` (1-byte offsets only at multiples of 64 within +/-8 KB) and 16 GPRs; pointer spills past ~12 streams | WRF loops have ~29 arrays per point; spilled pointers reload on the address path (AGI, 3 cycles) | 5-15% on 20+-stream loops | medium | compiler | T1 spill count on a 29-stream kernel; card at 4 threads vs a 12-stream variant |
| G10 | **Eviction hints** (`{eh}` on loads, `clevict0/1`) for single-use streams in mixed-reuse loops | 512 KB L2 and no L3: streamed arrays evict the reused stencil planes | 5-15% on mixed-reuse loops | medium (temporal classification in the vectorizer) | compiler | hand-written stencil with 8 streamed arrays, `{eh}` on and off |
| G11 | **Gather prefetch** (`vgatherpf0/1dps`) for indirect access | 357-cycle memory latency **[card]** and no prefetcher for indirect streams; SpMV-type loops are latency-bound | 1.3-2x on sparse kernels only | medium; after HPCG lands | compiler | SpMV with hand-inserted gather prefetch |
| G12 | **`_Float16` storage, FP32 compute** (float16 up/down conversions exist for loads and stores) | At 60 cores the card is bandwidth-bound (~175 GB/s); half the bytes is the only lever left there | up to 1.6-1.9x on bandwidth-bound C/C++ loops; nothing for Fortran | medium (`_Float16` scalar and vector support) | compiler for support, application for use | triad with half storage at 60x4 |
| G13 | **Cache-set conflicts**: warn on static arrays whose leading dimension is a multiple of 4 KB (L1 way) or 64 KB (L2 way); padding advice | 8-way L1 against 29 same-stride arrays thrashes; "Kunit" bank conflicts cost 2 clocks | 2-10x on pathological strides, 0 otherwise | small (diagnostic) | compiler (warning), application (padding) | stencil with leading dimension 1024 vs 1040 |
| G14 | **Code locality for the iTLB** (128 KB reach, 4 KB entries only): hot/cold partitioning and PGO function ordering (E7-08) | Large Fortran binaries miss the iTLB on every physics call chain; huge pages cannot help code | low-medium, unmeasured | small once E7-08 exists | compiler | hard to isolate; defer |
| G15 | **Application levers** to document on the flags page: tile widths a multiple of 16 in `i`; fewer, larger OpenMP regions (9,850 x 17 us = 0.17 s of fork per step); fixed static binding so a core's slab stays in its L2 across regions | Lane use 46% and fork plus barrier cost are the two largest measured losses, and neither is a compiler item | up to 2x on hot loops, large on fork cost | documentation only | application | WRF-shaped kernel with rows of 16 vs 8 |
| G16 | *Verify* **pre-RA scheduling with register pressure** (`-fschedule-insns -fsched-pressure`) is on for KNC; x86 defaults it off | Latency hiding at 1-2 threads per core comes from sched1 interleaving (sources note (b)) | 0-20% at 1-2 threads; 0 at 4 | trivial to check | compiler | C9 at 1 and 2 threads with and without |

## 3. Drop or deprioritize

- **Outer-loop vectorization:** with `i`-contiguous data every lane is a different line; a 16-line gather costs 127 cycles per core **[card]**. Only pays after a layout change the application owns.
- **Mask-register rematerialization:** the spill path (`kmov` to a GPR, scalar store) runs on the scalar pipe, which pairs free next to a saturated U pipe. Recomputing a compare costs a U slot. Keep LRA's default.
- **AoS-to-SoA and structure splitting in the compiler:** no mainline pass, needs LTO and escape analysis, and Fortran data is already SoA. Report "gather from struct stride" in E5-03 instead.
- **Compiler-directed thread density (multiversioning by density):** the one density-dependent choice, accumulator count, is settled at 2 (C7 pending). A runtime default and reporting at 2 and 4 is enough.
- **Streaming stores (E5-08):** PRACE saw no STREAM gain at full card; run C1 once, expect little, do not build the fence machinery unless C1 is clear.
- **Virtual L3 and hash-aware placement (Track H):** measure C11, but plain blocking inside 256 KB per core will usually win, as the owner already noted.
- **Power and thermal:** fixed 1238 MHz, no turbo, 164-172 W at full vector load **[card]**; no speed lever. Idle policy (G3, PhiNix `hlt`) is the only item.
- **Graphite tiling, SMS, `vaddsetsps`, the 233 forms:** agree with the backlog; parked.

## 4. Recommended order

1. Card checks C1-C7 as planned, adding G3's spin test and G1's T1 count (no card needed).
2. **Sprint 8 tuning block:** G1 memory-operand folding (exact, cheap), G2 `-O2` defaults, E4-04 tails, E5-07 prefetch, E5-11 and the small-matrix rejection, G16 and E5-12 (both cheap checks), E5-14.
3. **Sprint 9 with the runtimes:** G3 `delay` spin-wait inside E6-03, G6 denormal ADR, G8 LTO verification, G7 `declare simd` and chunk rounding, G5 scalar path (E5-04 raised; scalar libm after E7-01's ABI).
4. **With PhiNix:** G4 huge pages (the only OS item with a plausible 2x on real loops), G15 on the flags page.
5. **M4 and after:** G9, G10, G11 (after HPCG), G12, G13, G14.
