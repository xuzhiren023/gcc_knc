# The core model

Target: one Knights Corner core (K1OM, IMCI). Not Knights Landing, not AVX-512, not an
out-of-order x86. Source ids (R01, R02, ...) are listed in `sources.md`.

## Contexts and issue

- Four hardware contexts; the kernel activates 1-4 of them (`streams`). Each context is a
  strictly in-order instruction stream (R01 §2.1, R17 slide 10).
- Per cycle the core issues at most two instructions, both from the same context: the first on
  the U pipe, the second on the V pipe if the pairing rules allow (R01 §2.1, R02 p.34).
- A context cannot issue in consecutive cycles: after an issue event its next issue is at least
  `core.min_issue_gap_same_context` (2) cycles later (R02 ch.4, R17 slide 11; measured 2.08
  ticks per independent op at one thread). A single context therefore reaches at most one
  issue event every other cycle; two or more contexts can fill every cycle.
- Context selection: among contexts that are eligible this cycle (not spaced out, not stalled,
  head instruction's operands ready, resources free), the one that issued least recently wins;
  ties go to the lower context number (round-robin picker, R02 ch.4, R17 slide 10). A context
  that is stalled never issues out of order and never lets later instructions bypass the head.
- Instruction fetch always hits; the two-entry prefetch buffer and its refill bubble (R02 ch.4)
  are not modeled.

## Pairing (V pipe)

- V-eligible classes (`pairing.v_eligible_classes`, from R02 Table 3-1 p.34): scalar ALU,
  scalar load/store, branch, mask ops, vector stores, packstores, prefetches. Vector arithmetic,
  vector loads, gathers, x87 and fences are U-only. Two vector arithmetic instructions never pair
  (S6-03 pair.vector_vector).
- A pair must have no register, address, mask or flag dependency between its members, except
  `cmp/jcc` and `test/jcc` (R02 p.56). Whether other flag producers (`dec/jnz`, `sub/jnz`) pair
  is not documented and is a candidate for a native request; the model does not pair them.
- Encoding rules (R02 p.56: at most 8 bytes, not displacement and immediate together, no
  MVEX/VEX form with a 32-bit displacement) apply when a record carries `encoding` hints;
  otherwise the record is assumed pairable and the assumption is recorded.
- The instruction after a branch is not paired with it (model assumption).

## Latencies and resources

- A register result is ready `latency` cycles after issue; a dependent instruction may issue in
  that cycle. Classes: scalar ALU 1, mask 1 (assumed), vector arithmetic 4, long vector
  (permute/swizzle/vrcp23ps) 6, pd->dq conversions 7, scalar imul 10 (R02 p.56), x87 add/mul 3,
  x87 div 38 (occupancy 38), x87 mul occupancy 2. Measured values are from S6-03 on the project
  card; see `parameters.md`.
- Loads: result ready after the level latency: L1 scalar 3 (measured) / vector 12 (measured
  chain; R08 documents 3, alternative overlay provided), L2 24, memory 357 (one thread, idle),
  plus for vector loads the difference `vector_load_l1 - scalar_load_l1` (assumed additive).
- A vector arithmetic instruction with a memory source ("folded load") pays no extra latency on
  an L1 hit (S6-03 C9) and stalls like a load otherwise.
- Address-generation interlock: a register written at cycle t can be used as an address from
  t + 3 (R01 p.19, R17 slide 13; S6-03 point 7 consistent).
- L1 data port: `l1.accesses_per_cycle` (1, R17 slide 13; alternative 2) loads+stores per cycle.
- Gathers occupy both pipes for `occupancy.gather_cycles_per_line` (7) cycles per distinct line
  and complete after `latency.gather_first_line` (15) + 7 per further line.
- `vprefetch1/2/nta` issue at most one per `occupancy.vprefetch_l2_core_cycles` (2) core cycles
  (S8-01 C2 measured 2.25). `vprefetch0` costs only its issue slot.
- Fences (`lock add`, `mfence`) serialize the core for `latency.fence`, unknown in every bundled
  profile: a kernel with a fence stops with `missing_parameter`.

## Memory

- Demand load misses stall the issuing context until the data arrives; other contexts continue
  (R08 "in-order design stalls thread on L1 data cache misses, except store misses"; R02 ch.4
  thread-specific flush). Store misses do not stall. No-read stores (`vmovnrngoaps`) allocate
  no line and need no fill slot.
- Software prefetches are nonblocking (R27 pp.641-656): they install the line with an arrival
  time; a later demand access to a line in flight waits for the arrival instead of missing again.
- At most `l1.outstanding_demand_misses_per_core` (8, R08) fills in flight per core; an access
  that needs a new fill waits for a free slot.
- Scenarios: `fixed_level` (every access at one level), `classified` (address ranges), and
  `line_tracking` (set-associative true-LRU L1 32 KB/8-way and inclusive L2 512 KB/8-way, cold
  lines at `cold_level`, optional warm ranges). Pseudo-LRU, the L2 hardware prefetcher, TLBs,
  coherence traffic and the instruction cache are not modeled; a scenario that relies on the
  hardware prefetcher is rejected.
- Store-to-load through the same line: the load waits `latency.store_to_load_same_line`
  (assumed 3) cycles after the store issued.

## Branches

- Correctly predicted branches cost their issue slot (`latency.branch_taken_bubble` 0,
  consistent with S8-01 C9). Mispredicted branches (per scenario: none, all, direction change,
  listed ids) delay the context's next issue by `latency.branch_mispredict_penalty` cycles beyond
  the normal spacing (5 measured per branch in the C10 pseudorandom test; the per-miss value may
  be about 10).

## Functional semantics

Exact for the operations listed as functional in `capabilities`: scalar integer ALU with
flags, conditional branches, mask ops, int32 vector ops, f32/f64 add/sub/mul/FMA with one
rounding in the requested mode and FTZ/DAZ policy, compares to masks, dq<->ps conversions,
masked loads/stores (merge semantics: IMCI has no zeroing masks), broadcasts, dword gathers,
`vpermd`. Python floats are never used as the IMCI implementation; see `fp.py`. NaN propagation
follows the x86 first-operand rule (assumed); default NaN is the x86 real indefinite. Timing-only
instructions (x87, approximations, unpack/packstore, scatter, pd->dq) make `functional` fail with
`unsupported` and are only usable in static traces or kernels whose expected outputs do not
depend on them.

## What this is not

No encodings, no loader, no ABI, no C/Fortran translation, no whole-program binaries. Contexts
that communicate through memory are rejected by the sequential functional model. Pair and card
scales are formulas, not simulations (`analytic-scales.md`).
