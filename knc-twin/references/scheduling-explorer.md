# Scheduling explorer

## 1. Evaluation of S14-02 and S14-03

This is the S14-14 red-phase specification, not an implemented command or a
performance result. The ticket records and `gcc-pipeline-mapping.md` are the
basis of this evaluation. No compiler checkout, profile or measured row changes.

S14-02 is a probe of whether a KNC counted-loop pattern can enable GCC SMS.
Its ticket reports that SMS currently stops without `code_for_doloop_end`.
The twin cannot answer whether GCC recognizes or transforms that pattern.
It can supply ResMII, RecMII, the iteration critical path, an achievable
initiation interval under its model, stage count and counts of values live
across stages for the strict FP recurrence, independent scalar and vector
development loops. These distinguish recurrence limits from opportunities to
overlap independent work. S14-02's less-than-5% headroom stop rule belongs to
that probe; S14-14 must expose the evidence rather than implement the compiler
switch or decide adoption. Post-RA spills, code size and card time remain
S14-02's acceptance evidence.

S14-03 needs candidate orders and their pairing, stalls and cycles to compare
the existing reservations against the twin's sourced rules. Its ticket asks
for measured bypasses, folded-memory costs and V eligibility, then checks
post-RA schedules. The mapping document distinguishes GCC issue opportunities
from core cycles, and identifies AGI, dynamic pairing, memory behavior and
recurrences that the DFA alone does not express. The explorer must use the
existing profile and timing engine, not invent bypasses or update eligibility
to favor a candidate. It can expose a missed compare/jump adjacency, latency
hiding opportunity or resource limit; it cannot authorize a reservation change
without the measurement required by S14-03.

Scope: dependency-preserving block/body ordering, bounded search, modulo
feasibility under the modeled resources, and a fast list-scheduling baseline.
Not in scope: register allocation, spill insertion, proof of memory-reordering
legality beyond the twin's dependency view, GCC's own cost model, or a claim
that a predicted order wins on hardware. Unknown aliasing remains conservative.
Register anti/output dependencies, flags, explicit dependencies, control flow
and the x87 stack must survive reordering. A live-value count does not promise
that GCC can allocate the schedule.

The brief selects S12-31 `gas_0` as a regression for finding compare/jump
adjacency. `validation.md` identifies gas_0/adj_0 as calibration rows. Use the
input and existing model unchanged; do not read held-out timings to tune the
search, introduce a special case for its IDs, or assert the brief's reported
native percentage as a new measurement. Its binary-derived kernel has two
back edges and no `loop` declaration. Tests select the inner loop in an
in-memory copy, preserving the complete function, input arrays and expected
output. Moving binary instructions also invalidates their old byte layout;
an eventual implementation must remove or regenerate that metadata and state
the resulting layout assumption before claiming calibrated coverage.

## 2. Proposed interface and acceptance contract

The red tests specify `knc_model.scheduling.explore(kernel, profile, method=...,
seed=..., max_states=...)`, with methods `beam`, `modulo` and `list`.
This interface is a proposal for the green phase. It must not mutate the input.
`max_states` limits search work; deterministic budgets must not depend on host
wall time. Bounded search reports work consumed, whether its space was exhausted,
and the trace lower bound. A beam that discards candidates cannot claim an
exhaustive optimum merely because its remaining queue empties.

Each successful result exposes the best candidate kernel as normalized records,
the reordered region's instruction IDs, whole-trace completion cycles, baseline
cycles, cycles per loop iteration (separate from unit-of-work normalization),
pair fraction, limiting constraints, assumptions, unsupported features and a
result class. GAS comes from `asm.emit_gas`; the candidate kernel must run through
the ordinary functional and timing engine and remain usable by `batch` with its
frozen profile. Preserve numerical policy and expected outputs. No new profile
parameters or held-out fitting are required.

Modulo output separately exposes the loop bounds, achieved II, stages, issue
cycle/slot per instruction and count of registers live across stages. Search II
from MII upward; report infeasibility or budget exhaustion honestly. Validate
cyclic spacing (including the last/first issue), latency/distance constraints,
U/V pairing, x87 serialization and L1 port use. Do not call a sorted body a
software-pipelined executable: absent prologue/epilogue expansion and register
renaming, simulate the actual reordered kernel and explicitly report the
difference from the modulo estimate.

## 3. Red-phase coverage and remaining green work

`tests/test_scheduling_explorer.py` specifies the long-block search, deterministic
budget, a known small optimum, dependency preservation, the characterization
fixtures, modulo schedule structure and the S12-31 adjacency regression. These
are model tests, not hardware validation. The green phase must additionally
wire commands and batch export, document the actual algorithms/search claims
in this document and `bounds.md`, list commands in `SKILL.md`, and run selftest
and `tests/regress/test_knc_twin.py` subject to the ticket's host-idle restriction.
No native run or speed claim is made in the red phase.
