# knc-twin trial and validation (S13-06 merged with knc-twin 0.2.0, 2026-11-15)

Engine 0.2.0, profile `card-7120-measured` (hash `44e9c3bb3ae0...`). No card run, no GCC build. Numbers are
**(pred)** (twin output, status ok) or **(meas)** (native, existing logs); simulated cycles are never measurements.
This replaces the S13-06 branch report (engine 0.1.0). Full tables: `knc-twin/references/validation.md`,
`knc-twin/tests/heldout_native/characterization-run/validation.md`.

## 1. What the twin covers

One KNC core, 1-4 in-order contexts: exact functional execution plus a cycle model (U/V pairing, 2-cycle
same-context spacing, AGI, L1/L2 line tracking, miss stalls, no-read stores, gathers, x87 stack; optional DTLB,
L2 prefetcher and memory-service sub-models); analytical pair and card scales. Input: GCC `.s` through
`knc-twin/scripts/from_gcc_s.py`, or JSON records. Validated shapes (median/worst held-out error): register
vector chains 1/11%, scalar and mask 1/5%, x87 register chains 1/3%, L1/L2 dependent loads 2/14%, L1 stores
and prefetch pairing 2/12%. Everything else is an unvalidated estimate.

## 2. Merge decisions

- Branch `twin/merge-s13-06` from main d00f2d68: `twin/main-edits` c17216b3 (knc-twin/ only; board files keep
  main's text), then `s13/S13-06` 22944844. Root `.gitignore` unchanged; `knc-twin/.gitignore` re-includes `*.s`.
- Engine (`asm.py`, `isa.py`, `functional.py`): 0.2.0 kept; it has every form S13-06 added and executes x87
  memory forms and `movslq` exactly, so S13-06's rejections of those were dropped.
- One converter (0.2.0's `from_gcc_s.py`) with S13-06's `--loop LABEL`, `--spec`, `--contexts` and conversion
  report ported; `.skip N, 0x90` in code runs as nops; without `.size` a function ends at the next one.
- One harness: `validate_heldout.py --cases [--record]` predicts every `tests/heldout_native/` case;
  `knc_trial.py` delegates to it. S12-31: 7 function-level variants with the bench's input; S12-30: the 4
  measured variants as 0.2.0's `fixtures/batch` kernels. Five trial cases that 0.1.0 rejected now carry
  independent inputs and expected outputs; a wrong expected value fails each one.
- Follow-up (lead decisions): labelled assumptions (10), ADR-0013 rewording (8); profile hash ad82d111c1f8 ->
  44e9c3bb3ae0; all prediction.json and the batch manifest re-recorded; no held-out number moved.

## 3. Runs on the merged tree (Windows Python 3.8 through `tools/run.py`, after the follow-up commit)

selftest 95 tests, 0 failures; `examples/run_examples.py` 36 examples (28 ok, 8 intended non-ok); `validate_heldout.py
--cases --record` 119 characterization rows (2 unsupported, `vrcp23ps`) + 11 compiled rows + 4 card cases;
`tests/trial/knc_trial.py` 16 of 16 converted and functional ok; `tests/regress/test_knc_twin.py` 3 tests OK.

## 4. Consistency with characterization (rows that built the profile; not validation)

Ticks per unit per thread **(meas)** vs **(pred)**, `tests/trial/char.s`: C9 register u1/u2/u4 4.02/3.02/2.52 vs
4.016/3.016/2.516 (1 thread); C7 a1/a2 4.13/4.13 vs 4.156/4.156 (4 threads); pair.vector_scalar 2.08/2.10/4.20 vs
2.133/2.141/4.281; pair.vector_vector, agi.gap0, agi.gap1 within 1.4%. Largest difference 2.5%. Nothing tuned.

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

Ranking: 306 of 313 characterization orderings (0.978); S12-31 4 of 10 (card: adj/mid 11% faster, dead `movl`
free; twin: adj/mid 8% slower than gas_0, mov_* 15% slower again). S12-30: the twin puts two-nests last, the
card first (within 3%). The card cases only test the profile's bandwidth entries.

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

From 0.2.0's audit (`knc-twin/AUDIT.md`: 317 innermost loops, 294 timing-complete; not rerun): `call`,
`vpmadd231d`, a `ret` in an out-of-line block inside a loop region (16 loops), one exit redirect leaving an
unreadable `__knc_twin_end` operand, TLS `@gottpoff` displacements, symbolic immediates (`$.LC0`), lock prefixes
other than `lock add`. Timing stops (`missing_parameter`): `latency.x87_control`, `latency.x87_sqrt`,
`latency.scalar_idiv`, `occupancy.scatter_cycles_per_line`, `latency.fence`. Timing only: `vrcp23ps`.

## 8. ADR-0013 check of `knc-twin/references/` (after the rewording)

Intel-authored citations (R01 18, R27 9, SDM 3, R02 29, R17 33, R04 2) are facts behind a parameter or rule.
No Intel quotation remains: the R02 ch.4, R04 slides 9/18 and R17 slide 12 quotations, and three shorter R17
ones (slides 10, 13, 14), are now our own words in the profile `source` strings. Locators added from
`docs/research/knc-references.md`: R01 pp.22-23 (`l1.line_bytes`, `l2.size_bytes`), R01 p.19
(`architecture-model.md` prefetch streams), R17 slides 13-14 (`l1.line_bytes`, `latency.scalar_load_l1`).
Marked "locator missing" (the index gives none): R27 for `vpu.lanes_f32`, `vpu.lanes_f64`, `vpu.mask_registers`,
`vpu.zmm_registers`, `vpu.masking`, and R02 ch.4 for `core.min_issue_gap_same_context` (R01 pp.19, 23-24 added
for the same fact). No long verbatim run (Intel PDFs not in the worktree). R08 (TACC, not Intel) quotes remain.

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

11 disagreements. Agreements: clocks, cores, contexts, issue interval 2, vector latency 4/6/7, x87 add/mul 3,
AGI 3, cache geometry, DTLB 64, L1/L2/memory latency, 19.48 ticks per line, 16 L2 prefetch streams.

## 10. Costs without a source that the compiled rows use (now labelled "evidence E" in the profile)

| parameter or rule | value | used by |
|---|---|---|
| `latency.scalar_extend_extra` (new) | 0 cycles over mov / scalar load | `movslq` index load per nonzero: every S12-31 and S12-30 row |
| `pairing.extend_v_pairs` (new) | true | same |
| `latency.x87_move` | 3 (as the measured x87 add) | `fldz`, `fld %st(i)`, `fstp %st`: S12-30, S12-31 prologue |
| `pairing.u_instruction_can_be_branch` | false | every loop |
| engine rule: x87 loads at the scalar load latency, x87 issues on U only | - | every `fldl`/`fmull` row |

Results that use them list them under `parameters_used` (status assumed) and in `assumptions`. **Defect found**
while listing: x87 arithmetic with a memory operand (`fmull (%rcx,%rax,8)`, `fdivl`) gets its result at the load
latency only; the multiply or divide latency and the divider occupancy are not charged (an `fdivl` chain costs
3 cycles per op, `fldl`+`fdivrp` 38). S12-31 and S12-30 contain such `fmull`s. Not fixed (a timing-rule
change for the lead); fix it before trusting any x87 compiled-code prediction.

## 11. How far to trust it

Good on characterization-style microbenchmarks (median held-out error about 1%), with a caveat: those rows
come from the same harness and instruction families as the calibration rows. On compiled loops it is
currently 12-32% off and gets the order of close variants wrong (S12-31 4 of 10). Use it for bounds,
mechanisms (what binds, which dependency or resource) and differences well above 30%; do not use it to choose
between variants predicted within about 30% of each other.

## 12. Native requests staged in `.work/_shared/S13-06/` (prepare-native, not built, not run)

`s12_31_gas_0`/`adj_0`/`mov_adj_0` (S12-31 ordering miss; pred 346.6/373.6/427.6 per row in an 8-row call),
`sr_alias`/`sr_noalias` (store/reload pairs: issue blocker or overlap; 9.25 vs 4.25 per pair at one thread),
`st_seq`/`st_stride3` (memory.store_normal: is the speed the L2 prefetcher's; 39.1 vs 362.4 per store),
`trial_saxpy_L7`, `trial_stencil_L51`, `c7_reduce_a1`/`a2` (new predictions); index `README.md`; 0.1.0 ones superseded.
