# KNC machine characterization (S6-03 corpus, measured 2026-11-06)

Input for S6-05 (costs and the vectorizer cost model) and S6-06 (scheduler v0). Measured by the lead
with `.work/_shared/S6-03/knc-char.mic` on one core (core 0's siblings) at 1, 2 and 4 threads, in
`--benchmark` windows (`.work/_shared/tmp/claude-s6-slot5/char-1x{1,2,4}.out`, card_run jobs
`claude-0380b2ec…`, `claude-7191652b…`, `claude-b1f534af…`). ADR-0010 method: five groups,
median of medians, accepted when the group spread is under 2%; `*` marks a row with a worker over 2%
(5 of 312 measurements).

**Units.** Cycles are TSC ticks per operation **per thread** (TSC about 1232 MHz; core clock 1238 MHz,
governor `performance`, so ticks and core cycles agree within 0.5%). `.lat` runs a dependent chain;
`.rt` runs independent operations (reciprocal throughput). The last column divides the 4-thread
figure by 4: the core's cost per operation when all four threads issue.

## What the tables say

1. **Vector issue.** One thread issues at most every other cycle: 2.08 per vector op at one thread.
   Two threads already reach the core's limit of **one vector op per cycle** (2.07 per thread); four
   threads stay at one per cycle (4.19 per thread). Vector latency is **4** (add, mul, FMA, integer,
   logic, int/float conversions), **6** for permutes, swizzles and `vrcp23ps`, **7** for double to
   int conversions. At 4 threads the latency is hidden (4.19 per thread, the same as throughput).
2. **Pairing.** A vector op pairs with a scalar op (2.08 per pair at one thread, 4.20 at four);
   two vector ops never pair (4.09 and 8.20). Scalar integer and mask ops pair with each other
   (1.07 per op at one thread): latency 2, two per cycle per core.
3. **Memory-operand forms** (masked load and store, convert up and down, spill-reload): latency
   **12** (13 at four threads), throughput as a plain vector op. `unpack` (the `vloadunpackld/hd`
   pair) costs twice that: 4.09 per pair at one thread, 8.14 at four.
4. **Spills.** A spill-reload pair costs 5.09 at one thread and 4.26 per thread at four (about one
   cycle per core): cheap in throughput, expensive (12-13) on a dependency chain.
5. **Gathers.** All 16 lanes in one line: 15 latency, 7 per gather at one thread (28 at four: 7 per
   core). Lanes on 16 lines: about 175-184 at one thread and **127 per core** at four, so a scattered
   gather costs about as much as 16 scalar L1 misses; the cost model must not treat it as one op.
6. **x87.** Add: latency 3, one per cycle per core. Mul: latency 3, but **one per 2 cycles per core**
   (4.02 per thread at two threads). Divide: 38-39 cycles, **not pipelined** (151.8 per thread at four
   threads: one divide per 38 cycles per core).
7. **Address generation interlock.** A load whose address register was just written costs 3.1
   cycles at one thread instead of 2.1; each instruction placed between the write and the load adds
   one issue slot (gap 1-4: 4.15, 6.16, 8.18, 10.19), so the penalty is about one cycle and is gone
   once one other instruction separates them. At four threads the interlock is hidden (4.26 vs 4.19).
8. **Caches and memory.** Load latency: L1 3, L2 24-26, memory about 357-366. Memory load
   throughput per thread: 37 cycles per line at one thread, 78 at four (19.5 per line per core,
   about 4 GB/s per core at one core).
9. **Streaming stores are slower here** (measured with `vmovnraps` only; per the ISA manual the
   throughput form is the weakly ordered `vmovnrngoaps`, untested: check C1 in
   `docs/research/knc-optimization-sources.md`). On one core, streaming stores cost 157-160 cycles per line
   at every density, against 38 (one thread) to 80 (four threads, 20 per line per core) for normal
   stores; L1- and L2-sized streaming stores cost 27-36 against 2-25. Do not use them by default;
   E5-08 must measure them at 60 cores, where bandwidth rather than latency may decide.

## For S6-05 and S6-06

- Costs (S6-05): vector op 1 per core-cycle, latency 4/6/7 as above; memory-operand latency 12;
  unaligned load pair 2 ops; spill about 1 op; gather by lines touched (about 7 per core per line,
  127 for 16 lines); x87 add 1, mul 2, divide 38 per core; L2 miss 24, memory miss about 360.
- Scheduler (S6-06): pair each vector op with a scalar or mask op; never expect two vector ops in
  one cycle; separate an address computation from its load by at least one instruction; at the
  production density of 4 threads, latencies of 4 to 7 are mostly hidden, so issue order and pairing
  matter more than latency.
- M2 baseline for red-test design: `docs/research/card-runs-s6.md` (launches 2-3 tables; the final
  three-launch baseline follows the placement test).

## Full table

| Test | 1 thread | 2 threads | 4 threads | Per core at 4 threads |
|---|---:|---:|---:|---:|
| `vaddps.lat` | 4.02 | 4.08 | 4.19 | 1.05 |
| `vaddps.rt` | 2.08 | 2.07 | 4.18 | 1.05 |
| `vmulps.lat` | 4.03 | 4.08 | 4.20 | 1.05 |
| `vmulps.rt` | 2.08 | 2.07 | 4.19 | 1.05 |
| `vfmadd213ps.lat` | 4.02 | 4.08 | 4.20 | 1.05 |
| `vfmadd213ps.rt` | 2.08 | 2.07 | 4.20 | 1.05 |
| `vpaddd.lat` | 4.03 | 4.08 | 4.20 | 1.05 |
| `vpaddd.rt` | 2.08 | 2.32 * | 4.19 | 1.05 |
| `vpxord.lat` | 4.03 | 4.08 | 4.21 | 1.05 |
| `vpxord.rt` | 2.07 | 2.07 | 4.19 | 1.05 |
| `vpermd.lat` | 6.04 | 6.09 | 6.16 | 1.54 |
| `vpermd.rt` | 2.08 | 2.07 | 4.19 | 1.05 |
| `vpermf32x4.lat` | 6.04 | 6.09 | 6.16 | 1.54 |
| `vpermf32x4.rt` | 2.08 | 2.07 | 4.20 | 1.05 |
| `vrcp23ps.lat` | 6.04 | 6.09 | 6.16 | 1.54 |
| `vrcp23ps.rt` | 2.08 | 2.07 | 4.20 | 1.05 |
| `scalar_add.lat` | 2.08 | 2.07 | 4.19 | 1.05 |
| `scalar_add.rt` | 1.07 | 1.07 | 2.19 | 0.55 |
| `scalar_xor.lat` | 2.08 | 2.07 | 4.20 | 1.05 |
| `scalar_xor.rt` | 1.07 | 1.07 | 2.18 | 0.54 |
| `kmov.lat` | 2.08 | 2.07 | 4.19 | 1.05 |
| `kmov.rt` | 1.07 | 1.07 | 2.19 | 0.55 |
| `kand.lat` | 2.08 | 2.07 | 4.20 | 1.05 |
| `kand.rt` | 1.07 | 1.07 | 2.19 | 0.55 |
| `kxor.lat` | 2.08 | 2.07 | 4.19 | 1.05 |
| `kxor.rt` | 1.07 | 1.07 | 2.18 | 0.55 |
| `swizzle_cdab.lat` | 6.04 | 6.09 | 6.16 | 1.54 |
| `swizzle_cdab.rt` | 2.08 | 2.07 | 4.19 | 1.05 |
| `swizzle_badc.lat` | 6.04 | 6.09 | 6.16 | 1.54 |
| `swizzle_badc.rt` | 2.07 | 2.07 | 4.19 | 1.05 |
| `swizzle_dacb.lat` | 6.04 | 6.09 | 6.16 | 1.54 |
| `swizzle_dacb.rt` | 2.07 | 2.07 | 4.19 | 1.05 |
| `swizzle_aaaa.lat` | 6.04 | 6.09 | 6.16 | 1.54 |
| `swizzle_aaaa.rt` | 2.08 | 2.07 | 4.19 | 1.05 |
| `swizzle_bbbb.lat` | 6.04 | 6.09 | 6.16 | 1.54 |
| `swizzle_bbbb.rt` | 2.08 | 2.07 | 4.20 | 1.05 |
| `swizzle_cccc.lat` | 6.04 | 6.09 | 6.16 | 1.54 |
| `swizzle_cccc.rt` | 2.08 | 2.07 | 4.19 | 1.05 |
| `swizzle_dddd.lat` | 6.04 | 6.09 | 6.16 | 1.54 |
| `swizzle_dddd.rt` | 2.08 | 2.07 | 4.20 | 1.05 |
| `vaddpd.lat` | 4.03 | 4.08 | 4.20 | 1.05 |
| `vaddpd.rt` | 2.08 | 2.07 | 4.19 | 1.05 |
| `vmulpd.lat` | 4.03 | 4.08 | 4.20 | 1.05 |
| `vmulpd.rt` | 2.08 | 2.07 | 4.19 | 1.05 |
| `vfmadd213pd.lat` | 4.03 | 4.08 | 4.20 | 1.05 |
| `vfmadd213pd.rt` | 2.08 | 2.08 | 4.19 | 1.05 |
| `vcvtfxpntdq2ps.lat` | 4.03 | 4.08 | 4.20 | 1.05 |
| `vcvtfxpntdq2ps.rt` | 2.08 | 2.07 | 4.20 | 1.05 |
| `vcvtfxpntudq2ps.lat` | 4.03 * | 4.08 | 4.21 | 1.05 |
| `vcvtfxpntudq2ps.rt` | 2.08 | 2.07 | 4.20 | 1.05 |
| `vcvtfxpntps2dq.lat` | 4.03 | 4.08 | 4.20 | 1.05 |
| `vcvtfxpntps2dq.rt` | 2.08 | 2.07 | 4.20 | 1.05 |
| `vcvtfxpntps2udq.lat` | 4.03 | 4.08 | 4.20 | 1.05 |
| `vcvtfxpntps2udq.rt` | 2.08 | 2.07 | 4.20 | 1.05 |
| `vcvtfxpntpd2dq.lat` | 7.04 | 7.11 | 7.18 | 1.79 |
| `vcvtfxpntpd2dq.rt` | 2.08 | 2.07 | 4.20 | 1.05 |
| `vcvtfxpntpd2udq.lat` | 7.05 | 7.11 | 7.18 | 1.79 |
| `vcvtfxpntpd2udq.rt` | 2.08 | 2.07 | 4.20 | 1.05 |
| `x87_add.lat` | 3.02 | 3.08 | 4.13 | 1.03 |
| `x87_add.rt` | 2.08 | 2.07 | 4.13 | 1.03 |
| `x87_mul.lat` | 3.02 | 4.08 | 8.02 | 2.00 |
| `x87_mul.rt` | 2.08 | 4.02 | 8.02 | 2.00 |
| `x87_div.lat` | 39.25 | 76.30 | 151.79 | 37.95 |
| `x87_div.rt` | 38.24 | 76.27 | 151.76 | 37.94 |
| `masked_load.lat` | 12.11 | 12.17 | 13.14 | 3.28 |
| `masked_store.lat` | 12.11 | 12.17 | 13.17 | 3.29 |
| `unpack.lat` | 12.11 | 16.79 * | 24.40 | 6.10 |
| `convert_up.lat` | 12.11 | 12.18 * | 13.18 | 3.30 |
| `convert_down.lat` | 12.11 | 12.95 | 13.14 | 3.29 |
| `spill_reload.lat` | 12.11 | 12.98 | 13.14 | 3.29 |
| `masked_load.rt` | 2.08 | 2.37 | 4.13 | 1.03 |
| `masked_store.rt` | 2.08 | 2.08 * | 4.13 | 1.03 |
| `unpack.rt` | 4.09 | 4.08 | 8.14 | 2.04 |
| `convert_up.rt` | 2.08 | 2.07 | 4.13 | 1.03 |
| `convert_down.rt` | 2.08 | 2.07 | 4.13 | 1.03 |
| `spill_reload.rt` | 5.09 | 4.20 | 4.26 | 1.07 |
| `masked_load_sparse.lat` | 12.11 | 12.17 | 13.15 | 3.29 |
| `masked_store_sparse.lat` | 12.11 | 12.18 | 13.14 | 3.29 |
| `masked_load_sparse.rt` | 2.08 | 2.07 | 4.13 | 1.03 |
| `masked_store_sparse.rt` | 2.08 | 2.07 | 4.13 | 1.03 |
| `gather_all.lat` | 15.10 | 18.27 | 29.17 | 7.29 |
| `gather_all.rt` | 7.08 | 14.09 | 28.10 | 7.02 |
| `gather_scattered.lat` | 183.58 | 275.10 | 509.15 | 127.29 |
| `gather_scattered.rt` | 175.14 | 259.58 | 506.78 | 126.70 |
| `pair.vector_scalar` | 2.08 | 2.10 | 4.20 | 1.05 |
| `pair.vector_vector` | 4.09 | 4.08 | 8.20 | 2.05 |
| `pair.scalar_scalar` | 2.08 | 2.07 | 4.19 | 1.05 |
| `agi.gap0` | 3.11 | 3.17 | 4.26 | 1.06 |
| `agi.gap1` | 4.15 | 4.15 | 8.27 | 2.07 |
| `agi.gap2` | 6.16 | 6.16 | 12.27 | 3.07 |
| `agi.gap3` | 8.18 | 8.16 | 16.28 | 4.07 |
| `agi.gap4` | 10.19 | 10.18 | 20.29 | 5.07 |
| `l1.load_lat` | 3.03 | 3.08 | 4.13 | 1.03 |
| `l1.load_rt` | 2.20 | 2.27 | 4.38 | 1.10 |
| `l1.store_normal` | 2.20 | 2.27 | 4.38 | 1.10 |
| `l1.store_stream` | 27.19 | 30.09 | 36.16 | 9.04 |
| `l2.load_lat` | 24.42 | 24.93 | 25.68 | 6.42 |
| `l2.load_rt` | 23.38 | 23.51 | 23.85 | 5.96 |
| `l2.store_normal` | 23.39 | 23.66 | 25.04 | 6.26 |
| `l2.store_stream` | 27.49 | 30.22 | 36.29 | 9.07 |
| `memory.load_lat` | 356.53 | 357.96 | 365.76 | 91.44 |
| `memory.load_rt` | 37.35 | 47.78 | 77.92 | 19.48 |
| `memory.store_normal` | 38.28 | 48.93 | 79.83 | 19.96 |
| `memory.store_stream` | 157.12 | 158.07 | 160.26 | 40.07 |

## Sprint 8 tuning checks (S8-01, card 2026-11-07/08)

Binary `.work/_shared/S8-01/knc-char.mic` (`s8/S8-01` at 3f5ccb2), one core (core 0's siblings) unless
noted. Raw output: `.work/_shared/tmp/claude-s8-01/job1.out` to `job19.out`; job N is the Nth
`card_run` line of the README job list, job 18 is an extra `vaddps.lat` check and job 19 reruns job 3.
Figures are TSC ticks per unit **per thread** (median of five group medians, ADR-0010); `(x%)` is
the group spread; `*` marks a regime-step flag (spread 2% or more, amendment 2).

**Validity.** Every job: same boot, no overlapping job, no foreign process (only card_run's own
`sleep`), clock policy identical at start and end.
- Jobs 1, 2, 4-8, 10-18: exit 0, every point accepted.
- Job 9 (C5, 2 threads): exit 3. `c5.row8.l1_0.l2_32` and `c5.row9.l1_0.l2_32` have median batches
  of 212 and 233 ms (over 200 ms), so they are **invalid** under amendment 2 point 1. The other C5
  row points at 2 threads are bimodal: samples in one point differ up to 6x (median point 1.9x),
  so treat them as noisy.
- Jobs 3 and 19 (C1 at 60 cores x 4 threads): exit 2, ENOMEM; glibc 2.21 gave each worker its own
  64 MB malloc arena. After the fix (main allocates every buffer before the workers start), the lead
  reran job 19 on 2026-11-08 (job claude-3827228ac5c7, 6 GB config): exit 0, 240 workers, every
  point accepted, spread 0.4-1.3%, no regime step (.work/_shared/tmp/claude-s8-01/job19r.out).
- Job 18: `vaddps.lat` at 4 threads gives 4.22 against S6-03's 4.19, so the S8 binary agrees with
  the S6-03 table.
- Each line ran **once**, not the README's five launches. The cross-launch range is not measured.

### C1: write-only memory-sized stores, one core (16 MiB per core, ticks per 64-byte line)

| Store | 1 thread | 4 threads | Per core at 4 | GB/s, 1 thr | GB/s, 4 thr |
|---|---:|---:|---:|---:|---:|
| `vmovaps` | 37.94 (0.3%) | 79.58 (0.1%) | 19.9 | 2.1 | 4.0 |
| `vmovnraps` | 156.41 (0.1%) | 160.14 (0.3%) | 40.0 | 0.5 | 2.0 |
| `vmovnrngoaps` | 12.43 (0.2%) | 50.00 (0.3%) | 12.5 | 6.3 | 6.3 |

At 60 cores x 4 threads (4 MiB per thread, all workers start each sample on one barrier; ticks per
line per thread, median of 240 workers with the slowest in brackets; card GB/s from the median, slowest
worker's figure in brackets):

| Store | Ticks per line, per thread | Card GB/s |
|---|---:|---:|
| `vmovaps` | 227.7 (230.9) | 83.5 (82.4) |
| `vmovnraps` | 166.6 (171.6) | 114.1 (110.8) |
| `vmovnrngoaps` | 84.1 (93.0) | 226.1 (204.5) |

Decides (E5-08): NGO stores plus the `lock addl` fence beat normal stores 3.1x at 1 thread and 1.6x
at 4 threads on one core, and 2.7x on the whole card, so NGO is the default for write-only streams.
NR stores lose 2-4x on one core but beat normal stores 1.4x on the whole card, where the read for
ownership dominates; NGO still beats NR 2x there, so NR is never chosen. One launch only.

### C2: does `vprefetch` pair with a vector op (hot targets, ticks per instruction or pair)

| Unit | 1 thread | 2 threads | 4 threads |
|---|---:|---:|---:|
| vector op | 2.08 (0.1%) | 2.07 (0.1%) | 4.19 (0.7%) |
| `vprefetch0` | 1.07 (0.2%) | 1.09 (0.8%) | 2.13 (0.1%) |
| `vprefetch1` | 1.92 (1.7%) | 4.52 (0.0%) | 9.01 (0.0%) |
| vector + `vprefetch0` | 2.08 (0.0%) | 2.20 (0.2%) | 4.13 (0.1%) |
| vector + `vprefetch1` | 2.09 (0.1%) | 4.52 (0.1%) | 9.02 (0.1%) |

Decides (E5-07 cost model): `vprefetch0` pairs with a vector op and costs nothing extra;
`vprefetch1` is limited to about one per 2.25 core cycles per core at 2-4 threads, and a vector op
hides under it. Cost a `vprefetch1` at about 2 core cycles and issue it once per line. Targets were
L1-resident, so the cost of a prefetch that misses is not measured.

### C4: page-stride dependent loads (one load per 4 KiB page, ticks per load)

| KiB per core | Pages per thread, 1 / 4 thr | 1 thread | 4 threads |
|---:|---|---:|---:|
| 128 | 32 / 8 | 24.11 (0.1%) | 4.13 (0.1%) |
| 256 | 64 / 16 | 24.16 (0.1%) | 25.66 (0.3%) |
| 384 | 96 / 24 | 24.17 (0.1%) | 25.66 (0.2%) |
| 448 | 112 / 28 | 24.18 (0.0%) | 25.66 (0.0%) |

Every load sits at the same page offset, so all lines of a thread fall in one 8-way L1 set. Loads
therefore hit L2 (24-26, as `l2.load_lat`), except at 128 KiB and 4 threads, where 8 lines per
thread fit the set and hit L1 (4.13, as `l1.load_lat`).
S8-01's decision here (no TLB knee) was wrong: the layout put every line in one L1 set. **S8-12 rerun
(2026-11-08, lines at page offset 64*(5i mod 64), every L1 set used; one launch each,
`.work/_shared/tmp/claude-s8-12/job{1,2}-c4-*.out`):**

| KiB per core | Pages per core | 1 thread | 4 threads |
|---:|---:|---:|---:|
| 128 | 32 | 3.01 (0.0%) | 4.13 (0.0%) |
| 256 | 64 | 3.02 (0.2%) | 4.13 (0.0%) |
| 384 | 96 | 31.76 (0.0%) | 11.75 (0.2%) |
| 448 | 112 | 31.79 (0.0%) | 13.68 (0.1%) |

Every line now stays in L1, so the jump is the TLB: up to 64 4-KiB pages per core the loads cost L1
latency; above it each load misses the 64-entry first-level DTLB and costs about 29 ticks more at one
thread (31.8 against 3.0; at 4 threads the siblings hide part of it, 11.8-13.7 against 4.1).
Decides (I-2, E5-07 and blocking): with 4 KiB pages, a tile should touch at most 64 pages per core
(256 KiB, shared by its threads); larger tiles pay about 29 ticks per first touch of each page beyond that.
The 256 KB TLB-limited tile is supported; 2 MB pages remove the limit.

### C5: software prefetch distance sweep (ticks per 64-byte row iteration; rows L1 distance, columns L2 distance, in iterations)

2 threads per core:

| Kernel, L1 | L2 0 | L2 32 | L2 64 | L2 128 |
|---|---:|---:|---:|---:|
| stream, 0 | 97.8 | 85.0 | 83.6 | 86.4 |
| stream, 8 | 167.2 | 63.2 | 63.1 | 63.3 |
| stream, 16 | 167.6 | **62.1** | 64.0 | 63.1 |
| stream, 32 | 167.7 | 207.7 | 62.7 | 64.0 |
| stream, 64 | 167.9 | 175.0 | 218.0 | 65.2 |
| stencil, 0 | 100.4 | 84.7 | 88.3 | 88.6 |
| stencil, 8 | 168.4 | 63.9 | 64.2 | 64.4 |
| stencil, 16 | 167.8 | **63.3** | 65.4 | 65.1 |
| stencil, 32 | 168.2 | 217.4 | 65.6 | 66.7 |
| stencil, 64 | 169.2 | 177.4 | 227.0 | 76.5 |
| row7, 0 | **601.5*** | 1933.6 | 1426.9 | 1016.3* |
| row7, 8 | 1205.9* | 1659.5* | 1368.9* | 1065.6* |
| row7, 16 | 1323.4* | 2448.6 | 2436.7 | 2427.5 |
| row7, 32 | 2064.2 | 2283.0 | 2175.0 | 2194.5 |
| row7, 64 | 1482.8 | 2174.9 | 1709.2* | 1550.8 |
| row8, 0 | 621.2 | invalid | 1395.3 | 1065.8* |
| row8, 8 | 849.1* | **558.7*** | 1401.3 | 1016.8* |
| row8, 16 | 1608.3* | 2447.2 | 2453.9 | 2410.8 |
| row8, 32 | 2063.8 | 2276.6 | 2217.1 | 2180.6 |
| row8, 64 | 1476.0 | 2222.6 | 1746.0 | 1499.9 |
| row9, 0 | **617.0** | invalid | 1390.4 | 1034.3 |
| row9, 8 | 780.7 | 1475.7* | 1531.1* | 967.3* |
| row9, 16 | 1402.5* | 2454.1 | 2452.5 | 2418.1 |
| row9, 32 | 2063.6 | 2272.7 | 2182.2 | 2176.8 |
| row9, 64 | 1568.0* | 2200.4 | 1689.5* | 1502.7 |

4 threads per core:

| Kernel, L1 | L2 0 | L2 32 | L2 64 | L2 128 |
|---|---:|---:|---:|---:|
| stream, 0 | 162.2 | 129.7 | 128.1 | 132.1 |
| stream, 8 | 338.6 | 125.2 | 125.8 | 127.8 |
| stream, 16 | 339.6 | **123.4** | 125.7 | 126.1 |
| stream, 32 | 343.9 | 388.6 | 124.4 | 126.3 |
| stream, 64 | 368.3 | 370.5 | 411.4 | 133.4 |
| stencil, 0 | 161.4 | 131.6 | 132.1 | 132.8 |
| stencil, 8 | 338.8 | 127.0 | 128.5 | 129.3 |
| stencil, 16 | 340.6 | **126.2** | 126.8 | 130.1 |
| stencil, 32 | 345.7 | 396.3 | 126.9 | 129.5 |
| stencil, 64 | 367.9 | 374.2 | 420.1 | 137.9 |
| row7, 0 | **2461.2** | 2902.4 | 2993.4 | 2896.0 |
| row7, 8 | 2584.2* | 2842.4* | 2765.4* | 2560.8* |
| row7, 16 | 3183.0* | 3334.0 | 3490.7 | 3406.9* |
| row7, 32 | 3438.4 | 3573.0 | 3512.4 | 3525.7 |
| row7, 64 | 3622.2 | 3674.1 | 3609.2 | 3696.8 |
| row8, 0 | **2457.7** | 2927.0 | 2993.1 | 2906.7 |
| row8, 8 | 2590.7* | 2811.7* | 2775.6* | 2552.7* |
| row8, 16 | 3121.6* | 3341.8 | 3453.8* | 3421.1* |
| row8, 32 | 3437.5 | 3537.8 | 3555.8 | 3539.3 |
| row8, 64 | 3639.3 | 3670.0 | 3615.5 | 3693.0 |
| row9, 0 | **2464.0** | 2910.4 | 2990.5 | 2903.0 |
| row9, 8 | 2591.9 | 2826.4* | 2765.6* | 2632.2* |
| row9, 16 | 3188.2* | 3367.6 | 3450.8 | 3422.2* |
| row9, 32 | 3424.9 | 3569.7 | 3523.7 | 3541.2 |
| row9, 64 | 3593.8 | 3674.9 | 3605.7 | 3694.1 |

Stream and stencil spreads are all under 2%. Row points: 21 flagged at 2 threads (up to 36%, row7
8/32) and 18 at 4 threads (up to 5.8%).
Rows cost twice as much per core at 4 threads as at 2 (615 against 305 ticks per row): 8 streams
per thread overflow the 16-stream hardware prefetcher at 4 threads (I-3). The 8 row arrays are
1 MiB apart, so a row's 8 lines share one 8-way L1 set; the row results are an aliased worst case.
Decides (E5-07): for stream and stencil, best L1/L2 = 16/32 at both 2 and 4 threads (about 1.6x
and 1.3x over no prefetch); ICC's 32/64 is within 4% of best; L2 distance must exceed L1, and L1
prefetch without L2 prefetch is 1.7-2.3x slower than none. For 8-stream short rows, no software
prefetch was best at the swept distances (one flagged exception); rerun rows with padded arrays
before setting the many-stream rule.

### C6: loop tails for `y = x + 1`, lengths 1-33 (ticks per call)

x87 is linear: 7.05 ticks per element at 1 thread, 16.03 at 4 threads. The other strategies are
constant within 1-15 and 17-31. Peel starts one float off alignment, so it runs 15 scalar
elements before any vector (the worst case).

| n | x87, 1 thr | aligned | peel | gather | x87, 4 thr | aligned | peel | gather |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **7.1** | 13.2 | 7.1 | 19.2 | **16.2** | 24.8 | 16.2 | 49.8 |
| 2 | 14.2 | **13.2** | 14.2 | 19.2 | 32.2 | **24.7** | 32.2 | 49.7 |
| 3 | 21.2 | **13.2** | 21.2 | 19.2 | 48.2 | **24.8** | 48.2 | 49.7 |
| 4 | 28.2 | **13.2** | 28.2 | 19.2 | 64.3 | **24.8** | 64.2 | 49.8 |
| 5-15 | 35-106 | **13.2** | 35-106 | 19.2 | 80-241 | **24.7** | 80-241 | 49.8 |
| 16 | 112.8 | **13.2** | 120.8 | **13.2** | 256.6 | **24.7** | 270.7 | **24.6** |
| 17-31 | 120-219 | **26.3** | 120.8 | 32.3 | 273-497 | **49.3** | 270.8 | 74.7 |
| 32 | 225.2 | **26.3** | 133.9 | **26.3** | 513.2 | 49.3 | 296.1 | **49.0** |
| 33 | 232.6 | **39.3** | 133.9 | 45.4 | 529.2 | **73.7** | 296.1 | 99.2 |

All spreads under 2% except `c6.aligned.n6` at 4 threads (2.4%).
Decides (E4-04, E5-11): an aligned masked tail beats x87 from n = 2 at 1 and 4 threads; a gather
tail beats x87 from n = 3 at 1 thread and n = 4 at 4 threads, and costs 6 ticks (1 thread) to 25
ticks (4 threads, 2x) more than an aligned masked vector; a scalar peel to alignment loses to the
gather tail at every length 1-33. Order: aligned masked tail, then gather tail; scalar only at n = 1.
A masked vector peel was not measured.

### C7: reduction with 1 or 2 accumulators, 4 threads per core (ticks per 16-lane update)

| Accumulators | 4 threads |
|---|---:|
| 1 | 4.13 (0.2%) |
| 2 | 4.13 (0.0%) |

Decides (I-11, chain choice in `knc-costs.md`): 2 accumulators lose nothing at 4 threads, so 2 can
be the default at every density. The gain at 2 threads is not measured here.

### C9: unroll 1, 2, 4 on a dependent vector add (ticks per update)

| Chain | 1 thread | 2 threads |
|---|---:|---:|
| register, u1 | 4.02 (0.1%) | 4.02 (0.0%) |
| register, u2 | 3.02 (0.0%) | 3.01 (0.0%) |
| register, u4 | 2.52 (0.1%) | 2.51 (0.1%) |
| memory operand, u1 | 4.03 (0.0%) | 4.02 (0.1%) |
| memory operand, u2 | 3.02 (0.1%) | 3.01 (0.0%) |
| memory operand, u4 | 2.52 (0.1%) | 2.51 (0.0%) |

The loop costs about 2 ticks per vector op plus 2 per loop branch, so u2 already covers the
4-cycle latency and u4 only saves branches. The memory-operand chain costs the same as the register
chain: the folded load is off the recurrence, so this is not the 12-cycle chain the check asked for.
Decides (E5-09, SMS): unroll 4 is best at 1 and 2 threads per core (25% then 17% gains); no
latency-bound gap appears, so no case for SMS from C9. A folded load adds no cost (E5-17).

**S8-12 rerun of the memory chain (2026-11-08):** `vaddps 64i(%rsi), %zmm31, %zmmi` then
`vmovaps %zmmi, 64i(%rsi)`, so the load carries the recurrence through the store (ticks per
load-add-store link; one launch each, `.work/_shared/tmp/claude-s8-12/job{3,4}-c9-*.out`):

| Chain | 1 thread | 2 threads |
|---|---:|---:|
| register, u1 / u2 / u4 | 4.02 / 3.02 / 2.52 | 4.57 / 3.02* / 2.51 |
| memory, u1 | 11.07 (0.0%) | 13.08 (1.9%) |
| memory, u2 | 8.56 (0.0%) | 12.03 (1.5%) |
| memory, u4 | 8.30 (0.0%) | 11.01 (1.7%) |

\* flagged, 14.2% spread. A recurrence through memory costs about 11 ticks per link at one thread,
almost three times the register chain, and unrolling recovers only a quarter of it (1 thread) or
less (2 threads). Decides (E5-09, E5-17): keep recurrences in registers (store motion and scalar
replacement matter more than unroll for such loops); unroll does not fix a memory-carried chain.

### C10: branch-mispredict cost (ticks per branch)

| Branch | 1 thread | 4 threads |
|---|---:|---:|
| fixed direction | 6.22 (0.0%) | 17.02 (0.0%) |
| pseudorandom | 11.27 (0.0%) | 27.76 (0.1%) |
| difference | 5.05 | 10.74 (2.7 per core) |

Decides (E7-04): an unpredictable branch costs 5 ticks more at 1 thread, about 10 cycles per
mispredict if half of the random branches miss; at 4 threads it costs 2.7 cycles per core. Set
`BRANCH_COST` from about 10 cycles; a branchless sequence pays when it adds under about 5 ticks per
unpredictable branch.
