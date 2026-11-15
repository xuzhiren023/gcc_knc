# Capability and acceptance-gap report, knc-twin 0.2

Machine-readable: `python scripts/knc_twin.py capabilities --out <dir>` (`capabilities.json`);
coverage of real compiler output: `AUDIT.md` / `AUDIT.json` (regenerate with
`scripts/from_gcc_s.py ... --audit`); hardware agreement: `references/validation.md`.

## 1. Where native test time goes, and what the twin covers

The regions that consume repeated native testing in gcc_knc are the M4 gate programs (HPCG and
its CSR/SymGS shapes, STREAM, the PolyBench/NPB corpus) and the characterization and gate
microbenchmarks (S6-03/S8 catalog, S12-30 gate variants, S12-31 layout tests). Their hot
regions, as GCC-KNC emits them at `-O2 -march=knc`, are scalar x87 double loops with `movslq`
index loads and software prefetches, x87 float reductions, scalar integer loops, and the
vector microkernels of the catalog.

Audit of real output (`AUDIT.md`, 13 files: seven S12-30 gate variants, the HPCG shapes file,
the CG application, SpMV/SymGS applications, the 364-kernel characterization catalog, the
compiled fixtures):

| what | count | parser reads | ISA known | functional exact | timing complete |
|---|---:|---:|---:|---:|---:|
| functions | 455 | all but 9 (TLS `@gottpoff` operands, symbolic immediates, `rep`/`lock` prefixes other than `rep ret`/`lock add`) | | | |
| innermost loops | 317 | | | 295 | 294 |
| instructions in innermost loops | 5432 | | | | 4848 (89%) |

Every hot loop of the gate kernels (`knc_csr_raw:.L6`, 43 instructions; the SymGS forward and
backward shapes; the CG application's scalar loops) is complete for functional execution and
timing. The incomplete loops are those that call a function, use `fsqrt`, `idiv`, `fldcw/
fnstsw` (latencies unknown in every profile) or `vrcp23ps` (timing-only).

Native time potentially displaced: one S12-30 gate pass spends about 2.5 s of card time per
variant per case shape (five 0.5 s samples) across seven variants and several case shapes, plus
correctness children; its CSR variants are evaluated off-card by `fixtures/batch` in seconds.
The characterization catalog's 119 measured rows (S6-03: three exclusive card windows) are
reproduced off-card to a median error of about 1%; a new microkernel of the validated shapes
no longer needs a card window for a first answer. The M4 gate itself (15-21 h) is not displaced:
its programs run millions of iterations over cold data, outside the validated shapes.

## 2. Implemented

**Inputs**: GCC-KNC and GCC 5.1.1 k1om assembly through `scripts/from_gcc_s.py` (function or
loop regions; `.rept`, data symbols, numeric labels, size suffixes, swizzles, conversions,
masks, x87 forms, `lock add`, `rep ret`); hand-written JSON records; the GAS subset inline.
Nothing is simplified: unsupported instructions are kept and reported.

**Functional (exact)**: scalar integer ALU in 8/16/32/64 bits with flags (add/sub/adc/sbb/
and/or/xor/cmp/test/bt/inc/dec/neg/not/shifts by immediate or cl/imul 2- and 3-operand/idiv/
movsx/movzx/cltq/cltd/cqto/lea/mov/movabs/push/pop/leave/nop), conditional branches and setcc,
mask ops; int32 vector ops and int64 logic; f32/f64 add/sub/subr/mul/max/min and all FMA forms
with one rounding in rn/rd/ru/rz, FTZ/DAZ, signed zeros, infinities, NaN propagation; compares
to mask; blends; conversions dq/udq<->ps, pd->dq/udq, ps<->pd, vrndfxpntps; register swizzles;
broadcasts; up/down conversions (float16/uint8/sint8/uint16/sint16); masked loads/stores;
vloadunpack/vpackstore halves; gather/scatter (dword and qword) with completion masks; vpermd,
vpermf32x4; the x87 stack with extended precision, control word, fld/fst/fild/fistp/fisttp/
fxch/fchs/fabs/fsqrt/fcom/fucom/fcomi/fnstsw/fldcw/fnstcw. Oracles: binary64 double-rounding
for binary32 add/sub/mul, Python binary64 for f64, hand-derived vectors, and GCC-KNC's own
output for the x87 operand conventions.

**Timing (core scale)**: 1-4 in-order contexts, U/V pairing with the documented classes and
the measured exceptions (cmp/jcc pair, nop and jmp do not), 2-cycle same-context spacing,
round-robin picker, register/flag/mask/x87-physical-register scoreboard, 3-cycle AGI,
demand-miss and store-miss stalls, nonblocking software prefetch, 8-entry outstanding-miss
limit, L1 port limit, LRU L1/L2 line tracking, no-read store costs, gather unit occupancy,
x87 multiplier/divider occupancy, L2-prefetch issue rate, fence serialization; optional DTLB,
streaming L2 hardware prefetcher and per-core memory service sub-models.

**Bounds**: trace bounds (issue events, spacing, resources, critical path, memory
concurrency), loop MII (ResMII, RecMII, iteration critical path), exhaustive reorder search.

**Scales**: instruction, region, core simulated; pair and card analytical with explicit
parameters and `needs_parameters` otherwise.

**Workflow**: result classes on every number (`conditional_bound`,
`unvalidated_scenario_estimate`, `calibrated_forecast`), `compare` and `batch` with a frozen
profile hash, native requests for anything the model cannot rank, `prepare-native` /
`import-native` round trip, held-out validation harness.

## 3. Not implemented (explicit)

- Mnemonics outside the table (rejected, never costed); `call`/`ret` are region boundaries;
  symbolic immediates, TLS operands, `rep`/`lock` prefixes beyond the two accepted forms.
- Exact bit patterns of `vrcp23ps`, `vrsqrt23ps`, `vlog2ps`, `vexp223ps`, `vscaleps`
  (timing-only).
- Latencies unknown in every bundled profile: `fsqrt`, `idiv`, `fldcw/fnstcw/fnstsw`, fences,
  scatter occupancy; a region using them stops with `missing_parameter` (native request
  candidates in `references/calibration.md`).
- Second-level TLB and page walks, instruction cache and prefetch-buffer refill, cross-core
  coherence traffic, card-level bandwidth sharing, ring/memory-controller simulation, loaded
  latency growth, frequency/thermal effects; contexts communicating through memory (the
  sequential functional model).
- Pair and card scales are formulas; no pair/card prediction has been compared with a native run.
- End-to-end validation of a compiler-generated region against a native run of that region:
  not yet done (the gate CSR batch is 13% above the measured call on a different random input).

## 4. Memory result classes

Every memory-dependent number is labeled: `bounds` results are conditional bounds under the
model's listed assumptions; `simulate` results are unvalidated scenario estimates unless the
kernel declares a validated shape (five shapes, `references/validation.md`), in which case the
result is a calibrated forecast with that shape's error band; pair/card totals are unvalidated
scenario estimates whose memory term is a conditional bound given the stated bandwidth.

## 5. Known model uncertainties carried as alternatives

`latency.vector_load_l1` 5 derived (R08: 3; overlay with 12); `latency.l2_hit` 24 vs 11
(R17); `l1.accesses_per_cycle` 1 vs 2; `l1.outstanding_demand_misses_per_core` 8 vs 38;
`l2.hw_prefetch_depth_lines` 16 derived (8, 24); `latency.branch_mispredict_penalty` 5 per
branch; `fp.ftz_rule` tiny vs tiny_and_inexact; `occupancy.gather_cycles_per_line` 7 (about 11
for scattered lines); `latency.store_to_load_same_line` 7 (independent pairs over-charged).
