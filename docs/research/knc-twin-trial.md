# knc-twin trial and validation (S13-06 merged with knc-twin 0.2.0, 2026-11-15)

Engine 0.2.0, profile `card-7120-measured` (hash `ad82d111c1f8...`). No card run, no GCC build. Numbers are
**(pred)** (twin output, status ok) or **(meas)** (native, existing logs); simulated cycles are never measurements.
This replaces the S13-06 branch report (engine 0.1.0). Full tables: `knc-twin/references/validation.md`,
`knc-twin/tests/heldout_native/characterization-run/validation.md`.

## 1. What the twin covers

One KNC core, 1-4 in-order contexts, exact functional execution plus a cycle model (U/V pairing with the
measured exceptions, 2-cycle same-context spacing, AGI 3, L1/L2 line tracking, demand- and store-miss stalls,
no-read stores, gathers, x87 stack with extended precision; optional DTLB, L2 hardware prefetcher and memory
service sub-models). Card and pair scales are analytical (`needs_parameters` when a bandwidth is unknown).
Input: GCC-KNC or GCC 5.1.1 `.s` through one adapter, `knc-twin/scripts/from_gcc_s.py` (whole function, one
loop, or `--loop .L7 --spec` with a conversion report), or JSON records. Validated shapes (median/worst held-out
error): register vector chains 1%/11%, scalar and mask 1%/5%, x87 register chains 1%/3%, L1/L2 dependent loads
2%/14%, L1-resident stores and prefetch pairing 2%/12%. Everything else is an unvalidated estimate.

## 2. Merge decisions

- Branch `twin/merge-s13-06` from main d00f2d68: merged `twin/main-edits` c17216b3 (knc-twin/ content only; its
  two board commits were already on main, so STATUS.md, CURRENT_STATE.md and work/tickets keep main's text),
  then `s13/S13-06` 22944844. Root `.gitignore` unchanged; `knc-twin/.gitignore` (0.2.0) re-includes `*.s`/`*.c`.
- Engine files (`asm.py`, `isa.py`, `functional.py`): 0.2.0 kept. It already has every form S13-06 added
  (`jbe/ja/jnb/...`, `sal`, `vloadunpackl/hps`, `vpackstorel/hps`, now exact rather than timing only), and it
  executes x87 memory forms and `movslq` exactly, so S13-06's rejections of those were dropped (see 10.1).
- One converter: 0.2.0's (function regions, `.rept`, data symbols, audit). Ported from S13-06: `--loop LABEL`
  without a function name, `--spec` (`stream_init`, `addr`/`lines` hints, `contexts`), the conversion report
  (`knc-twin.conversion/1`, every unsupported line with exact text). New for S12-31's `mb.s`: `.skip N, 0x90` in
  code runs as N nops; without `.size`, a function ends at the next `@function` label.
- One harness: `knc-twin/scripts/validate_heldout.py` now also predicts every case in `tests/heldout_native/`
  (`--cases`, `--record` writes `prediction.json`); `tests/trial/knc_trial.py` delegates to it. S12-31 became 7
  function-level variants (input from `tools/s12_31_bench.cpp`, exact expected sum); S12-30 uses 0.2.0's
  `fixtures/batch` kernels for the 4 measured variants (B's per-nonzero loop excerpt `csr.s` removed).
- Trial cases (`tests/trial/make_cases.py`): five expectations changed because the merged engine reads what
  0.1.0 rejected: `agi_gap1` (nop), `gcc_forms_movslq`, `gcc_forms_unpack`, `trial_fsum_L26` (x87) and
  `trial_stencil_L51` (per-context buffers) now carry independently computed inputs and expected outputs and
  pass `functional`; a deliberately wrong expected value fails each one. All prediction.json files were
  re-recorded with the merged engine and profile (the engine changed, no parameter was set from them).

## 3. Runs on the merged tree (Windows Python 3.8 through `tools/run.py`)

| run | result |
|---|---|
| `knc_twin.py selftest` | 95 tests, 0 failures, 0 errors |
| `examples/run_examples.py` | 36 examples, statuses as recorded in `examples/RESULTS.md` (28 ok, 8 intended non-ok) |
| `validate_heldout.py ... --cases --record` | 119 characterization rows (2 unsupported: `vrcp23ps` timing only) + 11 compiled rows + 4 card cases, 2.5 min |
| `tests/trial/knc_trial.py` | 16 cases: 16 conversion ok, 16 functional ok |
| `tests/regress/test_knc_twin.py` | 3 tests OK (selftest, 16 trial cases, 6 held-out predictions unchanged) |

## 4. Consistency with characterization (rows that built the profile; not validation)

Ticks per unit per thread **(meas)** vs cycles per unit per thread **(pred)**, `tests/trial/char.s`:
C9 register u1/u2/u4 at 1 thread 4.02/3.02/2.52 vs 4.016/3.016/2.516, at 2 threads 4.02/3.01/2.51 vs
4.031/3.031/2.531; C7 1 and 2 accumulators at 4 threads 4.13/4.13 vs 4.156/4.156; pair.vector_scalar
2.08/2.10/4.20 vs 2.133/2.141/4.281; pair.vector_vector 4.09/4.08/8.20 vs 4.070/4.078/8.156; agi.gap0
3.11/3.17/4.26 vs 3.133/3.141/4.281; agi.gap1 4.15/4.15/8.27 vs 4.102/4.109/8.156. Largest difference 2.5%
(pair.vector_scalar, 1 thread); the adapter's synthetic end `nop` adds about 0.016 per unit. Nothing tuned.

## 5. Held-out validation (no row here set a parameter)

Error = (pred - meas) / meas, scenario A (TLB modeled, hardware prefetcher off), core cycles; seconds converted
with `card.clock_hz` 1.238 GHz; characterization ticks treated as cycles (TSC 0.5% slower).

| set | threads | n | median abs error | worst abs error (row) |
|---|---:|---:|---:|---|
| characterization | 1 | 62 | 0.9% | 834% memory.store_normal (no prefetcher in scenario A); next 78% spill_reload.rt |
| characterization | 2 | 62 | 0.4% | 631% memory.store_normal; next 116% spill_reload.rt |
| characterization | 4 | 59 | 1.6% | 349% memory.store_normal; next 161% spill_reload.rt |
| compiled code (S12-31 + S12-30) | 1 | 11 | 17.2% | 32.3% S12-31 gas_0 |
| all held-out | 1 / 2 / 4 | 73 / 62 / 59 | 0.9% / 0.4% / 1.6% | as above |

| compiled case | unit | meas | pred | error | twin's limit |
|---|---|---:|---:|---:|---|
| S12-31 gas_0 / mis_44 / inc_0 (window 5) | cycles per 27-product row | 488.9 / 489.2 / 489.0 | 331 | -32% | spacing, x87 dependency |
| S12-31 adj_0 / mid_0 | same | 433.5 / 432.5 | 358 | -17% | same |
| S12-31 mov_adj_0 / mov_split_0 | same | 487.9 / 487.6 | 412 | -16% | same |
| S12-30 donor-off (window 8, small CSR n=13) | cycles per csr_raw call | 8356 | 9518 | +14% | miss stalls, spacing |
| S12-30 knc-switch-off / knc-switch-on | same | 8484 / 8481 | 9527 / 9535 | +12% | same |
| S12-30 knc-switch-off-two-nests | same | 8284 | 9941 | +20% | same |
| STREAM RMW / write NGO, 60 thr (card scale, out of core model) | GB/s | 179.11 / 169.23 | 156.5 / 226.1 | -13% / +34% | profile bandwidth |
| STREAM read, GEMV fp32 (card scale) | GB/s | 147.24 / 125.30 | needs_parameters | - | read bandwidth unknown |

Ranking: 306 of 313 measured characterization orderings reproduced (0.978); S12-31 4 of 10: the card makes
adj_0/mid_0 11% faster than the rest and a dead `movl` free, the twin makes adj/mid 8% slower than gas_0 and
mov_* 15% slower again. S12-30 variants are within 3% of each other on the card (not ranked); the twin puts
two-nests last, the card first. The card cases only test the profile's bandwidth entries (memory bound).

## 6. Open misses (not tuned)

| miss | measured -> predicted | suspected mechanism |
|---|---|---|
| independent store/reload pairs (spill_reload.rt) | 5.09/4.20/4.26 -> 9.06/9.06/11.12 (+78/+116/+161%) | store-to-load wait modeled as an issue blocker; hardware overlaps independent pairs |
| scattered gathers (16 lines) | .lat 184/275/509 -> 124/224/448; .rt 175 -> 112 (-32..-36% at 1 thread) | per-line occupancy 7 fits one line, about 11 for scattered lines |
| four-thread sequential streams (scenario B; calibration row) | memory.load_rt 78 -> 85.5 (+10%) | memory service 20 cycles per line is itself a four-thread figure |
| branch-dense code at four threads (c10.branch.fixed; calibration row) | 17.02 -> 12.38 (-27%) | prefetch-buffer refill after taken branches not modeled |
| S12-31 x87 row loop | -16..-32%, wrong order | per-row cost of `fmull` mem + `faddp` chain, `movslq` cost (unsourced), instruction-order front-end effects |
| S12-30 csr_raw call | +12..+20% | deterministic vs random columns; L1/L2 split of a 32 KiB x |

## 7. Forms still unsupported in real `-O2` output

From 0.2.0's audit (`knc-twin/AUDIT.md`: 455 functions, 317 innermost loops, 295 functional- and 294
timing-complete, 4848 of 5432 loop instructions; not rerun): `call` (region boundary, 3 functions),
`vpmadd231d` (unknown, 2), a `ret` in an out-of-line block inside a loop region (16 loops), one exit redirect
leaving an unreadable `__knc_twin_end` operand (1 loop), TLS `@gottpoff` displacements (4 functions), symbolic
immediates such as `$.LC0` (6), lock prefixes other than `lock add` (1). Timing stops (`missing_parameter`):
`latency.x87_control` (`fldcw`/`fnstcw`/`fnstsw`), `latency.x87_sqrt`, `latency.scalar_idiv`,
`occupancy.scatter_cycles_per_line`, `latency.fence`. Timing only (no exact semantics): `vrcp23ps`.

## 8. ADR-0013 check of `knc-twin/references/`

Intel-authored citations: R01 (SSDG 328207) 18, R27 (ISA manual 327364) 9, SDM 3, R02 (Rahman, Intel/Apress)
29, R17 (Klemm, Intel) 33, R04 (Cornea, Intel) 2; all are facts behind a parameter or rule, and all but 10 give
a page, section, slide or table. Without a locator: R01 for `l1.line_bytes`, `l2.size_bytes` (`parameters.md`
145, 160) and `architecture-model.md` 108; R17 for `l1.line_bytes` and line 88; R27 for `vpu.lanes_f32/f64`,
`vpu.mask_registers`, `vpu.masking`, `vpu.zmm_registers` (207-212); SDM by section only. No long verbatim run
(the Intel PDFs are not in the worktree, so no n-gram comparison). Three short quotations of Intel-authored
text remain in `parameters.md` (generated from the profiles' `source` strings): R02 ch.4, 12 words (line 135);
R04, 10 words (142); R17 slide 12, 8 words (176). R08 (McCalpin, TACC, not Intel) is quoted six times.

## 9. `card-7120-measured` against `docs/research/knc-machine.yaml` (S13-05, on main)

| key (twin / yaml) | twin | yaml | sources |
|---|---|---|---|
| `card.sustained_bandwidth_gbs.read_only` / `stream_sweep2_bandwidth.read`, `stream_read_s11_09_bandwidth` | null | 186.14, 189.06 | twin: none; yaml: S11-06 case 25, S11-09 case 8 |
| `....read_modify_write` / `stream_sweep2_bandwidth.rmw` | 156.5 | 179.39 | S8-17 C12 vs S11-06 sweep 2 |
| `....write_ngo` / `c1_completed_store_bandwidth.ngo`, `stream_sweep2_bandwidth.write` | 226.1 | 204.5, 169.74 | S8-01 C1 worker median vs C1 completed and sweep 2 |
| `....write_normal` / `c1_completed_store_bandwidth.normal` | 83.5 | 82.4 | C1 worker median vs completed |
| `latency.branch_mispredict_penalty` / `branch_mispredict_penalty` | 5 (measured) | null | C10 delta 5.05 vs "C10 does not establish a penalty" |
| `card.barrier_ns` / `openmp_barrier_cost` | tree 6000, counter 27500 | null | S8-10 C11 vs R22/R20 (no transferable constant) |
| `l1.outstanding_demand_misses_per_core` / `r08_l1_misses`, `production_usable_outstanding_lines` | 8, a hard limit | 8 historical (models []), null | R08 vs R08/R06 "not proven on production" |
| `occupancy.gather_cycles_per_line` / `gather_*_endpoints` | 7 per line, linear | 15.10/183.58, 7.02/126.70 endpoints, no interpolation | S6-03 one-line rows vs both endpoints |
| `latency.x87_div` / `x87_dependency.divide` | 38 | 39.25 | twin rounds the .rt 38.24; yaml one-thread .lat |
| `l2.hw_prefetch_depth_lines` / (`r08_l2_prefetched_lines`) | 16 per stream (derived) | no per-stream value; 24 per core historical | fitted to memory.load_rt vs R08 |
| `latency.scalar_alu` / `scalar_add_dependency` | 1 (R17 slide 10) | no latency; 2.08/2.07/4.19 ticks, warns against 1 | documented vs measured |

11 disagreements. Agreements: clock 1.238 GHz, TSC 1.232, 61/60 cores, 4 contexts, issue interval 2, vector
latency 4/6/7, x87 add/mul 3, AGI 3, line 64 B, L1 32 KiB, L2 512 KiB, DTLB 64 pages, L1 3.03, L2 24.42,
memory 356.53, 19.48 ticks per line per core, 16 L2 prefetch streams, no L1 prefetcher, scatter cost unknown.

## 10. For the lead

1. `movslq`/`movsx*` are timed as a 1-cycle V-pairable scalar op without a source (R02 p.34 Table 3-1 lists no
   MOVSX). Every S12-31/S12-30 row depends on it. Accept, or require a native microbenchmark first.
2. The three Intel quotations and ten unlocated citations live in profile `source` strings; rewording them
   changes the profile hash and so every recorded prediction and the frozen batch manifest.
3. `calibration.held_out_validation_cases` in the profile stays 62 (characterization only) for the same reason.
4. Staged native requests in `.work/_shared/S13-06/` carry engine-0.1.0 predictions (saxpy `.L7` 19.875;
   now 13.125/13.25/17.5 **(pred)** at 1/2/4 contexts); re-stage before running them after M4.
