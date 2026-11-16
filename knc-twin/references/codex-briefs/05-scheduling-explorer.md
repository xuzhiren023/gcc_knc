# Codex ticket brief: knc-twin, a scheduling explorer beyond the 12-instruction search

For the GCC-KNC lead to dispatch on a Codex lane (backend codex, depth deep, model per
`harness/policy.json`; never Fable). Branch `twin/0.3` of gcc_knc, folder `knc-twin/`. Owner roadmap
item 4 (2026-11-16), after sampling (brief 04) and the multi-core model (brief 03).

## Before implementing

Read and evaluate GCC-KNC tickets S14-02 (software pipelining, SMS) and S14-03 (scheduler) in
`work/tickets/`, and `references/gcc-pipeline-mapping.md` (how the twin's rules relate to GCC's
`knc.md`). The explorer exists to tell those tickets which transformations pay on this core, with the
measured pairing and latency rules, not to re-derive what the tickets already decided. Write the
evaluation first (`references/scheduling-explorer.md`, section 1): what each ticket needs from the
twin, what questions the explorer answers, and what it does not (register allocation, legality of
memory reordering beyond the twin's dependency view, GCC's own cost model).

## What exists

`scripts/knc_model/bounds.py`: trace bounds; loop MII (ResMII, RecMII, critical path, over the
static body); an exhaustive dependency-preserving reorder search for straight-line blocks of at most
12 instructions on one context (`bounds --search`). The timing engine evaluates any candidate order
exactly (`simulate`).

## Work items

A. **Bounded search for longer blocks.** A branch-and-bound or beam search over dependency-
preserving orders of a block of up to about 60 instructions, using the trace lower bound as the
pruning bound and the timing engine as the evaluator; report the best order found, its cycles, the
bound, and whether the search was exhaustive; deterministic for a given seed and budget.

B. **Modulo scheduling for loop bodies.** For a loop (the kernel's `loop`), compute ResMII and
RecMII as today, then search initiation intervals from MII upward for a modulo schedule under the
twin's rules (U/V pairing, same-context spacing, latencies, x87 alone, L1 port), reporting the
achieved II, the schedule and its stage count, and the registers live across stages (count only; no
allocation). Evaluate the resulting kernel order with the timing engine on the real trace and report
the difference between the modulo-schedule estimate and the simulation.

C. **Pseudo out-of-order reordering.** For a loop body or block, a heuristic (list scheduling with
the twin's latencies and the pairing rules as the resource model, plus a lookahead window) that
produces an order quickly for blocks the search cannot cover; report its cycles against the bound
and, where the bounded search ran, against the best found order.

D. **Output for the compiler tickets.** For each candidate schedule: the order as GAS text (through
`asm.emit_gas`), the predicted cycles per iteration, the limiting resource or recurrence, and the
pairing achieved. `batch` must be able to rank schedules produced this way with a frozen profile;
results are `unvalidated_scenario_estimate` unless the kernel's shape is validated.

## Done when

- The evaluation section names what S14-02 and S14-03 need and the explorer's scope.
- A, B and C exist with tests (red first) on the characterization-style loops in `fixtures/` and on
  the S12-31 row loop (`tests/heldout_native/s12-31-microbench/kernels/gas_0.json`), where the
  explorer must find the adj/mid order (compare next to its jump) that the card measured 11% faster.
- `references/bounds.md` documents the search claims (exhaustive or not, bound used) and
  `references/scheduling-explorer.md` the methods; `SKILL.md` lists the commands.
- Host rule until the lead says M4 is done: two single-threaded processes at most, no builds, no card.
