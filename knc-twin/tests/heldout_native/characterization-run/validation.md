# Held-out validation against the characterization microbenchmarks

Generated 2026-11-15T20:27:12Z. Profile card-7120-measured (hash ad82d111c1f8...). line_tracking cold memory, TLB modeled, hardware prefetcher off, memory service modeled

## Error statistics (scenario A, per thread count)

| rows | n | median abs err % | worst abs err % | within 15% | within 30% | mean signed err % |
|---|---:|---:|---:|---:|---:|---:|
| calibration_threads_1 | 53 | 0.7 | 863.1 | 50 | 52 | 16.9 |
| calibration_threads_2 | 51 | 1.5 | 652.8 | 48 | 50 | 10.8 |
| calibration_threads_4 | 52 | 1.8 | 362.1 | 48 | 50 | 3.2 |
| held_out_threads_1 | 62 | 0.9 | 834.5 | 56 | 58 | 13.3 |
| held_out_threads_2 | 62 | 0.4 | 631.1 | 57 | 58 | 9.8 |
| held_out_threads_4 | 59 | 1.6 | 348.6 | 57 | 57 | 7.4 |

## Ranking reliability

306 of 313 measured pairwise orderings (within groups, measured difference > 3%) reproduced: reliability 0.978.

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
| gathers@threads_4 | 5 | 5 |  |
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
| memory_forms@threads_2 | 13 | 14 | masked_load.lat vs spill_reload.lat: 12.17/12.98 -> 12.00/12.00 |
| memory_forms@threads_4 | 13 | 14 | unpack.rt vs spill_reload.rt: 8.14/4.26 -> 8.12/11.12 |
| pairing@threads_1 | 2 | 2 |  |
| pairing@threads_2 | 2 | 2 |  |
| pairing@threads_4 | 2 | 2 |  |
| prefetch_pairing@threads_1 | 7 | 7 |  |
| prefetch_pairing@threads_2 | 9 | 9 |  |
| prefetch_pairing@threads_4 | 8 | 8 |  |
| stores@threads_1 | 13 | 14 | memory.store_normal vs memory.store_stream: 38.28/157.12 -> 357.73/157.28 |
| stores@threads_2 | 13 | 14 | memory.store_normal vs memory.store_stream: 48.93/158.07 -> 357.73/157.31 |
| stores@threads_4 | 13 | 14 | memory.store_normal vs memory.store_stream: 79.83/160.26 -> 358.08/157.31 |
| throughput_rows@threads_1 | 17 | 17 |  |
| throughput_rows@threads_2 | 22 | 24 | vaddps.rt vs masked_load.rt: 2.07/2.37 -> 2.06/2.06; vpermd.rt vs masked_load.rt: 2.07/2.37 -> 2.06/2.06 |
| throughput_rows@threads_4 | 21 | 21 |  |

## Rows

| test | class | status | measured 1/2/4 | predicted A 1/2/4 | err % 1/2/4 | predicted B (HWP) 1/2/4 | limiting (1 thread) |
|---|---|---|---|---|---|---|---|
| vaddps.lat | calibration | ok | 4.02/4.08/4.19 | 4.00/4.00/4.12 | -0/-2/-2 |  | miss_stall, dependency |
| vaddps.rt | calibration | ok | 2.08/2.07/4.18 | 2.06/2.06/4.12 | -1/-0/-1 |  | miss_stall, spacing |
| vmulps.lat | calibration | ok | 4.03/4.08/4.20 | 4.00/4.00/4.12 | -1/-2/-2 |  | miss_stall, dependency |
| vmulps.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| vfmadd213ps.lat | calibration | ok | 4.02/4.08/4.20 | 4.00/4.00/4.12 | -0/-2/-2 |  | miss_stall, dependency |
| vfmadd213ps.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| vpaddd.lat | calibration | ok | 4.03/4.08/4.20 | 4.00/4.00/4.12 | -1/-2/-2 |  | miss_stall, dependency |
| vpaddd.rt | held_out | ok | 2.08/2.32/4.19 | 2.06/2.06/4.12 | -1/-11/-2 |  | miss_stall, spacing |
| vpxord.lat | calibration | ok | 4.03/4.08/4.21 | 4.00/4.00/4.12 | -1/-2/-2 |  | miss_stall, dependency |
| vpxord.rt | held_out | ok | 2.07/2.07/4.19 | 2.06/2.06/4.12 | -0/-0/-2 |  | miss_stall, spacing |
| vpermd.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.03 | -1/-1/-2 |  | miss_stall, dependency |
| vpermd.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| vpermf32x4.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.03 | -1/-1/-2 |  | miss_stall, dependency |
| vpermf32x4.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| vrcp23ps.lat | calibration | unsupported: not functionally complete: timing only: timing only (23-bit approximat | 6.04/6.09/6.16 | -/-/- | -/-/- |  |  |
| vrcp23ps.rt | held_out | unsupported: not functionally complete: timing only: timing only (23-bit approximat | 2.08/2.07/4.20 | -/-/- | -/-/- |  |  |
| scalar_add.lat | calibration | ok | 2.08/2.07/4.19 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| scalar_add.rt | held_out | ok | 1.07/1.07/2.19 | 1.12/1.12/2.25 | +5/+5/+3 |  | miss_stall, spacing |
| scalar_xor.lat | held_out | ok | 2.08/2.07/4.20 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| scalar_xor.rt | held_out | ok | 1.07/1.07/2.18 | 1.12/1.12/2.25 | +5/+5/+3 |  | miss_stall, spacing |
| kmov.lat | held_out | ok | 2.08/2.07/4.19 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| kmov.rt | held_out | ok | 1.07/1.07/2.19 | 1.12/1.12/2.25 | +5/+5/+3 |  | miss_stall, spacing |
| kand.lat | held_out | ok | 2.08/2.07/4.20 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| kand.rt | held_out | ok | 1.07/1.07/2.19 | 1.12/1.12/2.25 | +5/+5/+3 |  | miss_stall, spacing |
| kxor.lat | held_out | ok | 2.08/2.07/4.19 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| kxor.rt | held_out | ok | 1.07/1.07/2.18 | 1.12/1.12/2.25 | +5/+5/+3 |  | miss_stall, spacing |
| swizzle_cdab.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.03 | -1/-1/-2 |  | miss_stall, dependency |
| swizzle_cdab.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| swizzle_badc.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.03 | -1/-1/-2 |  | miss_stall, dependency |
| swizzle_badc.rt | held_out | ok | 2.07/2.07/4.19 | 2.06/2.06/4.12 | -0/-0/-2 |  | miss_stall, spacing |
| swizzle_dacb.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.03 | -1/-1/-2 |  | miss_stall, dependency |
| swizzle_dacb.rt | held_out | ok | 2.07/2.07/4.19 | 2.06/2.06/4.12 | -0/-0/-2 |  | miss_stall, spacing |
| swizzle_aaaa.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.03 | -1/-1/-2 |  | miss_stall, dependency |
| swizzle_aaaa.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| swizzle_bbbb.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.03 | -1/-1/-2 |  | miss_stall, dependency |
| swizzle_bbbb.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| swizzle_cccc.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.03 | -1/-1/-2 |  | miss_stall, dependency |
| swizzle_cccc.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| swizzle_dddd.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.03 | -1/-1/-2 |  | miss_stall, dependency |
| swizzle_dddd.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| vaddpd.lat | calibration | ok | 4.03/4.08/4.20 | 4.00/4.00/4.12 | -1/-2/-2 |  | miss_stall, dependency |
| vaddpd.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| vmulpd.lat | calibration | ok | 4.03/4.08/4.20 | 4.00/4.00/4.12 | -1/-2/-2 |  | miss_stall, dependency |
| vmulpd.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| vfmadd213pd.lat | calibration | ok | 4.03/4.08/4.20 | 4.00/4.00/4.12 | -1/-2/-2 |  | miss_stall, dependency |
| vfmadd213pd.rt | held_out | ok | 2.08/2.08/4.19 | 2.06/2.06/4.12 | -1/-1/-2 |  | miss_stall, spacing |
| vcvtfxpntdq2ps.lat | calibration | ok | 4.03/4.08/4.20 | 4.00/4.00/4.12 | -1/-2/-2 |  | miss_stall, dependency |
| vcvtfxpntdq2ps.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| vcvtfxpntudq2ps.lat | calibration | ok | 4.03/4.08/4.21 | 4.00/4.00/4.12 | -1/-2/-2 |  | miss_stall, dependency |
| vcvtfxpntudq2ps.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| vcvtfxpntps2dq.lat | calibration | ok | 4.03/4.08/4.20 | 4.00/4.00/4.12 | -1/-2/-2 |  | miss_stall, dependency |
| vcvtfxpntps2dq.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| vcvtfxpntps2udq.lat | calibration | ok | 4.03/4.08/4.20 | 4.00/4.00/4.12 | -1/-2/-2 |  | miss_stall, dependency |
| vcvtfxpntps2udq.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| vcvtfxpntpd2dq.lat | calibration | ok | 7.04/7.11/7.18 | 7.00/7.00/7.00 | -1/-2/-3 |  | miss_stall, dependency |
| vcvtfxpntpd2dq.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| vcvtfxpntpd2udq.lat | calibration | ok | 7.05/7.11/7.18 | 7.00/7.00/7.00 | -1/-2/-3 |  | miss_stall, dependency |
| vcvtfxpntpd2udq.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| x87_add.lat | calibration | ok | 3.02/3.08/4.13 | 3.03/3.06/4.12 | +0/-1/-0 |  | miss_stall, spacing |
| x87_add.rt | held_out | ok | 2.08/2.07/4.13 | 2.06/2.06/4.12 | -1/-0/-0 |  | miss_stall, spacing |
| x87_mul.lat | calibration | ok | 3.02/4.08/8.02 | 3.03/4.06/8.00 | +0/-0/-0 |  | miss_stall, spacing |
| x87_mul.rt | calibration | ok | 2.08/4.02/8.02 | 2.06/4.00/8.00 | -1/-0/-0 |  | miss_stall, spacing |
| x87_div.lat | calibration | ok | 39.25/76.30/151.79 | 38.00/76.00/152.00 | -3/-0/+0 |  | dependency, miss_stall |
| x87_div.rt | calibration | ok | 38.24/76.27/151.76 | 38.00/76.00/152.00 | -1/-0/+0 |  | resource, miss_stall |
| masked_load.lat | calibration | ok | 12.11/12.17/13.14 | 12.00/12.00/12.09 | -1/-1/-8 |  | miss_stall, dependency |
| masked_store.lat | held_out | ok | 12.11/12.17/13.17 | 12.00/12.00/12.09 | -1/-1/-8 |  | miss_stall, dependency |
| unpack.lat | calibration | ok | 12.11/16.79/24.40 | 14.00/14.00/17.09 | +16/-17/-30 |  | miss_stall, dependency |
| convert_up.lat | calibration | ok | 12.11/12.18/13.18 | 12.00/12.00/12.09 | -1/-1/-8 |  | miss_stall, dependency |
| convert_down.lat | held_out | ok | 12.11/12.95/13.14 | 12.00/12.00/12.09 | -1/-7/-8 |  | miss_stall, dependency |
| spill_reload.lat | calibration | ok | 12.11/12.98/13.14 | 12.00/12.00/12.50 | -1/-8/-5 |  | miss_stall, dependency |
| masked_load.rt | held_out | ok | 2.08/2.37/4.13 | 2.06/2.06/4.12 | -1/-13/-0 |  | miss_stall, spacing |
| masked_store.rt | held_out | ok | 2.08/2.08/4.13 | 2.06/2.06/4.12 | -1/-1/-0 |  | miss_stall, spacing |
| unpack.rt | held_out | ok | 4.09/4.08/8.14 | 4.06/4.06/8.12 | -1/-0/-0 |  | miss_stall, spacing |
| convert_up.rt | held_out | ok | 2.08/2.07/4.13 | 2.06/2.06/4.12 | -1/-0/-0 |  | miss_stall, spacing |
| convert_down.rt | held_out | ok | 2.08/2.07/4.13 | 2.06/2.06/4.12 | -1/-0/-0 |  | miss_stall, spacing |
| spill_reload.rt | held_out | ok | 5.09/4.20/4.26 | 9.06/9.06/11.12 | +78/+116/+161 |  | miss_stall, dependency |
| masked_load_sparse.lat | held_out | ok | 12.11/12.17/13.15 | 12.00/12.00/12.09 | -1/-1/-8 |  | miss_stall, dependency |
| masked_store_sparse.lat | held_out | ok | 12.11/12.18/13.14 | 12.00/12.00/12.09 | -1/-1/-8 |  | miss_stall, dependency |
| masked_load_sparse.rt | held_out | ok | 2.08/2.07/4.13 | 2.06/2.06/4.12 | -1/-0/-0 |  | miss_stall, spacing |
| masked_store_sparse.rt | held_out | ok | 2.08/2.07/4.13 | 2.06/2.06/4.12 | -1/-0/-0 |  | miss_stall, spacing |
| gather_all.lat | calibration | ok | 15.10/18.27/29.17 | 19.00/19.00/28.00 | +26/+4/-4 |  | dependency, miss_stall |
| gather_all.rt | calibration | ok | 7.08/14.09/28.10 | 7.09/14.00/28.00 | +0/-1/-0 |  | miss_stall, spacing |
| gather_scattered.lat | held_out | ok | 183.58/275.10/509.15 | 124.00/224.00/448.00 | -32/-19/-12 |  | dependency, miss_stall |
| gather_scattered.rt | held_out | ok | 175.14/259.58/506.78 | 112.09/224.00/448.00 | -36/-14/-12 |  | dependency, miss_stall |
| pair.vector_scalar | held_out | ok | 2.08/2.10/4.20 | 2.12/2.12/4.25 | +2/+1/+1 |  | miss_stall, spacing |
| pair.vector_vector | held_out | ok | 4.09/4.08/8.20 | 4.06/4.06/8.12 | -1/-0/-1 |  | miss_stall, spacing |
| pair.scalar_scalar | held_out | ok | 2.08/2.07/4.19 | 2.12/2.12/4.25 | +2/+3/+1 |  | miss_stall, spacing |
| agi.gap0 | calibration | ok | 3.11/3.17/4.26 | 3.12/3.16/4.25 | +0/-0/-0 |  | miss_stall, spacing |
| agi.gap1 | calibration | ok | 4.15/4.15/8.27 | 4.09/4.12/8.12 | -1/-1/-2 |  | miss_stall, spacing |
| agi.gap2 | calibration | ok | 6.16/6.16/12.27 | 6.06/6.06/12.12 | -2/-2/-1 |  | miss_stall, spacing |
| agi.gap3 | calibration | ok | 8.18/8.16/16.28 | 8.06/8.06/16.12 | -1/-1/-1 |  | miss_stall, spacing |
| agi.gap4 | calibration | ok | 10.19/10.18/20.29 | 10.06/10.06/20.12 | -1/-1/-1 |  | miss_stall, spacing |
| l1.load_lat | calibration | ok | 3.03/3.08/4.13 | 3.03/3.06/4.12 | +0/-1/-0 | 3.03/3.06/4.12 | miss_stall, spacing |
| l1.load_rt | held_out | ok | 2.20/2.27/4.38 | 2.22/2.25/4.38 | +1/-1/-0 | 2.22/2.25/4.38 | miss_stall, spacing |
| l1.store_normal | held_out | ok | 2.20/2.27/4.38 | 2.22/2.25/4.38 | +1/-1/-0 | 2.22/2.25/4.38 | miss_stall, spacing |
| l1.store_stream | calibration | ok | 27.19/30.09/36.16 | 27.28/27.31/36.17 | +0/-9/+0 | 27.28/27.31/36.17 | miss_stall, spacing |
| l2.load_lat | calibration | ok | 24.42/24.93/25.68 | 24.58/26.36/24.19 | +1/+6/-6 | 24.58/26.36/24.19 | miss_stall, spacing |
| l2.load_rt | held_out | ok | 23.38/23.51/23.85 | 26.70/26.70/27.05 | +14/+14/+13 | 26.70/26.70/27.05 | miss_stall, spacing |
| l2.store_normal | calibration | ok | 23.39/23.66/25.04 | 24.73/24.75/25.08 | +6/+5/+0 | 24.73/24.75/25.08 | miss_stall, spacing |
| l2.store_stream | calibration | ok | 27.49/30.22/36.29 | 27.28/27.31/36.17 | -1/-10/-0 | 27.28/27.31/36.17 | miss_stall, spacing |
| memory.load_lat | calibration | ok | 356.53/357.96/365.76 | 386.12/385.67/386.50 | +8/+8/+6 | 386.12/385.67/391.36 | miss_stall, spacing |
| memory.load_rt | calibration | ok | 37.35/47.78/77.92 | 359.70/359.70/360.05 | +863/+653/+362 | 37.39/48.12/85.53 | miss_stall, spacing |
| memory.store_normal | held_out | ok | 38.28/48.93/79.83 | 357.73/357.73/358.08 | +835/+631/+349 | 35.45/47.94/85.50 | miss_stall, spacing |
| memory.store_stream | calibration | ok | 157.12/158.07/160.26 | 157.28/157.31/157.31 | +0/-0/-2 | 157.28/157.31/157.31 | miss_stall, spacing |
| c2.vector | held_out | ok | 2.08/2.07/4.19 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| c2.prefetch0 | held_out | ok | 1.07/1.09/2.13 | 1.12/1.12/2.25 | +5/+3/+6 |  | miss_stall, spacing |
| c2.prefetch1 | calibration | ok | 1.92/4.52/9.01 | 2.06/4.00/8.00 | +7/-12/-11 |  | miss_stall, spacing |
| c2.vector_prefetch0 | held_out | ok | 2.08/2.20/4.13 | 2.12/2.12/4.25 | +2/-3/+3 |  | miss_stall, spacing |
| c2.vector_prefetch1 | held_out | ok | 2.09/4.52/9.02 | 2.12/4.00/7.97 | +2/-12/-12 |  | miss_stall, spacing |
| c7.reduce.a1 | held_out | ok | -/-/4.13 | 4.00/4.00/4.12 | -/-/-0 |  | miss_stall, dependency |
| c7.reduce.a2 | held_out | ok | -/-/4.13 | 2.06/2.06/4.12 | -/-/-0 |  | miss_stall, spacing |
| c9.vector.u1 | held_out | ok | 4.02/4.02/- | 4.00/4.00/8.00 | -0/-0/- |  | miss_stall, spacing |
| c9.vector.u2 | held_out | ok | 3.02/3.01/- | 3.00/3.00/6.00 | -1/-0/- |  | miss_stall, spacing |
| c9.vector.u4 | held_out | ok | 2.52/2.51/- | 2.50/2.50/5.00 | -1/-0/- |  | miss_stall, spacing |
| c9.memory.u1 | calibration | ok | 11.07/13.08/- | 11.00/11.00/12.00 | -1/-16/- |  | miss_stall, dependency |
| c9.memory.u2 | held_out | ok | 8.56/12.03/- | 7.00/7.00/10.00 | -18/-42/- |  | miss_stall, spacing |
| c9.memory.u4 | held_out | ok | 8.30/11.01/- | 6.50/6.50/9.00 | -22/-41/- |  | miss_stall, spacing |
| c10.branch.fixed | calibration | ok | 6.22/-/17.02 | 6.19/6.19/12.38 | -1/-/-27 |  | miss_stall, spacing |
| c10.branch.random | calibration | ok | 11.27/-/27.76 | 11.34/11.34/14.47 | +1/-/-48 |  | miss_stall, spacing |

- predicted = slope of completion cycles between 2 and 4 rounds, divided by 32 units per round; TSC ticks and core cycles are treated as equal (0.5% difference on this card)
- footprints that fit L1 (L2) with all active threads are declared warm in L1 (L2) because the driver measures a warm steady state; larger footprints start cold
- the kernel catalog was regenerated from tests/bench/knc-char/kernels.py; S8-07 additions shift kernel indices but the measured S6-03 bodies are the same templates
- calibration rows set a parameter of the profile and are excluded from the held-out statistics
- every prediction is a model output; the measured column is native
