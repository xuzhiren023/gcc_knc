# Held-out validation against the characterization microbenchmarks

Generated 2026-11-16T00:26:24Z. Profile card-7120-measured (hash 0292e57ad671...). line_tracking cold memory with the default sub-models: TLB, L2 hardware prefetcher and memory service modeled

## Error statistics (per thread count)

| rows | n | median abs err % | worst abs err % | within 15% | within 30% | mean signed err % |
|---|---:|---:|---:|---:|---:|---:|
| all_held_out_threads_1 | 163 | 2.9 | 45.9 | 150 | 159 | 2.3 |
| all_held_out_threads_2 | 58 | 2.7 | 49.3 | 50 | 52 | 0.7 |
| all_held_out_threads_4 | 57 | 1.4 | 42.5 | 53 | 53 | -1.3 |
| calibration_threads_1 | 57 | 0.7 | 19.0 | 56 | 57 | -0.5 |
| calibration_threads_2 | 55 | 1.4 | 29.3 | 50 | 55 | -3.1 |
| calibration_threads_4 | 54 | 1.2 | 45.8 | 52 | 52 | -1.8 |
| compiled_calibration_threads_1 | 3 | 2.9 | 3.6 | 3 | 3 | 3.1 |
| compiled_held_out_threads_1 | 105 | 3.2 | 17.9 | 96 | 105 | 5.2 |
| held_out_threads_1 | 58 | 0.9 | 45.9 | 54 | 54 | -2.8 |
| held_out_threads_2 | 58 | 2.7 | 49.3 | 50 | 52 | 0.7 |
| held_out_threads_4 | 57 | 1.4 | 42.5 | 53 | 53 | -1.3 |

## Decision bar (held-out compiled code)

| criterion | limit | result | met |
|---|---|---|---|
| median absolute error | at most 10% | 3.2% over 105 rows (worst 17.9%, 89 within 10%) | yes |
| right winner, pairs measured more than 5% apart | at least 90% | 39 of 39 (1.0) | yes |
| held-out compiled loops | at least 50, from the M4 corpus | 105 rows in 4 cases from s12-30, s12-31 | yes |

Verdict: bar met on 105 held-out compiled rows.

## Ranking reliability

367 of 373 measured pairwise orderings (within groups, measured difference > 3%) reproduced: reliability 0.984.

| group | agree | pairs | disagreements (a, b: measured -> predicted) |
|---|---:|---:|---|
| agi_gap@threads_1 | 10 | 10 |  |
| agi_gap@threads_2 | 10 | 10 |  |
| agi_gap@threads_4 | 10 | 10 |  |
| branches@threads_1 | 1 | 1 |  |
| branches@threads_4 | 1 | 1 |  |
| c9_memory_unroll@threads_1 | 3 | 3 |  |
| c9_memory_unroll@threads_2 | 3 | 3 |  |
| c9_register_unroll@threads_1 | 3 | 3 |  |
| c9_register_unroll@threads_2 | 3 | 3 |  |
| gathers@threads_1 | 6 | 6 |  |
| gathers@threads_2 | 6 | 6 |  |
| gathers@threads_4 | 4 | 5 | gather_all.lat vs gather_all.rt: 29.17/28.10 -> 28.00/28.12 |
| latency_rows@threads_1 | 21 | 21 |  |
| latency_rows@threads_2 | 21 | 21 |  |
| latency_rows@threads_4 | 18 | 18 |  |
| load_levels_lat@threads_1 | 3 | 3 |  |
| load_levels_lat@threads_2 | 3 | 3 |  |
| load_levels_lat@threads_4 | 3 | 3 |  |
| load_levels_rt@threads_1 | 3 | 3 |  |
| load_levels_rt@threads_2 | 3 | 3 |  |
| load_levels_rt@threads_4 | 3 | 3 |  |
| memory_forms@threads_1 | 12 | 12 |  |
| memory_forms@threads_2 | 12 | 14 | masked_load.lat vs unpack.lat: 12.17/16.79 -> 12.00/12.00; masked_load.lat vs spill_reload.lat: 12.17/12.98 -> 12.00/12.00 |
| memory_forms@threads_4 | 14 | 14 |  |
| pairing@threads_1 | 2 | 2 |  |
| pairing@threads_2 | 2 | 2 |  |
| pairing@threads_4 | 2 | 2 |  |
| prefetch_pairing@threads_1 | 7 | 7 |  |
| prefetch_pairing@threads_2 | 9 | 9 |  |
| prefetch_pairing@threads_4 | 8 | 8 |  |
| s12-30-small: S12-30 small HPCG-pointers n=13 builds@threads_1 | 2 | 2 |  |
| s12-31-hpcg-104: HPCG 104-cubed SpMV builds@threads_1 | 12 | 12 |  |
| s12-31-hpcg-toy: HPCG toy SpMV builds@threads_1 | 12 | 12 |  |
| s12-31-hpcg-toy: HPCG toy SymGS builds@threads_1 | 12 | 12 |  |
| s12-31-microbench: S12-31 loop-body orders@threads_1 | 8 | 8 |  |
| s12-31-microbench: S12-31 padding styles at 13-15 bytes@threads_1 | 14 | 14 |  |
| stores@threads_1 | 14 | 14 |  |
| stores@threads_2 | 14 | 14 |  |
| stores@threads_4 | 14 | 14 |  |
| throughput_rows@threads_1 | 17 | 17 |  |
| throughput_rows@threads_2 | 21 | 24 | vaddps.rt vs masked_load.rt: 2.07/2.37 -> 2.12/2.12; vpermd.rt vs masked_load.rt: 2.07/2.37 -> 2.12/2.12; masked_load.rt vs x87_add.rt: 2.37/2.07 -> 2.12/2.19 |
| throughput_rows@threads_4 | 21 | 21 |  |

## Rows

| test | class | status | measured 1/2/4 | predicted 1/2/4 | err % 1/2/4 | predicted without HWP 1/2/4 | limiting (1 thread) |
|---|---|---|---|---|---|---|---|
| vaddps.lat | calibration | ok | 4.02/4.08/4.19 | 4.00/4.03/4.25 | -0.5/-1.2/+1.4 |  | miss_stall, dependency |
| vaddps.rt | calibration | ok | 2.08/2.07/4.18 | 2.06/2.12/4.25 | -0.9/+2.7/+1.7 |  | miss_stall, spacing |
| vmulps.lat | calibration | ok | 4.03/4.08/4.20 | 4.00/4.03/4.25 | -0.7/-1.2/+1.2 |  | miss_stall, dependency |
| vmulps.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.12/4.25 | -0.9/+2.7/+1.4 |  | miss_stall, spacing |
| vfmadd213ps.lat | calibration | ok | 4.02/4.08/4.20 | 4.00/4.03/4.25 | -0.5/-1.2/+1.2 |  | miss_stall, dependency |
| vfmadd213ps.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.12/4.25 | -0.9/+2.7/+1.2 |  | miss_stall, spacing |
| vpaddd.lat | calibration | ok | 4.03/4.08/4.20 | 4.00/4.03/4.25 | -0.7/-1.2/+1.2 |  | miss_stall, dependency |
| vpaddd.rt | held_out | ok | 2.08/2.32/4.19 | 2.06/2.12/4.25 | -0.9/-8.4/+1.4 |  | miss_stall, spacing |
| vpxord.lat | calibration | ok | 4.03/4.08/4.21 | 4.00/4.03/4.25 | -0.7/-1.2/+1.0 |  | miss_stall, dependency |
| vpxord.rt | held_out | ok | 2.07/2.07/4.19 | 2.06/2.12/4.25 | -0.4/+2.7/+1.4 |  | miss_stall, spacing |
| vpermd.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.14 | -0.7/-1.5/-0.3 |  | miss_stall, dependency |
| vpermd.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.12/4.25 | -0.9/+2.7/+1.4 |  | miss_stall, spacing |
| vpermf32x4.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.14 | -0.7/-1.5/-0.3 |  | miss_stall, dependency |
| vpermf32x4.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.12/4.25 | -0.9/+2.7/+1.2 |  | miss_stall, spacing |
| vrcp23ps.lat | calibration | unsupported: not functionally complete: timing only: timing only (23-bit approximat | 6.04/6.09/6.16 | -/-/- | -/-/- |  |  |
| vrcp23ps.rt | held_out | unsupported: not functionally complete: timing only: timing only (23-bit approximat | 2.08/2.07/4.20 | -/-/- | -/-/- |  |  |
| scalar_add.lat | calibration | ok | 2.08/2.07/4.19 | 2.06/2.12/4.25 | -0.9/+2.7/+1.4 |  | miss_stall, spacing |
| scalar_add.rt | held_out | ok | 1.07/1.07/2.19 | 1.12/1.19/2.38 | +5.1/+11.0/+8.4 |  | miss_stall, spacing |
| scalar_xor.lat | held_out | ok | 2.08/2.07/4.20 | 2.06/2.12/4.25 | -0.9/+2.7/+1.2 |  | miss_stall, spacing |
| scalar_xor.rt | held_out | ok | 1.07/1.07/2.18 | 1.12/1.19/2.38 | +5.1/+11.0/+8.9 |  | miss_stall, spacing |
| kmov.lat | held_out | ok | 2.08/2.07/4.19 | 2.06/2.12/4.25 | -0.9/+2.7/+1.4 |  | miss_stall, spacing |
| kmov.rt | held_out | ok | 1.07/1.07/2.19 | 1.12/1.19/2.38 | +5.1/+11.0/+8.4 |  | miss_stall, spacing |
| kand.lat | held_out | ok | 2.08/2.07/4.20 | 2.06/2.12/4.25 | -0.9/+2.7/+1.2 |  | miss_stall, spacing |
| kand.rt | held_out | ok | 1.07/1.07/2.19 | 1.12/1.19/2.38 | +5.1/+11.0/+8.4 |  | miss_stall, spacing |
| kxor.lat | held_out | ok | 2.08/2.07/4.19 | 2.06/2.12/4.25 | -0.9/+2.7/+1.4 |  | miss_stall, spacing |
| kxor.rt | held_out | ok | 1.07/1.07/2.18 | 1.12/1.19/2.38 | +5.1/+11.0/+8.9 |  | miss_stall, spacing |
| swizzle_cdab.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.14 | -0.7/-1.5/-0.3 |  | miss_stall, dependency |
| swizzle_cdab.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.12/4.25 | -0.9/+2.7/+1.4 |  | miss_stall, spacing |
| swizzle_badc.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.14 | -0.7/-1.5/-0.3 |  | miss_stall, dependency |
| swizzle_badc.rt | held_out | ok | 2.07/2.07/4.19 | 2.06/2.12/4.25 | -0.4/+2.7/+1.4 |  | miss_stall, spacing |
| swizzle_dacb.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.14 | -0.7/-1.5/-0.3 |  | miss_stall, dependency |
| swizzle_dacb.rt | held_out | ok | 2.07/2.07/4.19 | 2.06/2.12/4.25 | -0.4/+2.7/+1.4 |  | miss_stall, spacing |
| swizzle_aaaa.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.14 | -0.7/-1.5/-0.3 |  | miss_stall, dependency |
| swizzle_aaaa.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.12/4.25 | -0.9/+2.7/+1.4 |  | miss_stall, spacing |
| swizzle_bbbb.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.14 | -0.7/-1.5/-0.3 |  | miss_stall, dependency |
| swizzle_bbbb.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.12/4.25 | -0.9/+2.7/+1.2 |  | miss_stall, spacing |
| swizzle_cccc.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.14 | -0.7/-1.5/-0.3 |  | miss_stall, dependency |
| swizzle_cccc.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.12/4.25 | -0.9/+2.7/+1.4 |  | miss_stall, spacing |
| swizzle_dddd.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.14 | -0.7/-1.5/-0.3 |  | miss_stall, dependency |
| swizzle_dddd.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.12/4.25 | -0.9/+2.7/+1.2 |  | miss_stall, spacing |
| vaddpd.lat | calibration | ok | 4.03/4.08/4.20 | 4.00/4.03/4.25 | -0.7/-1.2/+1.2 |  | miss_stall, dependency |
| vaddpd.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.12/4.25 | -0.9/+2.7/+1.4 |  | miss_stall, spacing |
| vmulpd.lat | calibration | ok | 4.03/4.08/4.20 | 4.00/4.03/4.25 | -0.7/-1.2/+1.2 |  | miss_stall, dependency |
| vmulpd.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.12/4.25 | -0.9/+2.7/+1.4 |  | miss_stall, spacing |
| vfmadd213pd.lat | calibration | ok | 4.03/4.08/4.20 | 4.00/4.03/4.25 | -0.7/-1.2/+1.2 |  | miss_stall, dependency |
| vfmadd213pd.rt | held_out | ok | 2.08/2.08/4.19 | 2.06/2.12/4.25 | -0.9/+2.2/+1.4 |  | miss_stall, spacing |
| vcvtfxpntdq2ps.lat | calibration | ok | 4.03/4.08/4.20 | 4.00/4.03/4.25 | -0.7/-1.2/+1.2 |  | miss_stall, dependency |
| vcvtfxpntdq2ps.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.12/4.25 | -0.9/+2.7/+1.2 |  | miss_stall, spacing |
| vcvtfxpntudq2ps.lat | calibration | ok | 4.03/4.08/4.21 | 4.00/4.03/4.25 | -0.7/-1.2/+1.0 |  | miss_stall, dependency |
| vcvtfxpntudq2ps.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.12/4.25 | -0.9/+2.7/+1.2 |  | miss_stall, spacing |
| vcvtfxpntps2dq.lat | calibration | ok | 4.03/4.08/4.20 | 4.00/4.03/4.25 | -0.7/-1.2/+1.2 |  | miss_stall, dependency |
| vcvtfxpntps2dq.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.12/4.25 | -0.9/+2.7/+1.2 |  | miss_stall, spacing |
| vcvtfxpntps2udq.lat | calibration | ok | 4.03/4.08/4.20 | 4.00/4.03/4.25 | -0.7/-1.2/+1.2 |  | miss_stall, dependency |
| vcvtfxpntps2udq.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.12/4.25 | -0.9/+2.7/+1.2 |  | miss_stall, spacing |
| vcvtfxpntpd2dq.lat | calibration | ok | 7.04/7.11/7.18 | 7.00/7.03/7.08 | -0.6/-1.1/-1.4 |  | miss_stall, dependency |
| vcvtfxpntpd2dq.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.12/4.25 | -0.9/+2.7/+1.2 |  | miss_stall, spacing |
| vcvtfxpntpd2udq.lat | calibration | ok | 7.05/7.11/7.18 | 7.00/7.03/7.08 | -0.7/-1.1/-1.4 |  | miss_stall, dependency |
| vcvtfxpntpd2udq.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.12/4.25 | -0.9/+2.7/+1.2 |  | miss_stall, spacing |
| x87_add.lat | calibration | ok | 3.02/3.08/4.13 | 3.09/3.16/4.38 | +2.5/+2.5/+5.9 |  | miss_stall, spacing |
| x87_add.rt | held_out | ok | 2.08/2.07/4.13 | 2.12/2.19/4.38 | +2.2/+5.7/+5.9 |  | miss_stall, spacing |
| x87_mul.lat | calibration | ok | 3.02/4.08/8.02 | 3.09/4.12/8.11 | +2.5/+1.1/+1.1 |  | miss_stall, spacing |
| x87_mul.rt | calibration | ok | 2.08/4.02/8.02 | 2.12/4.09/8.11 | +2.2/+1.8/+1.1 |  | miss_stall, spacing |
| x87_div.lat | calibration | ok | 39.25/76.30/151.79 | 38.00/76.00/152.00 | -3.2/-0.4/+0.1 |  | dependency, miss_stall |
| x87_div.rt | calibration | ok | 38.24/76.27/151.76 | 38.00/76.00/152.00 | -0.6/-0.4/+0.2 |  | resource, miss_stall |
| masked_load.lat | calibration | ok | 12.11/12.17/13.14 | 12.00/12.00/12.06 | -0.9/-1.4/-8.2 |  | miss_stall, dependency |
| masked_store.lat | held_out | ok | 12.11/12.17/13.17 | 12.00/12.00/12.06 | -0.9/-1.4/-8.4 |  | miss_stall, dependency |
| unpack.lat | calibration | ok | 12.11/16.79/24.40 | 12.00/12.00/13.22 | -0.9/-28.5/-45.8 |  | miss_stall, dependency |
| convert_up.lat | calibration | ok | 12.11/12.18/13.18 | 12.00/12.00/12.06 | -0.9/-1.5/-8.5 |  | miss_stall, dependency |
| convert_down.lat | held_out | ok | 12.11/12.95/13.14 | 12.00/12.00/12.06 | -0.9/-7.3/-8.2 |  | miss_stall, dependency |
| spill_reload.lat | calibration | ok | 12.11/12.98/13.14 | 12.00/12.00/12.03 | -0.9/-7.6/-8.4 |  | miss_stall, dependency |
| masked_load.rt | held_out | ok | 2.08/2.37/4.13 | 2.06/2.12/4.25 | -0.9/-10.3/+2.9 |  | miss_stall, spacing |
| masked_store.rt | held_out | ok | 2.08/2.08/4.13 | 1.12/1.19/2.38 | -45.9/-42.9/-42.5 |  | miss_stall, spacing |
| unpack.rt | held_out | ok | 4.09/4.08/8.14 | 4.06/4.12/8.25 | -0.7/+1.1/+1.4 |  | miss_stall, spacing |
| convert_up.rt | held_out | ok | 2.08/2.07/4.13 | 2.06/2.12/4.25 | -0.9/+2.7/+2.9 |  | miss_stall, spacing |
| convert_down.rt | held_out | ok | 2.08/2.07/4.13 | 1.12/1.19/2.38 | -45.9/-42.6/-42.5 |  | miss_stall, spacing |
| spill_reload.rt | calibration | ok | 5.09/4.20/4.26 | 4.12/4.16/4.27 | -19.0/-1.0/+0.1 |  | miss_stall, store_interlock |
| masked_load_sparse.lat | held_out | ok | 12.11/12.17/13.15 | 12.00/12.00/12.06 | -0.9/-1.4/-8.3 |  | miss_stall, dependency |
| masked_store_sparse.lat | held_out | ok | 12.11/12.18/13.14 | 12.00/12.00/12.06 | -0.9/-1.5/-8.2 |  | miss_stall, dependency |
| masked_load_sparse.rt | held_out | ok | 2.08/2.07/4.13 | 2.06/2.12/4.25 | -0.9/+2.7/+2.9 |  | miss_stall, spacing |
| masked_store_sparse.rt | held_out | ok | 2.08/2.07/4.13 | 1.12/1.19/2.38 | -45.9/-42.6/-42.5 |  | miss_stall, spacing |
| gather_all.lat | calibration | ok | 15.10/18.27/29.17 | 15.00/15.03/28.00 | -0.7/-17.7/-4.0 |  | dependency, miss_stall |
| gather_all.rt | calibration | ok | 7.08/14.09/28.10 | 7.09/14.06/28.12 | +0.2/-0.2/+0.1 |  | miss_stall, spacing |
| gather_scattered.lat | held_out | ok | 183.58/275.10/509.15 | 180.00/226.03/448.12 | -2.0/-17.8/-12.0 |  | dependency, spacing |
| gather_scattered.rt | calibration | ok | 175.14/259.58/506.78 | 172.09/224.06/448.12 | -1.7/-13.7/-11.6 |  | dependency, spacing |
| pair.vector_scalar | held_out | ok | 2.08/2.10/4.20 | 2.12/2.19/4.38 | +2.2/+4.2/+4.2 |  | miss_stall, spacing |
| pair.vector_vector | held_out | ok | 4.09/4.08/8.20 | 4.06/4.12/8.25 | -0.7/+1.1/+0.6 |  | miss_stall, spacing |
| pair.scalar_scalar | held_out | ok | 2.08/2.07/4.19 | 2.12/2.19/4.38 | +2.2/+5.7/+4.4 |  | miss_stall, spacing |
| agi.gap0 | calibration | ok | 3.11/3.17/4.26 | 3.12/3.16/4.38 | +0.5/-0.4/+2.7 |  | miss_stall, spacing |
| agi.gap1 | calibration | ok | 4.15/4.15/8.27 | 4.12/4.19/8.38 | -0.6/+0.9/+1.3 |  | miss_stall, spacing |
| agi.gap2 | calibration | ok | 6.16/6.16/12.27 | 6.12/6.19/12.38 | -0.6/+0.5/+0.9 |  | miss_stall, spacing |
| agi.gap3 | calibration | ok | 8.18/8.16/16.28 | 8.12/8.19/16.38 | -0.7/+0.3/+0.6 |  | miss_stall, spacing |
| agi.gap4 | calibration | ok | 10.19/10.18/20.29 | 10.12/10.19/20.38 | -0.6/+0.1/+0.4 |  | miss_stall, spacing |
| l1.load_lat | calibration | ok | 3.03/3.08/4.13 | 3.03/3.06/4.25 | +0.0/-0.6/+2.9 | 3.03/3.06/4.25 | miss_stall, spacing |
| l1.load_rt | held_out | ok | 2.20/2.27/4.38 | 2.22/2.28/4.50 | +0.9/+0.5/+2.7 | 2.22/2.28/4.50 | miss_stall, spacing |
| l1.store_normal | held_out | ok | 2.20/2.27/4.38 | 1.28/1.34/2.62 | -41.8/-40.8/-40.1 | 1.28/1.34/2.62 | miss_stall, spacing |
| l1.store_stream | calibration | ok | 27.19/30.09/36.16 | 27.28/27.31/36.20 | +0.3/-9.2/+0.1 | 27.28/27.31/36.20 | miss_stall, spacing |
| l2.load_lat | calibration | ok | 24.42/24.93/25.68 | 24.58/26.38/24.16 | +0.6/+5.8/-5.9 | 24.58/26.38/24.16 | miss_stall, spacing |
| l2.load_rt | held_out | ok | 23.38/23.51/23.85 | 26.70/26.70/27.14 | +14.2/+13.6/+13.8 | 26.70/26.70/27.14 | miss_stall, spacing |
| l2.store_normal | calibration | ok | 23.39/23.66/25.04 | 24.73/24.75/25.11 | +5.7/+4.6/+0.3 | 24.73/24.75/25.11 | miss_stall, spacing |
| l2.store_stream | calibration | ok | 27.49/30.22/36.29 | 27.28/27.31/36.20 | -0.8/-9.6/-0.2 | 27.28/27.31/36.20 | miss_stall, spacing |
| memory.load_lat | calibration | ok | 356.53/357.96/365.76 | 386.12/385.67/391.36 | +8.3/+7.7/+7.0 | 386.12/385.67/386.50 | miss_stall, spacing |
| memory.load_rt | calibration | ok | 37.35/47.78/77.92 | 37.39/48.12/85.53 | +0.1/+0.7/+9.8 | 359.70/359.70/360.05 | miss_stall, spacing |
| memory.store_normal | held_out | ok | 38.28/48.93/79.83 | 35.45/47.94/85.50 | -7.4/-2.0/+7.1 | 357.73/357.73/358.08 | miss_stall, spacing |
| memory.store_stream | calibration | ok | 157.12/158.07/160.26 | 157.28/157.31/157.31 | +0.1/-0.5/-1.8 | 157.28/157.31/157.31 | miss_stall, spacing |
| c2.vector | held_out | ok | 2.08/2.07/4.19 | 2.06/2.12/4.25 | -0.9/+2.7/+1.4 |  | miss_stall, spacing |
| c2.prefetch0 | held_out | ok | 1.07/1.09/2.13 | 1.12/1.19/2.38 | +5.1/+9.0/+11.5 |  | miss_stall, spacing |
| c2.prefetch1 | calibration | ok | 1.92/4.52/9.01 | 2.06/4.06/8.12 | +7.4/-10.1/-9.8 |  | miss_stall, spacing |
| c2.vector_prefetch0 | held_out | ok | 2.08/2.20/4.13 | 2.12/2.19/4.38 | +2.2/-0.5/+5.9 |  | miss_stall, spacing |
| c2.vector_prefetch1 | held_out | ok | 2.09/4.52/9.02 | 2.12/4.06/8.09 | +1.7/-10.1/-10.3 |  | miss_stall, spacing |
| c7.reduce.a1 | held_out | ok | -/-/4.13 | 4.00/4.03/4.25 | -/-/+2.9 |  | miss_stall, dependency |
| c7.reduce.a2 | held_out | ok | -/-/4.13 | 2.06/2.12/4.25 | -/-/+2.9 |  | miss_stall, spacing |
| c9.vector.u1 | held_out | ok | 4.02/4.02/- | 4.00/6.00/12.00 | -0.5/+49.3/- |  | miss_stall, spacing |
| c9.vector.u2 | held_out | ok | 3.02/3.01/- | 3.00/4.00/8.00 | -0.7/+32.9/- |  | miss_stall, spacing |
| c9.vector.u4 | held_out | ok | 2.52/2.51/- | 2.50/3.00/6.00 | -0.8/+19.5/- |  | miss_stall, spacing |
| c9.memory.u1 | calibration | ok | 11.07/13.08/- | 11.00/11.00/16.00 | -0.6/-15.9/- |  | miss_stall, dependency |
| c9.memory.u2 | calibration | ok | 8.56/12.03/- | 8.00/8.50/12.00 | -6.5/-29.3/- |  | miss_stall, spacing |
| c9.memory.u4 | calibration | ok | 8.30/11.01/- | 8.00/8.25/10.00 | -3.6/-25.1/- |  | miss_stall, spacing |
| c10.branch.fixed | calibration | ok | 6.22/-/17.02 | 6.19/8.25/16.50 | -0.5/-/-3.1 |  | miss_stall, spacing |
| c10.branch.random | calibration | ok | 11.27/-/27.76 | 11.34/11.69/18.27 | +0.7/-/-34.2 |  | miss_stall, spacing |
| s12-30-small/csr13/donor-off | held_out | ok | 8355.60/-/- | 9513.00/-/- | +13.9/-/- |  | miss_stall, x87_serial |
| s12-30-small/csr13/knc-switch-off | held_out | ok | 8484.20/-/- | 9651.00/-/- | +13.8/-/- |  | miss_stall, x87_serial |
| s12-30-small/csr13/knc-switch-on | held_out | ok | 8480.60/-/- | 9661.00/-/- | +13.9/-/- |  | miss_stall, x87_serial |
| s12-30-small/csr13/knc-switch-off-two-nests | held_out | ok | 8283.60/-/- | 9554.00/-/- | +15.3/-/- |  | miss_stall, x87_serial |
| s12-30-small/csr27/donor-off | held_out | ok | 22062.80/-/- | 25748.00/-/- | +16.7/-/- |  | miss_stall, x87_serial |
| s12-30-small/csr27/knc-switch-off | held_out | ok | 22200.90/-/- | 25887.00/-/- | +16.6/-/- |  | miss_stall, x87_serial |
| s12-30-small/csr27/knc-switch-on | held_out | ok | 22198.30/-/- | 25898.00/-/- | +16.7/-/- |  | miss_stall, x87_serial |
| s12-30-small/csr27/knc-switch-off-two-nests | held_out | ok | 22045.20/-/- | 25791.00/-/- | +17.0/-/- |  | miss_stall, x87_serial |
| s12-30-small/ptr13/donor-off | held_out | ok | 8516.20/-/- | 9718.00/-/- | +14.1/-/- |  | miss_stall, x87_serial |
| s12-30-small/ptr13/knc-switch-off | held_out | ok | 8670.80/-/- | 9823.00/-/- | +13.3/-/- |  | miss_stall, x87_serial |
| s12-30-small/ptr13/knc-switch-on | held_out | ok | 8925.20/-/- | 10031.00/-/- | +12.4/-/- |  | miss_stall, x87_serial |
| s12-30-small/ptr13/knc-switch-off-two-nests | held_out | ok | 8925.90/-/- | 10043.00/-/- | +12.5/-/- |  | miss_stall, x87_serial |
| s12-30-small/ptr27/donor-off | held_out | ok | 23353.60/-/- | 27529.00/-/- | +17.9/-/- |  | miss_stall, x87_serial |
| s12-30-small/ptr27/knc-switch-off | held_out | ok | 23521.50/-/- | 27632.00/-/- | +17.5/-/- |  | miss_stall, x87_serial |
| s12-30-small/ptr27/knc-switch-on | held_out | ok | 23759.50/-/- | 27840.00/-/- | +17.2/-/- |  | miss_stall, x87_serial |
| s12-30-small/ptr27/knc-switch-off-two-nests | held_out | ok | 23764.70/-/- | 27852.00/-/- | +17.2/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-104/donor | held_out | ok | 699.57/-/- | 728.72/-/- | +4.2/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-104/donor_pf | held_out | ok | 699.55/-/- | 730.72/-/- | +4.5/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-104/knc | held_out | ok | 701.33/-/- | 731.70/-/- | +4.3/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-104/knc_pf | held_out | ok | 699.22/-/- | 731.70/-/- | +4.6/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-104/knc_noalign | held_out | ok | 695.59/-/- | 728.70/-/- | +4.8/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-104/knc_skip7 | held_out | ok | 699.15/-/- | 729.70/-/- | +4.4/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-104/knc_nosched | held_out | ok | 646.11/-/- | 676.29/-/- | +4.7/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-104/knc_nosched_noalign | held_out | ok | 640.39/-/- | 672.29/-/- | +5.0/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-toy/spmv/donor | held_out | ok | 533824.00/-/- | 547738.00/-/- | +2.6/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-toy/spmv/donor_pf | held_out | ok | 537748.00/-/- | 549786.00/-/- | +2.2/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-toy/spmv/knc | held_out | ok | 533761.00/-/- | 550796.00/-/- | +3.2/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-toy/spmv/knc_pf | held_out | ok | 535369.00/-/- | 550796.00/-/- | +2.9/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-toy/spmv/knc_noalign | held_out | ok | 531658.00/-/- | 547722.00/-/- | +3.0/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-toy/spmv/knc_skip7 | held_out | ok | 540803.00/-/- | 548746.00/-/- | +1.5/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-toy/spmv/knc_nosched | held_out | ok | 498036.00/-/- | 506428.00/-/- | +1.7/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-toy/spmv/knc_nosched_noalign | held_out | ok | 487592.00/-/- | 502328.00/-/- | +3.0/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-toy/symgs/donor | held_out | ok | 559902.00/-/- | 597887.00/-/- | +6.8/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-toy/symgs/donor_pf | held_out | ok | 561994.00/-/- | 597889.00/-/- | +6.4/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-toy/symgs/knc | held_out | ok | 567401.00/-/- | 600690.00/-/- | +5.9/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-toy/symgs/knc_pf | held_out | ok | 564673.00/-/- | 596594.00/-/- | +5.7/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-toy/symgs/knc_noalign | held_out | ok | 566156.00/-/- | 594545.00/-/- | +5.0/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-toy/symgs/knc_skip7 | held_out | ok | 569211.00/-/- | 595570.00/-/- | +4.6/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-toy/symgs/knc_nosched | held_out | ok | 526050.00/-/- | 556069.00/-/- | +5.7/-/- |  | miss_stall, x87_serial |
| s12-31-hpcg-toy/symgs/knc_nosched_noalign | held_out | ok | 516577.00/-/- | 549924.00/-/- | +6.5/-/- |  | miss_stall, x87_serial |
| s12-31-microbench/gas_0 | calibration | ok | 488.90/-/- | 503.00/-/- | +2.9/-/- |  | miss_stall, spacing |
| s12-31-microbench/gas_1 | held_out | ok | 488.50/-/- | 504.00/-/- | +3.2/-/- |  | miss_stall, spacing |
| s12-31-microbench/gas_2 | held_out | ok | 490.00/-/- | 504.00/-/- | +2.9/-/- |  | miss_stall, spacing |
| s12-31-microbench/gas_3 | held_out | ok | 489.30/-/- | 504.00/-/- | +3.0/-/- |  | miss_stall, spacing |
| s12-31-microbench/gas_4 | held_out | ok | 488.40/-/- | 504.00/-/- | +3.2/-/- |  | miss_stall, spacing |
| s12-31-microbench/gas_5 | held_out | ok | 488.60/-/- | 504.00/-/- | +3.2/-/- |  | miss_stall, spacing |
| s12-31-microbench/gas_6 | held_out | ok | 492.00/-/- | 504.00/-/- | +2.4/-/- |  | miss_stall, spacing |
| s12-31-microbench/gas_7 | held_out | ok | 485.80/-/- | 504.00/-/- | +3.7/-/- |  | miss_stall, spacing |
| s12-31-microbench/gas_8 | held_out | ok | 489.90/-/- | 504.00/-/- | +2.9/-/- |  | miss_stall, spacing |
| s12-31-microbench/gas_9 | held_out | ok | 489.80/-/- | 504.00/-/- | +2.9/-/- |  | miss_stall, spacing |
| s12-31-microbench/gas_10 | held_out | ok | 492.20/-/- | 506.00/-/- | +2.8/-/- |  | miss_stall, spacing |
| s12-31-microbench/gas_11 | held_out | ok | 494.70/-/- | 508.00/-/- | +2.7/-/- |  | miss_stall, spacing |
| s12-31-microbench/gas_12 | held_out | ok | 495.90/-/- | 510.00/-/- | +2.8/-/- |  | miss_stall, spacing |
| s12-31-microbench/gas_13 | held_out | ok | 500.70/-/- | 512.00/-/- | +2.3/-/- |  | miss_stall, spacing |
| s12-31-microbench/gas_14 | held_out | ok | 501.10/-/- | 514.00/-/- | +2.6/-/- |  | miss_stall, spacing |
| s12-31-microbench/gas_15 | held_out | ok | 502.20/-/- | 516.00/-/- | +2.7/-/- |  | miss_stall, spacing |
| s12-31-microbench/one_0 | held_out | ok | 489.10/-/- | 503.00/-/- | +2.8/-/- |  | miss_stall, spacing |
| s12-31-microbench/one_1 | held_out | ok | 487.50/-/- | 504.00/-/- | +3.4/-/- |  | miss_stall, spacing |
| s12-31-microbench/one_2 | held_out | ok | 492.50/-/- | 506.00/-/- | +2.7/-/- |  | miss_stall, spacing |
| s12-31-microbench/one_3 | held_out | ok | 494.00/-/- | 508.00/-/- | +2.8/-/- |  | miss_stall, spacing |
| s12-31-microbench/one_4 | held_out | ok | 493.90/-/- | 510.00/-/- | +3.3/-/- |  | miss_stall, spacing |
| s12-31-microbench/one_5 | held_out | ok | 498.20/-/- | 512.00/-/- | +2.8/-/- |  | miss_stall, spacing |
| s12-31-microbench/one_6 | held_out | ok | 499.50/-/- | 514.00/-/- | +2.9/-/- |  | miss_stall, spacing |
| s12-31-microbench/one_7 | held_out | ok | 501.60/-/- | 516.00/-/- | +2.9/-/- |  | spacing, miss_stall |
| s12-31-microbench/one_8 | held_out | ok | 504.30/-/- | 518.00/-/- | +2.7/-/- |  | spacing, miss_stall |
| s12-31-microbench/one_9 | held_out | ok | 505.50/-/- | 520.00/-/- | +2.9/-/- |  | spacing, miss_stall |
| s12-31-microbench/one_10 | held_out | ok | 506.20/-/- | 522.00/-/- | +3.1/-/- |  | spacing, miss_stall |
| s12-31-microbench/one_11 | held_out | ok | 511.90/-/- | 524.00/-/- | +2.4/-/- |  | spacing, miss_stall |
| s12-31-microbench/one_12 | held_out | ok | 510.90/-/- | 526.00/-/- | +3.0/-/- |  | spacing, miss_stall |
| s12-31-microbench/one_13 | held_out | ok | 514.20/-/- | 528.00/-/- | +2.7/-/- |  | spacing, miss_stall |
| s12-31-microbench/one_14 | held_out | ok | 514.30/-/- | 530.00/-/- | +3.1/-/- |  | spacing, miss_stall |
| s12-31-microbench/one_15 | calibration | ok | 517.00/-/- | 532.00/-/- | +2.9/-/- |  | spacing, miss_stall |
| s12-31-microbench/pf_0 | held_out | ok | 489.30/-/- | 503.00/-/- | +2.8/-/- |  | miss_stall, spacing |
| s12-31-microbench/pf_1 | held_out | ok | 487.90/-/- | 504.00/-/- | +3.3/-/- |  | miss_stall, spacing |
| s12-31-microbench/pf_2 | held_out | ok | 490.00/-/- | 506.00/-/- | +3.3/-/- |  | miss_stall, spacing |
| s12-31-microbench/pf_3 | held_out | ok | 491.60/-/- | 504.00/-/- | +2.5/-/- |  | miss_stall, spacing |
| s12-31-microbench/pf_4 | held_out | ok | 487.80/-/- | 504.00/-/- | +3.3/-/- |  | miss_stall, spacing |
| s12-31-microbench/pf_5 | held_out | ok | 488.30/-/- | 504.00/-/- | +3.2/-/- |  | miss_stall, spacing |
| s12-31-microbench/pf_6 | held_out | ok | 492.90/-/- | 506.00/-/- | +2.7/-/- |  | miss_stall, spacing |
| s12-31-microbench/pf_7 | held_out | ok | 488.20/-/- | 504.00/-/- | +3.2/-/- |  | miss_stall, spacing |
| s12-31-microbench/pf_8 | held_out | ok | 490.10/-/- | 504.00/-/- | +2.8/-/- |  | miss_stall, spacing |
| s12-31-microbench/pf_9 | held_out | ok | 490.60/-/- | 506.00/-/- | +3.1/-/- |  | miss_stall, spacing |
| s12-31-microbench/pf_10 | held_out | ok | 489.90/-/- | 506.00/-/- | +3.3/-/- |  | miss_stall, spacing |
| s12-31-microbench/pf_11 | held_out | ok | 492.10/-/- | 506.00/-/- | +2.8/-/- |  | miss_stall, spacing |
| s12-31-microbench/pf_12 | held_out | ok | 490.30/-/- | 506.00/-/- | +3.2/-/- |  | miss_stall, spacing |
| s12-31-microbench/pf_13 | held_out | ok | 491.80/-/- | 506.00/-/- | +2.9/-/- |  | miss_stall, spacing |
| s12-31-microbench/pf_14 | held_out | ok | 492.80/-/- | 506.00/-/- | +2.7/-/- |  | miss_stall, spacing |
| s12-31-microbench/pf_15 | held_out | ok | 490.80/-/- | 506.00/-/- | +3.1/-/- |  | miss_stall, spacing |
| s12-31-microbench/mis_4 | held_out | ok | 487.30/-/- | 503.00/-/- | +3.2/-/- |  | miss_stall, spacing |
| s12-31-microbench/mis_8 | held_out | ok | 489.10/-/- | 503.00/-/- | +2.8/-/- |  | miss_stall, spacing |
| s12-31-microbench/mis_12 | held_out | ok | 486.90/-/- | 503.00/-/- | +3.3/-/- |  | miss_stall, spacing |
| s12-31-microbench/mis_16 | held_out | ok | 489.50/-/- | 503.00/-/- | +2.8/-/- |  | miss_stall, spacing |
| s12-31-microbench/mis_20 | held_out | ok | 487.80/-/- | 503.00/-/- | +3.1/-/- |  | miss_stall, spacing |
| s12-31-microbench/mis_24 | held_out | ok | 489.20/-/- | 503.00/-/- | +2.8/-/- |  | miss_stall, spacing |
| s12-31-microbench/mis_28 | held_out | ok | 487.40/-/- | 503.00/-/- | +3.2/-/- |  | miss_stall, spacing |
| s12-31-microbench/mis_32 | held_out | ok | 487.80/-/- | 503.00/-/- | +3.1/-/- |  | miss_stall, spacing |
| s12-31-microbench/mis_36 | held_out | ok | 487.30/-/- | 503.00/-/- | +3.2/-/- |  | miss_stall, spacing |
| s12-31-microbench/mis_40 | held_out | ok | 490.00/-/- | 503.00/-/- | +2.7/-/- |  | miss_stall, spacing |
| s12-31-microbench/mis_44 | held_out | ok | 489.20/-/- | 503.00/-/- | +2.8/-/- |  | miss_stall, spacing |
| s12-31-microbench/mis_48 | held_out | ok | 489.60/-/- | 503.00/-/- | +2.7/-/- |  | miss_stall, spacing |
| s12-31-microbench/mis_52 | held_out | ok | 490.50/-/- | 503.00/-/- | +2.5/-/- |  | miss_stall, spacing |
| s12-31-microbench/mis_56 | held_out | ok | 486.90/-/- | 503.00/-/- | +3.3/-/- |  | miss_stall, spacing |
| s12-31-microbench/mis_60 | held_out | ok | 488.60/-/- | 503.00/-/- | +2.9/-/- |  | miss_stall, spacing |
| s12-31-microbench/inc_0 | held_out | ok | 489.00/-/- | 503.00/-/- | +2.9/-/- |  | miss_stall, spacing |
| s12-31-microbench/adj_0 | calibration | ok | 433.50/-/- | 449.00/-/- | +3.6/-/- |  | miss_stall, spacing |
| s12-31-microbench/mid_0 | held_out | ok | 432.50/-/- | 449.00/-/- | +3.8/-/- |  | miss_stall, spacing |
| s12-31-microbench/mov_adj_0 | held_out | ok | 487.90/-/- | 503.00/-/- | +3.1/-/- |  | miss_stall, spacing |
| s12-31-microbench/mov_split_0 | held_out | ok | 487.60/-/- | 503.00/-/- | +3.2/-/- |  | miss_stall, spacing |

## Card-scale cases (analytical card scale; outside the core model, not in the statistics)

| case | status | per-core cycles per unit (stand-in loop) | predicted GB/s | measured GB/s (median) |
|---|---|---:|---:|---:|
| gemv-fp32-card | ok | 3.0 | 186.1 | 125.30 |
| stream-read-card | ok | 4.125 | 186.1 | 147.24 |
| stream-rmw-card | ok | 13.125 | 179.4 | 179.11 |
| stream-write-ngo-card | ok | 31.125 | 169.7 | 169.23 |

- predicted = slope of completion cycles between 2 and 4 rounds, divided by 32 units per round; TSC ticks and core cycles are treated as equal (0.5% difference on this card)
- footprints that fit L1 (L2) with all active threads are declared warm in L1 (L2) because the driver measures a warm steady state; larger footprints start cold
- the kernel catalog was regenerated from tests/bench/knc-char/kernels.py; S8-07 additions shift kernel indices but the measured S6-03 bodies are the same templates
- calibration rows set a parameter of the profile and are excluded from the held-out statistics
- every prediction is a model output; the measured column is native
- compiled rows (tests/heldout_native/<case>/) come from the binaries and objects that ran on the card, with code layout; seconds converted with card.clock_hz 1.238 GHz; variants marked 'calibrates' in a case.json set a model rule and are calibration rows; each prediction is recorded in the case's prediction.json
- decision bar (compiled held-out rows only): median absolute error at most 10%, right winner in at least 90% of within-group pairs measured more than 5% apart, at least 50 loops
