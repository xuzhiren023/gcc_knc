# Scheduling explorer

## 1. Evaluation of S14-02 and S14-03

This evaluation precedes implementation and uses the two ticket records and
`gcc-pipeline-mapping.md`. No compiler, profile or measured row is changed.

S14-02 probes a counted-loop pattern because SMS stops without `code_for_doloop_end`.
The twin supplies ResMII, RecMII, critical path, feasible II, stages and live-register
counts for strict FP, scalar and vector loops. It sizes overlap headroom; S14-02 owns
its <5% stop rule, pattern recognition, adoption, post-RA spills, size and card timing.

S14-03 needs orders, pairing, stalls and cycles to assess reservations, bypasses,
folded-memory costs and V eligibility. GCC schedules issue opportunities; the twin
predicts core cycles, including AGI, pairing, memory and recurrences beyond its DFA.
Reservation changes still require S14-03's measurements.

Scope: dependency-preserving ordering under the existing profile. Physical-register
RAW/WAR/WAW, flags, MXCSR observations, explicit dependencies, x87 stack order and
possibly aliasing stores are preserved. No allocation, spill insertion, legality
proof beyond this dependency view, GCC cost-model decision or hardware win is claimed.
S12-31 gas_0/adj_0 are calibration rows (`validation.md`); tests select gas_0's inner
loop while retaining the function and input. No held-out timings tune the search.

## 2. Methods and output

`knc_model.scheduling.explore(kernel, profile, method=..., seed=..., max_states=...)`
accepts `beam`, `list` or `modulo`, without mutating input. One context's block or
selected loop is supported, with the final branch last; interior labels/calls/branches
are rejected. List uses prefix timing and dependency height, deferring an eligible
compare whose only successor is the final jump. Beam ranks prefixes and simulates
complete orders. Modulo greedily places the best baseline/list order in cyclic slots.
See `bounds.md` for budgets, resource checks, pruning and search claims.

Candidates include normalized records, GAS from `asm.emit_gas`, whole-trace cycles,
pairing and limiting constraints. Cycles per iteration divide completion by actual
selected back-branch executions, including entry/exit and surrounding work.
Modulo reports II, stages, distinct physical register names live across stages
(from a representative functional iteration), and simulation minus estimated II.
No renamed values, allocation, prologue or epilogue are generated. Simulation runs
the actual reordered kernel, not an executable software pipeline.
Both baseline and candidate discard binary layout and, when layout was present,
its validated shape. They are then `unvalidated_scenario_estimate`; otherwise the
ordinary profile/shape classification applies. Inputs and numerical policy remain.

## 3. Commands and verification

```sh
python scripts/knc_twin.py schedule fixtures/reduce_2acc.json --method beam --seed 17 --max-states 4096 --out /tmp/twin-schedule --force
python scripts/knc_twin.py batch /tmp/twin-schedule/batch.json --out /tmp/twin-rank --force
```

Use `tools/run.py` in this repository. Exports are `candidate.s`, `candidate.json`,
`baseline.json` and `batch.json`; input-file paths become absolute. The manifest
freezes the existing profile/overlays and disables automatic native requests.
Use `prepare-native` to stage any requests for the lead; these commands run no card.
Seven tests cover long/deterministic search, a known optimum, dependencies, fixtures,
modulo constraints, S12-31 adjacency/x87 order and frozen-profile batch ranking/refusal.
Red had six missing-module failures. Selftest/regression are model checks, not native results.
