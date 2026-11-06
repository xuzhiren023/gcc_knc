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
9. **Streaming stores are slower here.** On one core, streaming stores cost 157-160 cycles per line
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
