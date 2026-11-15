# Capability report, knc-twin 0.1.0

Machine-readable version: `python scripts/knc_twin.py capabilities --out <dir>` writes
`capabilities.json` (scales, per-mnemonic table, scenarios, profiles). This page separates what
is implemented from what is not, and says how much of it is backed by hardware evidence.

## Implemented

**Scales**

| scale | kind | what |
|---|---|---|
| instruction | simulated | timing class, pipe eligibility and latency per supported mnemonic; exact semantics for the mnemonics marked functional |
| region | simulated | straight-line or single-loop record streams, 1-4 contexts; functional execution, cycle prediction, trace bounds, loop MII, exhaustive reorder search (<= 12 instructions) |
| core | simulated | 4 hardware contexts with 1-4 active, in-order per context, U/V issue with documented pairing classes and the cmp/jcc exception, 2-cycle same-context issue gap, least-recently-issued round-robin picker, scoreboarded register/flag/mask dependencies, 3-cycle address-generation interlock, demand-load-miss stalls per context (others progress), nonblocking software prefetch with in-flight tracking, 8-entry outstanding-miss limit, L1 port limit, LRU L1/L2 line tracking, gather/x87/L2-prefetch occupancy, fence serialization, branch misprediction scenarios |
| pair | analytical | two cores exchanging lines over the ring: max(core work) + handoffs and lines at remote-L2 latency over a declared concurrency |
| card | analytical | max(compute term, bandwidth term) x imbalance + barriers, per traffic type; needs_parameters when the bandwidth is unknown unless a sweep is declared; never one-core throughput x cores |

**Functional (exact) coverage**: scalar integer add/sub/and/or/xor/cmp/test/mov/lea/inc/dec/
neg/not/shl/shr/sar/imul with flags, 32/64-bit registers; jmp and conditional branches on flags
and on masks (jkzd/jknzd); kmov/kand/kor/kxor/kxnor/kandn/kandnr/knot/kortest; int32 vector
add/sub/and/andn/or/xor/mullo/min/max/shifts (immediate and variable), compares to mask;
f32 and f64 add/sub/mul and all FMA forms (fmadd/fmsub/fnmadd/fnmsub x 132/213/231) with a
single rounding in rn/rd/ru/rz, FTZ/DAZ policy, signed zeros, infinities, NaN propagation;
f32/f64 compares to mask; dq/udq <-> ps conversions with rounding immediate; vmovaps/apd/dqa32/
dqa64 loads and stores with merge masks; no-read stores; vbroadcastss/sd, vpbroadcastd; dword
gather with completion mask; vpermd. Expected outputs are checked lane by lane; NaNs match any
NaN unless bitwise comparison is requested.

**Timing-only mnemonics** (no semantics; usable in static traces): vcvtfxpntpd2dq/udq,
vrcp23ps, vrsqrt23ps, vlog2ps, vexp223ps, vpermf32x4, vloadunpackld/hd, vpackstoreld/hd,
vgatherdpd, vscatterdps, movzx, x87 fadd/fmul/fdiv families and moves, lock_add, mfence.

**Inputs**: normalized JSON records (schema provided) and a GAS AT&T subset (labels, size
suffixes, masks, rounding, 1toN broadcasts, lock add). Dynamic traces come from functional
execution or static unrolling with explicit address descriptions; no card trace is needed.

**Reports**: result.json + summary.md with result type, status, engine version, profile id/
version/hash, input hash, scale and representation, calibration status, functional-check
status, assumptions, unsupported features, prediction or bound, limiting constraints, exact
invocation, artifact paths, Python wall time (separate from predicted cycles). Statuses:
ok, invalid_input, unsupported, missing_parameter, budget_exhausted (with a partial block
that is never a result), functional_mismatch, needs_parameters, incompatible.

**Evidence**: `card-7120-measured` imports native single-core microbenchmarks (latencies 4/6/7/
12/3/24/357, AGI, gather, x87, prefetch issue rate, bandwidths, barrier times) with job ids.
`card-5110p-literature` uses published measurements by others. `card-3120-documented` and
`knc-common` carry documented values only and leave the rest unknown. `synthetic-demo` is
labeled synthetic in every result.

## Not implemented (explicit)

- Any mnemonic outside the table: rejected, never costed. Swizzles other than 1toN broadcasts.
  Semantics of x87, approximations, unpack/packstore, scatter, pd->dq. 8/16-bit registers,
  memory-destination ALU forms.
- Contexts that communicate through memory (sequential functional model). Inter-core coherence
  traffic, TLBs, page size, instruction cache, the L2 hardware prefetcher, pseudo-LRU details,
  bank conflicts, the decoder's refill bubble, loaded-latency growth, frequency/thermal effects.
- Whether `dec/jnz` (and other flag producers besides cmp/test) pair; `latency.fence`;
  `latency.vector_long` and `vector_convert_df` on the 3120/common profiles; read-only sustained
  bandwidth; any 3120/5110P latency not published: all surface as missing_parameter or
  needs_parameters.
- C, Fortran, arbitrary assembly or binaries: no translation. Encodings, loader, ABI.
- Pair and card scales are formulas; no ring, directory or memory-controller simulation.
- Hardware calibration of end-to-end predictions: none yet (`tests/heldout_native/` is empty).
  Passing the bundled tests is not validation against the card.

## Known model uncertainties carried as alternatives

`latency.vector_load_l1` 12 (measured chain) vs 3 (R08) — overlay provided; `latency.l2_hit`
24 vs 11 (R17); `l1.accesses_per_cycle` 1 vs 2; `l1.outstanding_demand_misses_per_core` 8 vs
38; `latency.branch_mispredict_penalty` 5 per branch vs ~10 per miss; `fp.ftz_rule` tiny vs
tiny_and_inexact; `occupancy.vprefetch_l2_core_cycles` 2 vs measured 2.25; gather per-line
occupancy understates scattered gathers (112 vs measured 127 per 16 lines).
