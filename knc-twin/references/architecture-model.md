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
- Instruction fetch always hits; the two-entry prefetch buffer and its refill bubble (R02 ch.4)
  are not modeled. The C10 fixed-direction row at four threads (17 measured vs 12 modeled) is the
  visible cost of this omission for branch-dense code.

## Pairing (V pipe)

- V-eligible classes (`pairing.v_eligible_classes`, from R02 Table 3-1 p.34): scalar ALU and
  read-modify-write, scalar load/store, branch, mask ops, vector stores, packstores, prefetches.
  Vector arithmetic, vector loads, gathers, scatters, x87 and fences are U-only. Two vector
  arithmetic instructions never pair (S6-03 pair.vector_vector).
- A pair must have no register, address, mask or flag dependency between its members, except
  `cmp/jcc` and `test/jcc` (R02 p.56). `dec/jnz` and `sub/jnz` are not paired (not documented;
  native request candidate).
- A `nop` in the U slot takes no V partner (S6-03 agi.gap1-4: each nop beyond the first costs a
  full issue slot); an unconditional `jmp` does not issue in the V slot (S8-01 C10 fixed row:
  cmp/je, add, jmp are three issue events). Conditional branches do pair as `cmp/jcc`.
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
- Store-to-load through the same line: the load waits `latency.store_to_load_same_line` (7,
  derived from the C9 memory chain) after the store issued. Independent store/reload pairs are
  therefore over-charged (spill_reload.rt 9 modeled vs 5 measured): a known open miss.
- Address-generation interlock: a register written at cycle t can be used as an address from
  t + 3 (R01 p.19, R17 slide 13; S6-03 agi.gap0).
- L1 data port: `l1.accesses_per_cycle` (1, R17 slide 13; alternative 2) loads+stores per cycle.
- Gathers occupy a gather unit for `occupancy.gather_cycles_per_line` (7) cycles per distinct
  line while other instructions keep issuing; the data is ready after
  `latency.gather_first_line` (15) + 7 per further line; the completion mask is readable after
  `latency.gather_mask_cycles` (2). Scattered 16-line gathers measure about 11 per line, so the
  model is optimistic there (gather_scattered rows). Scatters need
  `occupancy.scatter_cycles_per_line`, unknown in every bundled profile.
- `vprefetch1/2/nta` issue at most one per `occupancy.vprefetch_l2_core_cycles` (2) core cycles
  (S8-01 C2 measured 2.25). `vprefetch0` costs only its issue slot.
- No-read stores (`vmovnr*`) stall their context `store.nr_stall_cycles_resident` (27) cycles
  when the line is in L1 or L2 and `store.nr_stall_cycles_memory` (157) otherwise, and occupy a
  shared store path for `store.nr_occupancy_core_cycles` (9) (S6-03 store_stream rows). A
  non-resident line written by a no-read store is left in L2 (assumed).
- Fences (`lock add`, `mfence`), `fldcw/fnstcw/fnstsw`, `fsqrt`, `idiv` need latencies that are
  unknown in every bundled profile: a region using them stops with `missing_parameter`.

## x87

The x87 stack is modeled exactly: eight physical registers with TOP, push/pop, `fxch`, the
control word's rounding and precision control, extended-precision arithmetic with one rounding,
`fld/fst` of binary32/64/80 and integers, `fistp/fisttp`, `fsqrt`, `fcom*` condition codes and
`fnstsw`. GAS AT&T operand conventions are followed (`fsub %st(1),%st` = st0-st1;
`fsubrp %st,%st(1)` = st1-st0; `fsubrl m` = m-st0), checked against GCC-KNC output
(`fixtures/gcc/x87test.s`). The functional trace gives the timing engine the physical registers
each instruction reads and writes, so x87 chains are scoreboarded like vector chains; a static
trace falls back to serializing x87 instructions. x87 instructions issue on U only.

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
  lines at `cold_level`, optional warm ranges). Optional sub-models under `line_tracking`:
  - `tlb: modeled`: 64-entry fully associative first-level DTLB for 4 KiB pages
    (`tlb.l1_entries_4k`, measured C4) with `tlb.l1_miss_penalty_cycles` (29, measured C4 and
    R06 Table II); warm ranges also warm the TLB; the second-level TLB and page walks are not
    modeled.
  - `hardware_prefetcher: modeled`: a streaming L2 prefetcher with `l2.hw_prefetch_streams` (16,
    R01) streams, one per 4 KiB page, confirmed after two accesses with the same stride of at
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

No encodings, no loader, no ABI, no C/Fortran translation, no whole-program binaries; `call`
and `ret` are region boundaries. Contexts that communicate through memory are rejected by the
sequential functional model. Pair and card scales are formulas, not simulations
(`analytic-scales.md`).
