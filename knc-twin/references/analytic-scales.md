# Pair and card scales: analytical scenario models

These are formulas with named parameters, labeled `analytical_scenario_estimate`. They are not
cycle simulations and are never derived by multiplying one-core throughput by the core count.
A required parameter that the profile leaves unknown gives `needs_parameters`, unless the
caller declares a sweep.

## pair (`bounds --scale pair --params p.json`)

Two cores exchange cache lines through their private L2s over the ring.

```
remote_line_cycles = latency.remote_l2_line_ns * card.clock_hz / 1e9
T = max(core_a_cycles, core_b_cycles)
    + handoffs * remote_line_cycles
    + lines_exchanged * remote_line_cycles / concurrency
```

Parameters: `core_a_cycles`, `core_b_cycles` (core-scale simulate results per unit),
`lines_exchanged`, `handoffs` (default 0), `concurrency` or `concurrency_sweep` (default sweep
1, 2, 4, 8, declared in the assumptions). Assumptions stated in the result: no ring bandwidth
limit, no contention from other cores, one round trip per handoff, no OS effects.
`latency.remote_l2_line_ns` is 192 (measured, S8-10 C11) in `card-7120-measured`, 243 (R06)
in `card-5110p-literature`, unknown in `card-3120-documented`.

## card (`bounds --scale card --params p.json`)

```
compute_s = per_core_cycles_per_unit * units / cores / card.clock_hz
memory_s  = bytes_per_unit * units / (bandwidth_gbs * 1e9)
T = max(compute_s, memory_s) * imbalance_factor + barriers * barrier_s
```

Parameters: `units`, `bytes_per_unit`, `traffic_type` (`read_only`, `read_modify_write`,
`write_normal`, `write_ngo`), `per_core_cycles_per_unit` (from a core-scale simulate at the
intended thread count), `cores` (default `card.usable_cores`), `barriers`, `barrier_kind`
(`tree`/`counter`), `imbalance_factor` (default 1.0, stated), `bandwidth_sweep_gbs` (declared
sweep when the profile has no sustained bandwidth for the traffic type).

The result lists per scenario the compute and memory terms, which one binds, the total, and
the bandwidth implied by the total. It also carries `not_an_estimate.single_core_throughput_times_cores_seconds`
to make explicit that the compute term alone is not the card estimate.

Known bandwidths in `card-7120-measured`: read-modify-write 156.5 GB/s (S8-17 C12), normal
stores 83.5, NGO stores 226.1 (S8-01 C1); read-only is unknown (the project's target is
264-299 GB/s; declare a sweep). Barriers: tree 6.0 us, counter 27.5 us (S8-10 C11).

Not modeled: ring contention, tag-directory placement, TLB and page size, frequency and
thermal effects, bandwidth dependence on access pattern or core count, OS core interference.
