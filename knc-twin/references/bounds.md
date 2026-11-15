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

## Reading a result

`binding_term` names the constraint that sets the bound. Compare it with the simulated
candidate's `limiting_constraints`: when the candidate is far above the bound and the binding
term is `dependency_critical_path`, more independent chains or software pipelining help; when it
is `per_context_issue_spacing`, more contexts or fewer instructions; when `core_issue_events`,
only fewer instructions or better pairing.
