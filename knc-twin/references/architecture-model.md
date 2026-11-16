# The core model

Target: one Knights Corner core (K1OM, IMCI). Not Knights Landing, not AVX-512, not an
out-of-order x86. Source ids (R01, R02, ...) are listed in `sources.md`; measured values
come from the gcc_knc characterization runs named in `profiles/card-7120-measured.json`
and are checked row by row in `validation.md`.

## Contexts and issue

- Four hardware contexts; the kernel activates 1-4 of them (`streams`). Each context is a
  strictly in-order instruction stream (R01 §2.1, R17 slide 10).
- Per cycle the core issues at most two instructions, both from the same context: the first on
  the U pipe, the second on the V pipe if the pairing rules allow (R01 §2.1, R02 p.34).
- A context cannot issue in consecutive cycles: after an issue event its next issue is at least
  `core.min_issue_gap_same_context` (2) cycles later (R02 ch.4, R17 slide 11; measured 2.08
  ticks per independent op at one thread). Two or more contexts can fill every cycle.
- Context selection: among contexts that are eligible this cycle (not spaced out, not stalled,
  head instruction's operands ready, resources free), the one that issued least recently wins;
  ties go to the lower context number (round-robin picker, R02 ch.4, R17 slide 10). A context
  that is stalled never issues out of order and never lets later instructions bypass the head.
- Front end (0.3.0). With code layout (records carrying `encoding` from `scripts/from_binary.py`):
  an instruction with k two-cycle prefixes (66, 67, lock, segment, rep: R02 p.56) cannot issue
  before `frontend.slow_prefix_decode_cycles` x k cycles after its context's previous issue, so
  one such prefix is hidden by the two-cycle spacing and each further one costs two cycles
  (S12-31 padding rows: the assembler's 10- to 15-byte NOPs with 66/2e prefixes); such an
  instruction does not pair. Alignment padding executes as the NOPs it is. The loop-top offset
  and 16- or 64-byte boundary crossings cost nothing (S12-31 mis_4..mis_60 within 0.45 ns per
  row). Without layout these effects are not modeled and the result says so.
- Each taken branch costs the core `frontend.taken_branch_core_bubble_cycles` (1, derived from
  the S8-01 C10 fixed-direction row at four threads: 17.02 vs 12.4 without it) for the
  prefetch-buffer refill (R02 ch.4); at one thread the same-context spacing hides it.
- Instruction cache: assumed resident (hot region). `scenario.frontend.icache` `cold_l2` or
  `cold_memory` adds a 32 KiB 8-way instruction cache whose first touch of each code line stalls
  the context for the data-side L2 or memory latency (assumed equal for code).

## Pairing (V pipe)

- V-eligible classes (`pairing.v_eligible_classes`, from R02 Table 3-1 p.34): scalar ALU and
  read-modify-write, scalar load/store, branch, mask ops, vector stores, packstores, prefetches.
  Vector arithmetic, vector loads, gathers, scatters, x87 and fences are U-only. Two vector
  arithmetic instructions never pair (S6-03 pair.vector_vector).
- A pair must have no register, address, mask or flag dependency between its members, except
  `cmp/jcc` and `test/jcc` (R02 p.56). `dec/jnz` and `sub/jnz` are not paired (not documented;
  native request candidate).
- A `nop` takes no partner on either side (S6-03 agi.gap1-4; S12-31 one_15: fifteen
  single-byte NOPs cost one issue each); an unconditional `jmp` does not issue in the V slot
  (S8-01 C10 fixed row: cmp/je, add, jmp are three issue events). Conditional branches do pair as
  `cmp/jcc`.
- An x87 instruction issues alone (`pairing.x87_pairs_with_scalar` false): S12-31 measured
  `fmull; add; cmp; faddp; jg` at five issues per iteration and `fmull; faddp; add; cmp; jg` at
  four (44.8 ns per 27-product row, one issue per iteration); the compare must be the first of
  its pair (an independent instruction before it takes it as partner, mov_adj_0). Whether other
  scalar instructions pair with x87 is not measured (calibration-plan x87-pairing).
- A load and a store can issue together (`pairing.load_store_pair`, derived from spill_reload.rt
  at four threads: 1.07 cycles per store plus reload); the L1 port limit counts loads.
- Encoding rules (R02 p.56: at most 8 bytes, not displacement and immediate together, no
  MVEX/VEX form with a 32-bit displacement) apply when a record carries `encoding` hints;
  otherwise the record is assumed pairable and the assumption is recorded.
- The instruction after a branch is not paired with it (model assumption).

## Latencies and resources

- A register result is ready `latency` cycles after issue; a dependent instruction may issue in
  that cycle. Classes: scalar ALU 1, mask 1 (assumed), vector arithmetic 4, long vector
  (permute/swizzle/vrcp23ps) 6, pd->dq and ps<->pd conversions 7, scalar imul 10 (R02 p.56),
  x87 add/mul 3, x87 div 38 (occupancy 38), x87 mul occupancy 2, x87 move/compare 3 (assumed).
  A swizzled register source raises a vector arithmetic instruction to the long latency
  (S6-03 swizzle rows).
- Loads: result ready after the level latency: L1 scalar 3 (measured), L1 plain vector 5
  (derived from the spill/reload chain; R08 documents 3; overlay with 12 provided), merge or
  converting vector forms the same 5 (the masked and converting chains measure the same 12 as
  the plain spill/reload chain), L2 24, memory 357 (one thread, idle); beyond L1 the difference
  between the form's L1 latency and the scalar L1 latency is added. x87 loads deliver at the
  scalar load latency.
- A vector arithmetic instruction with a memory source ("folded load") pays no extra latency on
  an L1 hit (S6-03 C9) and stalls like a load otherwise.
- Stores and loads (0.3.0): a load may issue `store.load_after_store_interlock_cycles` (4,
  derived from spill_reload.rt at two and four threads and the C9 memory chains at one thread)
  after any store of its context; a load of a line stored recently gets the stored data
  `latency.store_to_load_same_line` (7) cycles after the store plus the load latency, without
  blocking issue. Open: spill_reload.rt at one thread is 5.09 (one cycle more), and the
  two-thread C9 chains 12.0/11.0 against 8 to 9 modeled.
- Address-generation interlock: a register written at cycle t can be used as an address from
  t + 3 (R01 p.19, R17 slide 13; S6-03 agi.gap0).
- L1 data port: `l1.accesses_per_cycle` (1, R17 slide 13; alternative 2) loads+stores per cycle.
- Gathers and scatters complete one cache line per execution (R05 section V.D): the lanes that
  share the line of the lowest pending lane are done and the others stay in the mask, so the
  `jknzd` loop the compiler emits re-executes the instruction once per line. Each execution
  occupies the gather unit `occupancy.gather_cycles_per_line` (7) cycles; its data is ready
  after `latency.gather_first_line` (11, derived from gather_all.lat minus the index operation)
  and a re-execution waits for it because the lanes merge into the destination, which gives the
  measured 175 cycles for sixteen lines (16 x 11, gather_scattered.rt). The completion mask is
  readable after `latency.gather_mask_cycles` (2). `numerical_policy.gather_completion` `all`
  restores one-shot completion for hand-written kernels. Scatters need
  `occupancy.scatter_cycles_per_line`, unknown in every bundled profile.
- `vprefetch1/2/nta` issue at most one per `occupancy.vprefetch_l2_core_cycles` (2) core cycles
  (S8-01 C2 measured 2.25). `vprefetch0` costs only its issue slot.
- No-read stores (`vmovnr*`) stall their context `store.nr_stall_cycles_resident` (27) cycles
  when the line is in L1 or L2 and `store.nr_stall_cycles_memory` (157) otherwise, and occupy a
  shared store path for `store.nr_occupancy_core_cycles` (9) (S6-03 store_stream rows). A
  non-resident line written by a no-read store is left in L2 (assumed).
- `fsqrt` (70), `idiv`/`div` (46) and `fldcw/fnstcw/fnstsw` (7) carry labelled priors from the
  published Pentium (P5) instruction timings in `knc-common` (status assumed; the P5 figures that
  could be checked on the card agree: FDIV 39, IMUL 10); the calibration plan stages the
  microbenchmarks that replace them. Fences and locked read-modify-write instructions (`lock
  add/sub/and/or/xor/inc/dec/xadd/cmpxchg/xchg`) need `latency.fence`, unknown in every bundled
  profile: a region using them stops with `missing_parameter`.
- Calls and returns (0.3.0). A `call` to a label in the region pushes the return address and
  continues there; `ret` pops it and continues at the return site (or ends the stream at the
  entry sentinel when the kernel's `entry` is `function`). A call to a callee outside the region
  needs a costed stub in the kernel's `calls`: the context stalls for the declared cycles (plus
  `cycles_per_byte` for mem* models), the callee's own cache and resource use is not modeled,
  and a result with stub calls is never a calibrated forecast. A direct call is never
  mispredicted; a `ret` is predicted when it returns where it returned last time (assumed).

## x87

The x87 stack is modeled exactly: eight physical registers with TOP, push/pop, `fxch`, the
control word's rounding and precision control, extended-precision arithmetic with one rounding,
`fld/fst` of binary32/64/80 and integers, `fistp/fisttp`, `fsqrt`, `fcom*` condition codes and
`fnstsw`. GAS AT&T operand conventions are followed (`fsub %st(1),%st` = st0-st1;
`fsubrp %st,%st(1)` = st1-st0; `fsubrl m` = m-st0), checked against GCC-KNC output
(`fixtures/gcc/x87test.s`). The functional trace gives the timing engine the physical registers
each instruction reads and writes, so x87 chains are scoreboarded like vector chains; a static
trace falls back to serializing x87 instructions. x87 instructions issue on U only and alone.
An x87 instruction with a memory operand holds its context until its result is complete
(`x87.mem_operand_serializes`, derived from the S12-31 loop-body orders): `fldl m` delivers
after `latency.x87_load` (3) and `fmull m` after `latency.x87_mem_operand_load` (1) plus the
multiply (3); only the sum of the two latencies is measured (7 cycles per `fldl; fmull` pair).
`fxam`, `ftst`, `frndint` are exact; `fsqrt` is correctly rounded in the control word's precision.

## Memory

- Demand load misses stall the issuing context until the data arrives; other contexts continue
  (R08; R02 ch.4). Store misses stall too on this card (S6-03 l2.store_normal 23.4 per store;
  `l1.store_miss_stalls_context`, with R08's opposite statement as the alternative).
- Software prefetches are nonblocking (R27 pp.641-656): they install the line with an arrival
  time; a later demand access to a line in flight waits for the arrival instead of missing again.
- At most `l1.outstanding_demand_misses_per_core` (8, R08) fills in flight per core; an access
  that needs a new fill waits for a free slot. Gathers missing on more lines than that are
  charged all misses in parallel (optimistic).
- Scenarios: `fixed_level` (every access at one level), `classified` (address ranges), and
  `line_tracking` (set-associative true-LRU L1 32 KB/8-way and inclusive L2 512 KB/8-way, cold
  lines at `cold_level`, optional warm ranges). Sub-models under `line_tracking`, each `auto`
  (on when the profile has its parameters: the default since 0.3.0), `modeled` or `off`:
  - `tlb: modeled`: 64-entry fully associative first-level DTLB for 4 KiB pages
    (`tlb.l1_entries_4k`, measured C4) with `tlb.l1_miss_penalty_cycles` (29, measured C4 and
    R06 Table II); warm ranges also warm the TLB; the second-level TLB and page walks are not
    modeled.
  - `hardware_prefetcher: modeled`: a streaming L2 prefetcher with `l2.hw_prefetch_streams` (16,
    R01 p.19) streams, one per 4 KiB page, confirmed after two accesses with the same stride of at
    most `l2.hw_prefetch_max_stride_lines` (2, R08), prefetching `l2.hw_prefetch_depth_lines`
    (16, derived from memory.load_rt) lines ahead within the page into L2; it trains on loads and
    stores (R01 TUNE_PREFQ RFO bit).
  - `memory_service: modeled`: one memory fill per `memory.core_service_cycles_per_line` (20,
    measured at four threads) for this core; card-level sharing is not modeled.
  The sub-models are explicit memory events with finite resources and measured service rates;
  there is no ring or memory-controller simulation. Results that use them are
  `unvalidated_scenario_estimate` unless the kernel's declared shape is validated.
- Pseudo-LRU, coherence traffic, the instruction cache and loaded-latency growth are not
  modeled.

## Branches

- Correctly predicted branches cost their issue slot (`latency.branch_taken_bubble` 0,
  consistent with S8-01 C9 and C10 fixed at one thread). Mispredicted branches (per scenario:
  none, all, direction change, listed ids) delay the context's next issue by
  `latency.branch_mispredict_penalty` cycles beyond the normal spacing (5, measured per branch
  in the C10 pseudorandom test; `all_mispredicted` reproduces that row).

## Functional semantics

Exact for the operations listed as functional in `capabilities`: scalar integer ALU with
flags in 8/16/32/64 bits, conditional branches and setcc, mask ops, int32 vector ops and int64
logic, f32/f64 add/sub/subr/mul/max/min/FMA with one rounding in the requested mode and FTZ/DAZ
policy, compares to masks, blends, conversions (dq<->ps, pd->dq, ps<->pd, round), register
swizzles, broadcasts, up/down conversions (float16/uint8/sint8/uint16/sint16), masked loads
and stores (merge semantics: IMCI has no zeroing masks), vloadunpack/vpackstore halves with the
64-byte boundary rule, dword/qword gather and scatter with completion masks, `vpermd`,
`vpermf32x4`, and the x87 stack. Python floats are never used as the IMCI implementation; see
`fp.py`. NaN propagation follows the x86 first-operand rule (assumed); default NaN is the x86
real indefinite. Timing-only instructions (approximations, `vcvtfxpntpd2*` are exact now;
`vrcp23ps`, `vrsqrt23ps`, `vlog2ps`, `vexp223ps`, `vscaleps`) make `functional` fail with
`unsupported` and are only usable in static traces.

## What this is not

Not a system emulator: no operating system, system calls, files, signals, MPI or shared-memory
processes; no indirect jumps or calls (jump tables, function pointers: reported as unsupported);
no whole-program runs (about 20,000 simulated instructions per second). Callees outside the
region are costed stubs, not executed code. Contexts that communicate through memory are
rejected by the sequential functional model. No frequency or thermal effects, no coherence
traffic, no loaded-latency growth beyond the memory-service rate. Pair and card scales are
formulas, not simulations (`analytic-scales.md`). The binary adapter reads K1OM ELF files and
`objdump` listings; it is not a loader (data symbols are copied, the stack and arguments come
from the kernel's init).
