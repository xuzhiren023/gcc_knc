# Capability and acceptance-gap report, knc-twin 0.3

Machine-readable: `python scripts/knc_twin.py capabilities --out <dir>` (`capabilities.json`);
coverage of real compiler output: `AUDIT.md` / `AUDIT.json`; hardware agreement, the decision bar
and the open misses: `references/validation.md`; what to measure next: `knc_twin.py calibration-plan`.

## 1. What changed from 0.2 and why

Two projects declined 0.2 because it was accurate on microbenchmarks but 17 to 32% off on real
loops and ranked the S12-31 variants wrongly. The six causes they named, and what 0.3 does:

| gap named | 0.3 |
|---|---|
| no front end: padding, slow NOP prefixes, alignment invisible | the binary adapter (`scripts/from_binary.py`) converts the function as built, with every instruction's bytes; the engine charges two decode cycles per 66/67/lock/segment/rep prefix after the first (R02 p.56; S12-31 padding rows 0 to 15 bytes all within 3%), executes padding NOPs (never paired), refuses to pair prefixed instructions, charges a core cycle per taken forward branch at several threads, and has an optional instruction-cache scenario. The S12-31 order and padding rankings are reproduced 22 of 22 |
| store path misses (independent store/reload +78 to +161%, stores without prefetcher 8x, scattered gathers -32%, four-thread streams +10%) | a load issues 4 cycles after any store of its context and pairs with a store (spill_reload.rt 4.1 vs 4.2 measured); TLB, L2 hardware prefetcher and memory service are on by default (memory.store_normal 34.6/47.0/85.1 vs 38.3/48.9/79.8); gathers and scatters complete one cache line per execution and re-executions wait for the previous data (gather_scattered.rt 176 vs 175); the four-thread stream stays 7 to 10% high (open) |
| coverage: calls, `vpmadd231d`, returns in loops, TLS, lock prefixes, no timing for sqrt/idiv/scatter/fence/x87 control; loop body only | calls and returns run (callees in the region are executed; others are costed stubs that never get a default cost); `vpmadd231d`, `fxam`, `ftst`, `frndint`, `sahf`, `xchg`, the lock family, `%fs:` TLS, symbolic immediates; sqrt, idiv and x87 control carry labelled Pentium priors (status assumed); fence and scatter still stop with `missing_parameter` (staged microbenchmarks). The whole function, not the loop body, is the unit. Audit: 341 of 357 innermost loops of the S12-30/HPCG/CG/characterization files timing-complete (was 294 of 317); the 16 left need the fence or scatter measurement |
| different inputs than the card run | `init.memory` file blocks bind the run's arrays (SHA-256 recorded); the S12-31 cases use the bench's own data; the S12-30 cases use the gate's generator and report the spread over input instances (2.5 to 6%) because the card's generator state is not reproducible |
| validation on real compiled code, separate from calibration | 105 held-out compiled rows from the binaries and objects that ran on the card (68 S12-31 row-loop variants, 16 HPCG toy kernels, 8 memory-bound HPCG SpMV builds, 16 S12-30 sparse products), 3 calibration rows named; results in `references/validation.md` |
| a bar and a habit | `validate_heldout.py` reports the bar (median error at most 10%, right winner in at least 90% of pairs more than 5% apart, at least 50 loops from at least 5 M4 programs); `calibration-plan` lists the microbenchmarks that settle each assumed value, the open misses and the held-out cases to add; `references/calibration.md` is the habit. The 3120 and 5110P profiles inherit the measured core layer as transferred values and say so |

What the report does not claim: the bar's breadth criterion is not met (the compiled rows come from
HPCG and one sparse microbenchmark family); the twin is a region model, not a system emulator; the
card scale is formulas on measured bandwidths.

## 2. Where native test time goes, and what the twin covers

Regions that consume repeated native testing in gcc_knc: the M4 programs (HPCG and its CSR/SymGS
shapes, STREAM, PolyBench, NPB), the characterization and gate microbenchmarks (S6-03/S8 catalog,
S12-30 gate variants, S12-31 layout tests), and the A/B windows of each tuning ticket. Audit of 13
real files (seven S12-30 gate variants, the HPCG shapes file, the CG application, SpMV/SymGS
applications, the 364-kernel catalog, the compiled fixtures):

| what | count | functional exact | timing complete |
|---|---:|---:|---:|
| functions | 455 | | |
| innermost loops | 357 | 357 | 341 |
| instructions in innermost loops | 7209 | | 5751 (80%) |

The 16 loops left are NPB CG's scatter loops and one `lock`-fenced loop: two unmeasured
parameters (`occupancy.scatter_cycles_per_line`, `latency.fence`), both first in the calibration
plan.

Native time displaced so far: the S12-31 microbench window (68 variants, one card window) is
reproduced to 2 to 4% and its two rankings fully; the S12-31 HPCG toy and the 104-cubed SpMV
runs (two more windows) to 2 to 7% with every ranking right; the S12-30 gate's small cases are 12
to 18% high but ranked right where the builds differ by more than 5%. A new variant of these
shapes gets a first answer off-card in seconds to minutes. The M4 gate itself (15 to 21 hours of
card time) is not displaced: it runs whole programs, outside the region model.

## 3. Implemented

**Inputs**: K1OM object files and linked executables with their `objdump -dr` listing
(`scripts/from_binary.py`: layout, padding, prefixes, calls, returns, constants, TLS, string
addresses); GCC-KNC and GCC 5.1.1 assembly (`scripts/from_gcc_s.py`: function or loop regions,
coverage audit); hand-written JSON records; the GAS subset inline; measured-run arrays as file
blocks. Nothing is simplified: unsupported instructions are kept and reported.

**Functional (exact)**: scalar integer ALU in 8/16/32/64 bits with flags, shifts, imul, idiv,
extensions, lea, moves, push/pop/leave, xchg, the lock family (xadd, cmpxchg, ...), sahf,
conditional branches, setcc, call/ret with the stack, mask ops; int32 vector ops, int64 logic,
`vpmadd231d`; f32/f64 add/sub/subr/mul/max/min and all FMA forms with one rounding in four modes,
FTZ/DAZ, NaN propagation; compares, blends, conversions, swizzles, broadcasts, up/down conversions,
masked loads/stores, vloadunpack/vpackstore, gather/scatter with the hardware's one-line-per-
execution completion, vpermd, vpermf32x4; the x87 stack with extended precision, control word,
loads, stores, integer conversions, fxch, fchs, fabs, fsqrt, fcom/fucom/fcomi, fxam, ftst, frndint,
fnstsw, fldcw, fnstcw. Stubs: memcpy/memmove/memset exact; libm sqrt/fabs/floor/ceil/trunc/
fmin/fmax/copysign exact, other libm functions from the host library and marked approximate.

**Timing (core scale)**: 1-4 in-order contexts, U/V pairing with the measured rules (cmp/jcc
pairs; nop, jmp and x87 issue alone; an instruction with a two-cycle prefix does not pair; a load
and a store may issue together, two loads or two stores may not), 2-cycle same-context spacing,
prefix decode delay, round-robin picker, register/flag/mask/x87 scoreboard, 3-cycle AGI,
store-to-load interlock and forwarding, demand-miss and store-miss stalls, nonblocking software
prefetch, 8-entry outstanding-miss limit, LRU L1/L2 line tracking, DTLB, streaming L2 hardware
prefetcher, per-core memory service, no-read store costs, gather unit occupancy, x87 memory-operand
serialization, x87 multiplier/divider occupancy, L2-prefetch issue rate, fence and locked-instruction
serialization, costed stubs, taken-forward-branch core bubble, optional instruction cache.

**Bounds**: trace bounds, loop MII (ResMII, RecMII, iteration critical path), exhaustive reorder
search. **Scales**: instruction, region, core simulated; pair and card analytical.

**Workflow**: result classes on every number, `compare`/`batch`/`rollup` with a frozen profile
hash, native requests for anything the model cannot rank, `prepare-native`/`import-native`,
`calibration-plan`, the held-out harness with the decision bar.

## 4. Not implemented (explicit)

- Mnemonics outside the table (rejected, never costed); indirect jumps and calls; `rep` string
  instructions; segments other than fs/gs; exact bit patterns of `vrcp23ps`, `vrsqrt23ps`,
  `vlog2ps`, `vexp223ps`, `vscaleps` (timing-only).
- Unknown in every bundled profile: `latency.fence` (lock prefix, mfence), `occupancy.scatter_cycles_per_line`:
  a region using them stops with `missing_parameter`. Priors, not measurements: `fsqrt`, `idiv`,
  x87 control (Pentium timings, labelled), `movslq` cost, x87 pairing with scalar instructions
  other than the jump.
- No operating system, system calls, files, MPI or shared-memory processes; no whole-program runs;
  callees outside the region are stubs. Second-level TLB and page walks, coherence traffic,
  card-level bandwidth sharing, ring/memory-controller simulation, loaded-latency growth beyond
  the memory-service rate, frequency/thermal effects, pseudo-LRU replacement.
- Pair and card scales are formulas on measured bandwidths; no pair/card prediction has been
  compared with a native run of a parallel program.
- The decision bar's breadth: compiled rows from HPCG and one sparse microbenchmark family, not
  from five M4 programs; the 3120 and 5110P have no measurement of their own.

## 5. Result classes

`bounds` results are conditional bounds under the model's listed assumptions; `simulate` results
are unvalidated scenario estimates unless the kernel declares a validated shape
(`references/validation.md`), in which case the result is a calibrated forecast with that shape's
error band; a result with stub calls is never a calibrated forecast; pair/card totals and roll-ups
over unvalidated regions are unvalidated scenario estimates.

## 6. Known model uncertainties carried as alternatives

`latency.vector_load_l1` 5 derived (R08: 3; overlay with 12); `latency.l2_hit` 24 vs 11 (R17);
`l1.outstanding_demand_misses_per_core` 8 vs 38; `l2.hw_prefetch_depth_lines` 16 derived;
`latency.branch_mispredict_penalty` 5 per branch (the four-thread random row is 34% under);
`store.load_after_store_interlock_cycles` 4 (one-thread row says 5); `latency.x87_load` 3 and
`latency.x87_mem_operand_load` 1 (only the sum 7 is measured; the row loops are 3% slow);
`frontend.taken_branch_core_bubble_cycles` 1 for forward transfers (one four-thread row);
`latency.memory` 328 derived from 357 minus one TLB miss; `fp.ftz_rule` tiny vs tiny_and_inexact.
