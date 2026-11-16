# Bounds, candidates and optima

Three different things, never mixed:

1. **Timing of a particular candidate**: `simulate` (`result_type: timing_prediction`).
2. **Optimistic lower bound**: `bounds` (`analytical_bound`). The largest of independent
   constraints; no schedule under the model can beat it. It does not say a schedule reaching it
   exists.
3. **Proven optimum within a search space**: `bounds --search` enumerates every
   dependency-preserving order of one context's straight-line block (at most 12 instructions)
   and simulates each with the unchanged model. The result claims optimality only when the
   space was exhausted; a budget hit is reported as `budget_exhausted` with the best found. When
   the best equals the lower bound this is said too.

## Trace bounds (`bounds <kernel>`)

Terms, each in cycles for the whole trace of the active contexts:

- `core_issue_events`: sum over contexts of the minimum number of issue events (each event is
  one U instruction plus at most one V-eligible instruction; instructions that occupy both
  pipes cannot pair). One event per cycle at most.
- `per_context_issue_spacing`: `gap * events - (gap - 1)` for the busiest context (a context
  issues at most every other cycle).
- `l1_port`, `gather_occupancy`, `x87_unit_occupancy`, `l2_prefetch_issue_occupancy`,
  `fence_serialization`: resource occupancies.
- `dependency_critical_path`: longest chain through register, flag, explicit and same-line
  store->load dependencies with model latencies; memory levels per the scenario (under
  `line_tracking`, a line costs its cold level once and L1 afterwards: optimistic).
- `memory_concurrency`: distinct missing lines times level latency divided by the outstanding
  miss slots (Little's law, R08 slides 23-28), ignoring the hardware prefetcher.

## Loop bounds (`bounds --loop`, needs `kernel.loop`)

Vocabulary from Rau, *Iterative Modulo Scheduling* (HPL-94-115):

- `ResMII`: max over resource terms per iteration (core issue events, per-context spacing,
  occupancies).
- `RecMII`: max over recurrence circuits of total latency / total distance. Register and flag
  recurrences have distance 1 (a value read before it is written in the body comes from the
  previous iteration); memory-carried recurrences must be declared in
  `loop.memory_carried [{from, to, distance}]`. Computed by binary search with Bellman-Ford
  positive-cycle detection, then snapped to a rational.
- `MII = max(ResMII, ceil(RecMII))`: lower bound on steady-state cycles per iteration for any
  modulo schedule under the model.
- `iteration_critical_path`: longest distance-0 chain in one iteration: the latency of one
  iteration, not the throughput. A loop can have II 4 and a 17-cycle iteration.

Under `line_tracking` the loop bound assumes steady-state L1 hits; use `fixed_level` to bound a
miss-dominated loop.

## Scheduling explorer (`schedule`)

`schedule <kernel> --method beam --max-states 4096 --beam-width 8 --seed 17`
explores one straight-line block or a selected loop body of at most 60 static
instructions. The final back branch remains last; labels, physical-register
RAW/WAR/WAW, flags, MXCSR observations, explicit dependencies, x87 stack order
and possibly aliasing stores constrain the order. Interior labels and control
transfers are rejected. All candidate cycles come from functional tracing and
the unchanged timing engine, including the surrounding function when present.

The pruning bound is an **invariant resource subset of the trace lower bound**:
issue events, same-context spacing and L1 ports. UV-both instructions prevent
pairing but do not add an extra issue event. Dependency and memory-concurrency
terms of the original execution are excluded: a reordered prefetch can change
memory timing. Prefix simulation ranks the beam; it is not used as a lower
bound. A global bound hit can stop a long search, but does not set
`space_exhausted`. The bound is conditional on the model, not a card guarantee.

`max_states` counts expanded beam prefixes; each considers at most the body
length in ready successors. Width limits the retained frontier at each depth.
The baseline and a lookahead list seed are evaluated before beam expansion;
`list_steps` reports that fixed preparation cost, and `orders_evaluated` counts
distinct full orders including the baseline. Work is deterministic for fixed
input, profile, seed, width, lookahead and state budget. No wall-clock cutoff
decides which candidate wins. Beam truncation and budget exhaustion are recorded.
`space_exhausted` is true only if all legal orders were explored without either
truncation. Otherwise this is best found, not a proven optimum; a bound match
is reported separately. Status `ok` means the returned complete candidate was
evaluated successfully, even if the beam's search budget ended.

`--method list --lookahead 8` chooses among a bounded number of ready operations
using prefix timing, dependency heights and a preference to leave an eligible
compare adjacent to the final jump. It supports bodies beyond 60 instructions.
Beam reports `list_cycles` and `best_minus_list_cycles` for comparison. Neither
list scheduling nor beam ordering is a claim about real out-of-order hardware.

`--method modulo --max-states 4096` starts at the existing loop MII and tries
each increasing integer II. It greedily places the selected executable order
in cyclic slots, allowing stages. Each attempted cycle placement consumes one
state. It enforces zero/distance-one hazards, declared memory-carried edges,
profile latency/AGI, U/V pairing, cyclic context spacing, L1 ports, x87 occupancy
and memory-operand context holds. Failed greedy placements do not prove that
an II is infeasible; the achieved II is never claimed minimal. A state limit
before a complete feasible placement returns `budget_exhausted`, not a partial
schedule presented as a result.

Modulo estimates assume steady-state L1, without decode or branch-refill
stalls; unusual resources (gather/scatter, fences, prefetches, no-read stores,
division/control serialization) are explicitly unsupported in placement.
X87 occupancy reservations are conservative, including the operand-load lead-in.
Register live counts count distinct physical names from the representative
functional iteration, not register allocation or renamed value versions.
There is no prologue, epilogue or rotating-register generation. Actual simulation
executes the reordered kernel under its original scenario; the reported
`simulation_minus_estimate_cycles_per_iteration` makes that distinction explicit.
Per-iteration simulation is whole-trace completion divided by actual selected
back-branch executions, so includes entry, exit and any surrounding loops.

Both baseline and candidate discard obsolete binary-layout metadata. A declared
validated shape is removed when that metadata was present; such candidates are
`unvalidated_scenario_estimate` until the new assembly is built and reimported.
For inputs without layout, the usual shape/profile classification applies.
Exports include `candidate.s` (via `asm.emit_gas`), `candidate.json`, the
normalized baseline and a frozen-profile batch manifest; the existing `batch`
command evaluates those kernels without any new ranking or timing rules.

## Reading a result

`binding_term` names the constraint that sets the bound. Compare it with the simulated
candidate's `limiting_constraints`: when the candidate is far above the bound and the binding
term is `dependency_critical_path`, more independent chains or software pipelining help; when it
is `per_context_issue_spacing`, more contexts or fewer instructions; when `core_issue_events`,
only fewer instructions or better pairing.
