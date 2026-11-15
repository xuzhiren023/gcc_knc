# knc-twin trial and validation (S13-06, 2026-11-15)

Engine 0.1.0, profile `card-7120-measured` v0.1.0 (hash `7ba039d9aac0...`); no card run, no GCC build. Numbers are
**(pred)** (twin output, status ok) or **(meas)** (native, existing log); simulated cycles are never measurements. Reproduce: `python knc-twin/tests/trial/knc_trial.py` (writes `results.json`); host test `tests/regress/test_knc_twin.py`.

**In short.** The twin reproduces its own characterization rows within 2%. That is consistency, because those
rows built the profile. It cannot read GCC-KNC's scalar floating-point code: every measured held-out
kernel we have (S12-31, S12-30) is x87 with memory operands, which the twin rejects. The only held-out
rows inside the model are two card-scale STREAM scenarios, and their predicted bandwidths are off by
-12.6% and +33.6%. Core-scale timing is **not validated yet**. Four native requests that would validate it are staged.

## 1. Selftest, examples, ADR-0013

- `selftest` (repo copy): 72 tests, 2 errors (`test_asm_fixture_matches_records`, `test_fixture_expectations_hold`:
  `asm_file ...\fixtures\saxpy.s not found`): `.gitignore` ignores `*.s`, so the fixture never reached git. Added
  `!/knc-twin/**/*.s` and the file (= `make_fixtures.py` output): 72 tests, 0 failures, 0 errors. `examples/run_examples.py`:
  31 commands; `simulate-saxpy-asm` was `invalid_input` (same file); after the fix 24 ok plus the 7 intended non-ok statuses.
- Intel-document citations in `knc-twin/references/`: R01 (§2.1; p.19), R27 (§2.4 p.39; pp.641-656; several
  rows in `parameters.md` 169-174 without a page), SDM vol.1 (§4.8.3.5, §4.8.3.7, §10.2.3.3; sections only),
  R02 (Rahman, Intel: p.34 Table 3-1, pp.32-33, 55, 56; "ch.3"/"ch.4" without pages), R17 (Klemm, Intel:
  slides 10-14), R04 (Cornea, Intel: slides 9, 18). All are facts, but six are short quotations, which ADR-0013 rules
  out (from `profiles/*.json` `source` strings, copied into `parameters.md`): R02 ch.4 12 words (`parameters.md:119`,
  `knc-common.json:39`), R17 slide 12 6 (`:154`), slide 10 3 (`:120`), slide 13 7 and 2 (`:127`, `:153`), R04 10
  (`:126`). No long verbatim run (longest 12 words); R08 (McCalpin, TACC, not Intel) quotes up to 21. PDFs not
  in the worktree, so not compared. Profiles unchanged without a lead answer; rewording them is a follow-up.

## 2. Converter and the forms real `-O2` output needs

`knc-twin/scripts/from_gcc_s.py file.s --loop .L7 | --function f [--spec] [--contexts N] [--out]`. The body runs
from the label to the last branch back to it. Every line is either converted (ids `L<line>`) or listed with
its line, exact text and reason, and the kernel is written only when nothing is listed. `--function` takes the
only innermost loop; regions that `ret` are not loops. Fixes, each in `fixtures/gcc_o2_forms.s` (cases
`gcc_forms_scalar`, functional ok, `gcc_forms_unpack`, static, `gcc_forms_movslq`, rejected):

- `jbe`/`ja`/`jnb` (and `jna`, `jnbe`, `jnae`): missing from the ISA table; in the trial prologues (saxpy, stencil1) and in `fsum`.
- `movslq`/`movsx*`: rejected with a reason, no sourced cost (R02 p.34 Table 3-1 lists neither MOVSX nor the
  existing `movzx` row). In every S12-30/S12-31 SpMV loop; costing it needs a source or a lead answer.
- `salq`/`sall` -> `shl`; `vloadunpacklps/hps`, `vpackstorelps/hps`: aliases of the `ld/hd` rows, timing only.
- x87 with a memory operand is now rejected with a reason in `asm.py`. Before this, the parser rejected only the
  suffixed mnemonic. A JSON record such as `{"op": "fld", "ops": [mem]}` still silently loses the operand,
  because `kernel.Insn` ignores operands of x87 rows (`kernel.py` x87 branch): **finding for the lead**.

Rejected in the trial loops and held-out kernels, exact text (status `unsupported`):
`fadds\t(%rax)` ... `fadds\t-4(%rax)` (trial.s 164-183, all 16 of `fsum` .L26); `fldl\t(%rdx,%r10,8)`,
`fmull\t(%rcx,%rax,8)` (every S12-31 variant); `fldl\t(%r8,%rdx,8)`, `fmull\t(%rbx,%rax,8)` (S12-30 `.L8`);
8x `fldl\t(%r8,%rsi,8)` + `fmull\t(%rdx)`/`-56(%rdx)`...`-8(%rdx)` (S12-30 `.L6`); `fldl\t(%r8,%r10,8)`,
`fmull\t0(%rbp,%rax,8)` (donor `.L4`); `movslq\t(%r8,%rax,4), %r10` (every S12-31 variant), `movslq\t(%rax), %rsi`,
`4(%rax)`...`-4(%rax)`, `(%r10,%rax,4), %rdx`, `(%rbx,%rax,4), %r10` (S12-30); `nop` (char.s `agi.gap1`). Outside the converted loops: `lock; addl`,
`setne`, `sbbq`, `sall %cl`, `leave`. Parameters a run stopped on: `card.sustained_bandwidth_gbs.read_only`
(`needs_parameters`: STREAM read, GEMV). No `missing_parameter` stops.

## 3. Consistency with characterization (rows that built the profile)

Ticks per unit per thread **(meas)**, docs/research/knc-characterization.md, against core cycles x contexts
**(pred)** (TSC and core clock within 0.5%). Kernels repeat the s8_compute.py / kernels.py bodies (`char.s`).

| Row | Threads | Meas | Pred | Pred/meas | Twin's limit |
|---|---|---:|---:|---:|---|
| C9 register u1 / u2 / u4 | 1 | 4.02 / 3.02 / 2.52 | 4.000 / 3.000 / 2.500 | 0.995 / 0.993 / 0.992 | spacing |
| C9 register u1 / u2 / u4 | 2 | 4.02 / 3.01 / 2.51 | 4.016 / 3.016 / 2.516 | 0.999 / 1.002 / 1.002 | core issue slots |
| C7 1 / 2 accumulators | 4 | 4.13 / 4.13 | 4.125 / 4.125 | 0.999 / 0.999 | issue slots (a1 also dependency) |
| pair.vector_scalar | 1 / 2 / 4 | 2.08 / 2.10 / 4.20 | 2.117 / 2.125 / 4.250 | 1.018 / 1.012 / 1.012 | spacing; slots |
| pair.vector_vector | 1 / 2 / 4 | 4.09 / 4.08 / 8.20 | 4.063 / 4.070 / 8.125 | 0.993 / 0.998 / 0.991 | spacing; slots |
| agi.gap0 | 1 / 2 / 4 | 3.11 / 3.17 / 4.26 | 3.117 / 3.125 / 4.250 | 1.002 / 0.986 / 0.998 | spacing, AGI |
| agi.gap1 | 1 / 2 / 4 | 4.15 / 4.15 / 8.27 | rejected (`nop`) | - | - |

Largest difference: 1.8% (pair.vector_scalar, one thread). No parameter was tuned.

## 4. Trial loops (frozen prefix, `-O2 -march=knc`, `knc-twin/tests/trial/trial.c`; no native time)

Cycles per 16 floats per thread **(pred)**, L1 fixed-level scenario; functional = exact check against host values.

| Loop | Functional | 1 ctx | 2 ctx | 4 ctx | Loop bound (MII / iteration) | Limit at 1 ctx |
|---|---|---:|---:|---:|---|---|
| saxpy `.L7` (n/16 <= 127) | ok | 19.875 | 20.0 | 24.0 | 12, resources; critical path 17 | dependency (load 12 -> FMA) |
| saxpy `.L5` (prefetching) | ok | 19.875 | 20.0 | 25.875 | 24 | spacing, dependency |
| stencil1 `.L51` (no prefetch) | unsupported (unpack timing only) | 44.44 | 44.5 | 49.0 | 128 / 4 vectors, recurrence | dependency |
| fsum `.L26` | conversion unsupported (x87) | - | - | - | - | - |

`compare` `.L7` -> `.L5` at one context: 19.875 both (ratio 1.000; the prefetches pair into idle V slots).
With `overlay-vector-load-3` (documented 3-cycle vector load instead of the measured-chain 12) **(pred)**:
saxpy `.L7` 10.875 (1 ctx) / 16.0 (4 ctx); stencil 20.44 / 29.0. Loops with vector loads move up to 2.2x on
this one parameter. Stencil `.L51`'s RecMII comes from `vloadunpacklps` reading (merging into) `%zmm0`/`%zmm1`,
which the previous unrolled copy wrote. If the hardware merges like the ISA rows, GCC's unroll
serializes the unaligned loads (a compiler lead to measure, not a result). `fsum` stays x87 at `-O2`, which is correct
(no reassociation without fast-math).

## 5. Held-out validation (predicted first; no parameter set from these)

Clock: core cycles = ns x 1.238 GHz (`card.clock_hz`, S6-01 logs; micsmc 1.24 GHz). Cases and measurement
files with their source logs: `knc-twin/tests/heldout_native/`.

| Case | Unit | Pred (status) | Meas | Pred/meas | Twin's limit | In model? |
|---|---|---|---|---:|---|---|
| S12-31 mb `gas_0`, `mis_44`, `inc_0` (w3/w5) | row of 27 | unsupported: `fldl`, `fmull` mem | 393.3-395.2 ns = 487-489 cyc | - | - | no: x87 memory forms |
| S12-31 `adj_0`, `mid_0`, `mov_adj_0`, `mov_split_0` | row | unsupported (same lines) | 349.3-394.1 ns | - | - | no |
| S12-30 small CSR n=13, 32 rows, `knc_csr_raw .L8` | nonzero | unsupported: `fldl`, `fmull` mem | 16.47 ns = 20.39 cyc | - | - | no |
| same, donor `.L4` | nonzero | unsupported | 16.22 ns = 20.09 cyc | - | - | no |
| STREAM RMW, 60 thr (S11-06 case 15) | GB/s | 156.5 ok | 179.11 | 0.874 | memory (parameter) | scenario only |
| STREAM write NGO, 60 thr (case 9) | GB/s | 226.1 ok | 169.23 | 1.336 | memory (parameter) | scenario only |
| STREAM read, 60 thr (case 6) | GB/s | needs_parameters | 147.24 | - | - | no: read bandwidth unknown |
| GEMV fp32, 120 thr (S11-09 case 14) | GB/s | needs_parameters | 125.30 | - | - | no |

Status-ok rows: median |error| 23.1%, worst 33.6% (NGO write). Predicted time over measured time: 1.144 (RMW),
0.748 (NGO). The card model's bandwidths come from other runs (S8-17 C12, 240 threads; S8-01 C1 worker
median). The model has no thread-count or page dependence, so these rows test those parameters more than the
formula. The NGO profile entry's own uncertainty already cites 169.7 from this sweep, so its author saw it,
but it did not set the value. The compute terms come from stand-in one-line loops (`core.s`, labelled) and do not
bind. Core-scale held-out rows inside the model: **none**.

## 6. Where the twin can be trusted now

- Trustworthy, by consistency only: register vector chains, vector+scalar pairing, AGI distance 0 and
  L1-resident reductions on 1-4 contexts, i.e. issue-, spacing- and latency-bound shapes built from
  characterized classes. Relative comparisons (`compare`, unroll and accumulator choices) of such loops.
- Not yet: any loop with vector loads at 1-2 contexts (it hinges on `latency.vector_load_l1` 12 vs 3), unaligned
  `vloadunpack` chains, gathers over many lines (16 lines: 15 + 7 x 15 = 120 **(pred, by parameter)** against 183.58
  ticks **(meas)** `gather_scattered.lat`, one thread), card bandwidth scenarios (above), mispredicted branches
  (penalty 5 is the C10 per-branch delta, not a per-miss penalty).
- Unusable: scalar FP code from GCC-KNC (x87 memory forms) and `movslq` index loads, so SpMV/HPCG/PhiWeather
  scalar kernels; any loop stopped by `nop`, `lock;`, side exits or cl-count shifts. Merge: main's checkout has uncommitted
  twin edits (asm/isa/functional/kernel.py, profiles, untracked `from_gcc_s.py`) that overlap this branch.

## 7. `card-7120-measured` against `docs/research/knc-machine.yaml` (branch s13/S13-05, 6966ce88)

| Item | Twin profile | knc-machine.yaml |
|---|---|---|
| Vector L1 load-to-use | `latency.vector_load_l1` 12 measured (spill/reload chain) | `spill_reload_dependency` 12.11 is a store/load pair only, "not ... folded-load latency"; `l1_load_latency_idle` 3.03 (scalar) |
| Branch mispredict | `latency.branch_mispredict_penalty` 5 measured | `branch_mispredict_penalty` null; `c10_branch_pattern_delta` 5.05 / 10.74 (1 / 4 thr) |
| RMW bandwidth | 156.5 (S8-17 C12) | `stream_sweep2_bandwidth.rmw` 179.39; baseline 179.11 |
| NGO write bandwidth | 226.1 (C1 worker median) | `c1_completed_store_bandwidth.ngo` 204.5; sweep-2 write 169.74 |
| Read-only bandwidth | null | 186.14 (sweep 2), 189.06 (S11-09 read) |
| Outstanding demand misses | 8 per core, applied as a hard limit | `r08_l1_misses` 8 reported; `production_usable_outstanding_lines` null (not proven) |
| Barrier | tree 6.0 us, counter 27.5 us (S8-10 C11) | `openmp_barrier_cost` null (a different quantity) |
| Gather | 15 + 7 per further line | endpoints 15.10 / 183.58 (1 thr), 7.02 / 126.70 per core |

They agree on: clock 1.238 GHz, TSC 1.232, issue interval 2, vector latency 4/6/7, x87 3/3/38 and occupancy 2,
AGI 3, L2 24 (24.42), memory 357 (356.53), 60 usable cores, `memory.lines_per_cycle` 0.0513 (= 1/19.48).

## 8. Native microbenchmarks worth running after M4 (staged, not run)

Staged with `prepare-native` and cross-built with the MPSS toolchain in `.work/_shared/S13-06/<case>/`
(`kernel.S`, `driver.c`, `knc_twin_native`, `request.json`, prediction `result.json`). Run
`./knc_twin_native --reps 1000 --cpus 1` | `1,2` | `1,2,3,4` (one core, exclusive; README in each).

1. `trial_saxpy_L7`: the first core-scale held-out row from real `-O2` output. Pred 19.875 / 20.0 / 24.0 per
   iteration per thread (10.875 / - / 16.0 if the vector load is 3), so it decides `latency.vector_load_l1`.
2. `trial_stencil_L51` (`--no-check`, no expected output): pred 44.44 / 44.5 / 49.0 (20.44 / - / 29.0); unpack merge chain.
3. `c7_reduce_a1`, `c7_reduce_a2` at 1 and 2 threads: pred 4.0 / 2.06 and 4.01 / 2.07, the gain C7 never measured.
4. Not stageable (the twin cannot export x87): chains of `fldl`/`fmull`/`fadds` with memory operands and `faddp` in the knc-char harness; they would open the S12-31/S12-30 rows and all GCC-KNC scalar FP.
