# Held-out validation against the characterization microbenchmarks

Generated 2026-11-15T19:46:24Z. Profile card-7120-measured (hash f28472ab6793...). line_tracking cold memory, TLB modeled, hardware prefetcher off, memory service modeled

## Error statistics (scenario A, per thread count)

| rows | n | median abs err % | worst abs err % | within 15% | within 30% | mean signed err % |
|---|---:|---:|---:|---:|---:|---:|
| calibration_threads_1 | 42 | 0.7 | 857.8 | 36 | 38 | 25.4 |
| calibration_threads_2 | 41 | 2.0 | 648.7 | 35 | 37 | 16.8 |
| calibration_threads_4 | 42 | 1.8 | 359.6 | 37 | 39 | 7.1 |
| held_out_threads_1 | 71 | 0.9 | 243.8 | 53 | 61 | 0.1 |
| held_out_threads_2 | 70 | 0.7 | 244.7 | 52 | 57 | -1.5 |
| held_out_threads_4 | 67 | 1.8 | 129.6 | 55 | 57 | -2.2 |

## Ranking reliability

264 of 299 measured pairwise orderings (within groups, measured difference > 3%) reproduced: reliability 0.883.

| group | agree | pairs | disagreements (a, b: measured -> predicted) |
|---|---:|---:|---|
| agi_gap@threads_1 | 10 | 10 |  |
| agi_gap@threads_2 | 9 | 10 | agi.gap1 vs agi.gap2: 4.15/6.16 -> 4.12/4.12 |
| agi_gap@threads_4 | 10 | 10 |  |
| branches@threads_1 | 1 | 1 |  |
| branches@threads_4 | 1 | 1 |  |
| c9_memory_unroll@threads_1 | 3 | 3 |  |
| c9_memory_unroll@threads_2 | 3 | 3 |  |
| c9_register_unroll@threads_1 | 3 | 3 |  |
| c9_register_unroll@threads_2 | 3 | 3 |  |
| gathers@threads_1 | 1 | 1 |  |
| gathers@threads_2 | 1 | 1 |  |
| gathers@threads_4 | 1 | 1 |  |
| latency_rows@threads_1 | 21 | 21 |  |
| latency_rows@threads_2 | 21 | 21 |  |
| latency_rows@threads_4 | 18 | 18 |  |
| load_levels_lat@threads_1 | 3 | 3 |  |
| load_levels_lat@threads_2 | 3 | 3 |  |
| load_levels_lat@threads_4 | 3 | 3 |  |
| load_levels_rt@threads_1 | 3 | 3 |  |
| load_levels_rt@threads_2 | 3 | 3 |  |
| load_levels_rt@threads_4 | 3 | 3 |  |
| memory_forms@threads_1 | 10 | 12 | spill_reload.lat vs unpack.rt: 12.11/4.09 -> 6.03/14.06; unpack.rt vs spill_reload.rt: 4.09/5.09 -> 14.06/5.06 |
| memory_forms@threads_2 | 12 | 14 | masked_load.lat vs spill_reload.lat: 12.17/12.98 -> 15.00/6.06; spill_reload.lat vs unpack.rt: 12.98/4.08 -> 6.06/14.06 |
| memory_forms@threads_4 | 13 | 14 | spill_reload.lat vs unpack.rt: 13.14/8.14 -> 8.12/14.06 |
| pairing@threads_1 | 2 | 2 |  |
| pairing@threads_2 | 2 | 2 |  |
| pairing@threads_4 | 2 | 2 |  |
| prefetch_pairing@threads_1 | 7 | 7 |  |
| prefetch_pairing@threads_2 | 9 | 9 |  |
| prefetch_pairing@threads_4 | 8 | 8 |  |
| stores@threads_1 | 5 | 14 | l1.store_normal vs l1.store_stream: 2.20/27.19 -> 2.22/2.22; l1.store_normal vs l2.store_stream: 2.20/27.49 -> 2.22/2.22; l1.store_normal vs memory.store_stream: 2.20/157.12 -> 2.22/2.22; l1.store_stream vs l2.store_normal: 27.19/23.39 -> 2.22/3.00; l1.store_stream vs memory.store_stream: 27.19/157.12 -> 2.22/2.22; l2.store_normal vs l2.store_stream: 23.39/27.49 -> 3.00/2.22; l2.store_normal vs memory.store_stream: 23.39/157.12 -> 3.00/2.22; l2.store_stream vs memory.store_stream: 27.49/157.12 -> 2.22/2.22; memory.store_normal vs memory.store_stream: 38.28/157.12 -> 44.94/2.22 |
| stores@threads_2 | 5 | 14 | l1.store_normal vs l1.store_stream: 2.27/30.09 -> 2.25/2.22; l1.store_normal vs l2.store_stream: 2.27/30.22 -> 2.25/2.22; l1.store_normal vs memory.store_stream: 2.27/158.07 -> 2.25/2.22; l1.store_stream vs l2.store_normal: 30.09/23.66 -> 2.22/6.00; l1.store_stream vs memory.store_stream: 30.09/158.07 -> 2.22/2.22; l2.store_normal vs l2.store_stream: 23.66/30.22 -> 6.00/2.22; l2.store_normal vs memory.store_stream: 23.66/158.07 -> 6.00/2.22; l2.store_stream vs memory.store_stream: 30.22/158.07 -> 2.22/2.22; memory.store_normal vs memory.store_stream: 48.93/158.07 -> 89.70/2.22 |
| stores@threads_4 | 5 | 14 | l1.store_normal vs l1.store_stream: 4.38/36.16 -> 4.38/4.38; l1.store_normal vs l2.store_stream: 4.38/36.29 -> 4.38/4.38; l1.store_normal vs memory.store_stream: 4.38/160.26 -> 4.38/4.38; l1.store_stream vs l2.store_normal: 36.16/25.04 -> 4.38/12.00; l1.store_stream vs memory.store_stream: 36.16/160.26 -> 4.38/4.38; l2.store_normal vs l2.store_stream: 25.04/36.29 -> 12.00/4.38; l2.store_normal vs memory.store_stream: 25.04/160.26 -> 12.00/4.38; l2.store_stream vs memory.store_stream: 36.29/160.26 -> 4.38/4.38; memory.store_normal vs memory.store_stream: 79.83/160.26 -> 183.25/4.38 |
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
| vpermd.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.06 | -1/-1/-2 |  | miss_stall, dependency |
| vpermd.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| vpermf32x4.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.06 | -1/-1/-2 |  | miss_stall, dependency |
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
| swizzle_cdab.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.06 | -1/-1/-2 |  | miss_stall, dependency |
| swizzle_cdab.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| swizzle_badc.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.06 | -1/-1/-2 |  | miss_stall, dependency |
| swizzle_badc.rt | held_out | ok | 2.07/2.07/4.19 | 2.06/2.06/4.12 | -0/-0/-2 |  | miss_stall, spacing |
| swizzle_dacb.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.06 | -1/-1/-2 |  | miss_stall, dependency |
| swizzle_dacb.rt | held_out | ok | 2.07/2.07/4.19 | 2.06/2.06/4.12 | -0/-0/-2 |  | miss_stall, spacing |
| swizzle_aaaa.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.06 | -1/-1/-2 |  | miss_stall, dependency |
| swizzle_aaaa.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| swizzle_bbbb.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.06 | -1/-1/-2 |  | miss_stall, dependency |
| swizzle_bbbb.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| swizzle_cccc.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.06 | -1/-1/-2 |  | miss_stall, dependency |
| swizzle_cccc.rt | held_out | ok | 2.08/2.07/4.19 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| swizzle_dddd.lat | calibration | ok | 6.04/6.09/6.16 | 6.00/6.00/6.06 | -1/-1/-2 |  | miss_stall, dependency |
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
| vcvtfxpntpd2dq.lat | calibration | ok | 7.04/7.11/7.18 | 7.00/7.00/7.03 | -1/-2/-2 |  | miss_stall, dependency |
| vcvtfxpntpd2dq.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| vcvtfxpntpd2udq.lat | calibration | ok | 7.05/7.11/7.18 | 7.00/7.00/7.03 | -1/-2/-2 |  | miss_stall, dependency |
| vcvtfxpntpd2udq.rt | held_out | ok | 2.08/2.07/4.20 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| x87_add.lat | calibration | ok | 3.02/3.08/4.13 | 3.03/3.03/4.12 | +0/-2/-0 |  | miss_stall, spacing |
| x87_add.rt | held_out | ok | 2.08/2.07/4.13 | 2.06/2.06/4.12 | -1/-0/-0 |  | miss_stall, spacing |
| x87_mul.lat | calibration | ok | 3.02/4.08/8.02 | 3.03/4.03/8.00 | +0/-1/-0 |  | miss_stall, spacing |
| x87_mul.rt | calibration | ok | 2.08/4.02/8.02 | 2.06/4.03/8.00 | -1/+0/-0 |  | miss_stall, spacing |
| x87_div.lat | calibration | ok | 39.25/76.30/151.79 | 38.00/76.00/152.00 | -3/-0/+0 |  | dependency, miss_stall |
| x87_div.rt | calibration | ok | 38.24/76.27/151.76 | 38.00/76.00/152.00 | -1/-0/+0 |  | resource, miss_stall |
| masked_load.lat | calibration | ok | 12.11/12.17/13.14 | 15.00/15.00/15.00 | +24/+23/+14 |  | dependency, miss_stall |
| masked_store.lat | held_out | ok | 12.11/12.17/13.17 | 15.00/15.00/15.00 | +24/+23/+14 |  | dependency, miss_stall |
| unpack.lat | held_out | ok | 12.11/16.79/24.40 | 28.00/28.00/28.03 | +131/+67/+15 |  | dependency, miss_stall |
| convert_up.lat | calibration | ok | 12.11/12.18/13.18 | 15.00/15.00/15.00 | +24/+23/+14 |  | dependency, miss_stall |
| convert_down.lat | held_out | ok | 12.11/12.95/13.14 | 15.00/15.00/15.00 | +24/+16/+14 |  | dependency, miss_stall |
| spill_reload.lat | calibration | ok | 12.11/12.98/13.14 | 6.03/6.06/8.12 | -50/-53/-38 |  | miss_stall, dependency |
| masked_load.rt | held_out | ok | 2.08/2.37/4.13 | 2.06/2.06/4.12 | -1/-13/-0 |  | miss_stall, spacing |
| masked_store.rt | held_out | ok | 2.08/2.08/4.13 | 2.06/2.06/4.12 | -1/-1/-0 |  | miss_stall, spacing |
| unpack.rt | held_out | ok | 4.09/4.08/8.14 | 14.06/14.06/14.06 | +244/+245/+73 |  | miss_stall, dependency |
| convert_up.rt | held_out | ok | 2.08/2.07/4.13 | 2.06/2.06/4.12 | -1/-0/-0 |  | miss_stall, spacing |
| convert_down.rt | held_out | ok | 2.08/2.07/4.13 | 2.06/2.06/4.12 | -1/-0/-0 |  | miss_stall, spacing |
| spill_reload.rt | held_out | ok | 5.09/4.20/4.26 | 5.06/5.09/8.12 | -1/+21/+91 |  | miss_stall, dependency |
| masked_load_sparse.lat | held_out | ok | 12.11/12.17/13.15 | 15.00/15.00/15.00 | +24/+23/+14 |  | dependency, miss_stall |
| masked_store_sparse.lat | held_out | ok | 12.11/12.18/13.14 | 15.00/15.00/15.00 | +24/+23/+14 |  | dependency, miss_stall |
| masked_load_sparse.rt | held_out | ok | 2.08/2.07/4.13 | 2.06/2.06/4.12 | -1/-0/-0 |  | miss_stall, spacing |
| masked_store_sparse.rt | held_out | ok | 2.08/2.07/4.13 | 2.06/2.06/4.12 | -1/-0/-0 |  | miss_stall, spacing |
| gather_all.lat | calibration | ok | 15.10/18.27/29.17 | 21.12/26.16/36.50 | +40/+43/+25 |  | dependency, miss_stall |
| gather_all.rt | calibration | ok | 7.08/14.09/28.10 | 19.12/22.19/36.25 | +170/+57/+29 |  | miss_stall, dependency |
| gather_scattered.lat | held_out | budget_exhausted: python time budget exhausted after 1497088 simulated cycles (partial,  | 183.58/275.10/509.15 | -/-/- | -/-/- |  |  |
| gather_scattered.rt | held_out | budget_exhausted: python time budget exhausted after 1456128 simulated cycles (partial,  | 175.14/259.58/506.78 | -/-/- | -/-/- |  |  |
| pair.vector_scalar | held_out | ok | 2.08/2.10/4.20 | 2.12/2.12/4.25 | +2/+1/+1 |  | miss_stall, spacing |
| pair.vector_vector | held_out | ok | 4.09/4.08/8.20 | 4.06/4.06/8.12 | -1/-0/-1 |  | miss_stall, spacing |
| pair.scalar_scalar | held_out | ok | 2.08/2.07/4.19 | 2.12/2.12/4.25 | +2/+3/+1 |  | miss_stall, spacing |
| agi.gap0 | calibration | ok | 3.11/3.17/4.26 | 3.12/3.16/4.25 | +0/-0/-0 |  | miss_stall, spacing |
| agi.gap1 | held_out | ok | 4.15/4.15/8.27 | 4.09/4.12/6.25 | -1/-1/-24 |  | miss_stall, spacing |
| agi.gap2 | held_out | ok | 6.16/6.16/12.27 | 4.12/4.12/8.25 | -33/-33/-33 |  | miss_stall, spacing |
| agi.gap3 | held_out | ok | 8.18/8.16/16.28 | 5.12/5.12/10.25 | -37/-37/-37 |  | miss_stall, spacing |
| agi.gap4 | held_out | ok | 10.19/10.18/20.29 | 6.12/6.12/12.25 | -40/-40/-40 |  | miss_stall, spacing |
| l1.load_lat | calibration | ok | 3.03/3.08/4.13 | 3.03/3.06/4.12 | +0/-1/-0 | 3.03/3.03/3.03 | miss_stall, spacing |
| l1.load_rt | held_out | ok | 2.20/2.27/4.38 | 2.22/2.25/4.38 | +1/-1/-0 | 2.22/2.25/4.01 | miss_stall, spacing |
| l1.store_normal | held_out | ok | 2.20/2.27/4.38 | 2.22/2.25/4.38 | +1/-1/-0 | 2.22/2.25/4.38 | outstanding_limit, miss_stall |
| l1.store_stream | held_out | ok | 27.19/30.09/36.16 | 2.22/2.22/4.38 | -92/-93/-88 | 2.22/2.22/4.38 | miss_stall, spacing |
| l2.load_lat | calibration | ok | 24.42/24.93/25.68 | 24.12/24.12/24.12 | -1/-3/-6 | 24.12/24.35/23.45 | miss_stall, spacing |
| l2.load_rt | held_out | ok | 23.38/23.51/23.85 | 24.28/24.28/24.28 | +4/+3/+2 | 24.28/24.31/24.34 | miss_stall, spacing |
| l2.store_normal | held_out | ok | 23.39/23.66/25.04 | 3.00/6.00/12.00 | -87/-75/-52 | 3.00/6.00/12.00 | outstanding_limit, spacing |
| l2.store_stream | held_out | ok | 27.49/30.22/36.29 | 2.22/2.22/4.38 | -92/-93/-88 | 2.22/2.22/4.38 | spacing, miss_stall |
| memory.load_lat | calibration | ok | 356.53/357.96/365.76 | 386.12/385.67/386.50 | +8/+8/+6 | 386.12/385.67/387.61 | miss_stall, spacing |
| memory.load_rt | calibration | ok | 37.35/47.78/77.92 | 357.73/357.73/358.11 | +858/+649/+360 | 84.25/84.38/88.28 | miss_stall, spacing |
| memory.store_normal | held_out | ok | 38.28/48.93/79.83 | 44.94/89.70/183.25 | +17/+83/+130 | 44.94/89.70/183.25 | outstanding_limit, miss_stall |
| memory.store_stream | held_out | ok | 157.12/158.07/160.26 | 2.22/2.22/4.38 | -99/-99/-97 | 2.22/2.22/4.38 | miss_stall, spacing |
| c2.vector | held_out | ok | 2.08/2.07/4.19 | 2.06/2.06/4.12 | -1/-0/-2 |  | miss_stall, spacing |
| c2.prefetch0 | held_out | ok | 1.07/1.09/2.13 | 1.12/1.12/2.25 | +5/+3/+6 |  | miss_stall, outstanding_limit |
| c2.prefetch1 | calibration | ok | 1.92/4.52/9.01 | 2.06/4.00/8.00 | +7/-12/-11 |  | miss_stall, outstanding_limit |
| c2.vector_prefetch0 | held_out | ok | 2.08/2.20/4.13 | 2.12/2.12/4.25 | +2/-3/+3 |  | miss_stall, outstanding_limit |
| c2.vector_prefetch1 | held_out | ok | 2.09/4.52/9.02 | 2.12/4.03/8.02 | +2/-11/-11 |  | miss_stall, outstanding_limit |
| c7.reduce.a1 | held_out | ok | -/-/4.13 | 4.00/4.00/4.12 | -/-/-0 |  | miss_stall, dependency |
| c7.reduce.a2 | held_out | ok | -/-/4.13 | 2.06/2.06/4.12 | -/-/-0 |  | miss_stall, spacing |
| c9.vector.u1 | held_out | ok | 4.02/4.02/- | 4.00/4.00/8.00 | -0/-0/- |  | miss_stall, spacing |
| c9.vector.u2 | held_out | ok | 3.02/3.01/- | 3.00/3.00/6.00 | -1/-0/- |  | miss_stall, spacing |
| c9.vector.u4 | held_out | ok | 2.52/2.51/- | 2.50/2.50/5.00 | -1/-0/- |  | miss_stall, spacing |
| c9.memory.u1 | held_out | ok | 11.07/13.08/- | 8.00/8.00/12.00 | -28/-39/- |  | miss_stall, spacing |
| c9.memory.u2 | held_out | ok | 8.56/12.03/- | 7.00/7.00/10.00 | -18/-42/- |  | miss_stall, spacing |
| c9.memory.u4 | held_out | ok | 8.30/11.01/- | 6.50/6.50/9.00 | -22/-41/- |  | miss_stall, spacing |
| c10.branch.fixed | held_out | ok | 6.22/-/17.02 | 9.77/9.78/13.34 | +57/-/-22 |  | miss_stall, spacing |
| c10.branch.random | calibration | ok | 11.27/-/27.76 | 12.19/12.80/14.42 | +8/-/-48 |  | miss_stall, spacing |

- predicted = slope of completion cycles between 2 and 4 rounds, divided by 32 units per round; TSC ticks and core cycles are treated as equal (0.5% difference on this card)
- the kernel catalog was regenerated from tests/bench/knc-char/kernels.py; S8-07 additions shift kernel indices but the measured S6-03 bodies are the same templates
- calibration rows set a parameter of the profile and are excluded from the held-out statistics
- every prediction is a model output; the measured column is native
