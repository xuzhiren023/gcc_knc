# Scheduling explorer

## 1. Evaluation of S14-02 and S14-03

This evaluation was written before the S14-14 implementation. The ticket records
and `gcc-pipeline-mapping.md` are its basis. The explorer changes no compiler
checkout, profile or measured row. Its outputs are predictions, not native results.

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
the explorer removes that metadata and its validated shape, and states the
resulting layout assumption before evaluating either baseline or candidate.

## 2. Interface and result contract

The tests specify `knc_model.scheduling.explore(kernel, profile, method=...,
seed=..., max_states=...)`, with methods `beam`, `modulo` and `list`.
It does not mutate the input. `beam_width` and `lookahead` default to eight.
`max_states` limits expanded beam prefixes or attempted modulo cycle placements;
the deterministic budget does not depend on host wall time. The list seed takes
one step per instruction and examines at most `lookahead` ready successors per
step. Bounded search reports this preparation separately, work consumed, whether
its space was exhausted and the trace resource lower bound. A beam that discards
candidates cannot claim an exhaustive optimum merely because its queue empties.

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

## 3. Methods and limits

The region is one context's block or the body selected by `kernel.loop`.
The final loop back branch stays last. Interior labels, other branches and calls
inside the region are rejected. Code outside the region remains in the functional
trace. Normalization transfers the entry label to the reordered region's first
instruction; inputs, expected outputs and numerical policy are retained.
Unknown memory aliasing is conservative, and x87 operations keep their stack order.

List scheduling uses the timing engine to score ready-prefix candidates, then
dependency height to break issue-time ties. An eligible compare whose only
remaining successor is the final jump is deferred behind other ready work. This
is a general pairing preference, not a case-ID rule. Its bounded lookahead keeps
it usable on blocks beyond the beam's 60-instruction limit.

Beam search starts with the baseline and list candidate, explores topological
prefixes and keeps the best `beam_width` prefixes at each depth. Prefix timing
is a heuristic ranking only. Complete orders are functionally executed and
evaluated on the real trace. Only strict improvements replace the incumbent.
The invariant issue/spacing/L1 subset of the trace lower bound can prune a long
search once the incumbent meets it. Execution-order-sensitive memory and
dependency terms are excluded from that bound. Search claims and budgets are
spelled out in `bounds.md`; an interrupted beam still returns a complete evaluated
candidate, while explicitly recording that it did not exhaust the space.

Modulo placement starts at the existing `max(ResMII, ceil(RecMII))`. For each II,
it greedily places the selected order in cyclic slots, with a finite stage horizon
covering a serial body plus one II. It checks forward and carried physical-register,
flag, x87 and conservative memory hazards, declared memory recurrences, AGI,
U/V pairing, cyclic issue spacing, L1 ports, x87 occupancy and context holds.
Isolated L1 latency and hold values come from the timing engine. A failed greedy
placement triggers the next integer II, not a proof of infeasibility; no achieved
II is claimed optimal. Exhausting the placement budget raises `budget_exhausted`.

Modulo supports ordinary scalar, mask, vector and x87 arithmetic/load/store bodies;
unusual resource classes return `unsupported`. Its steady-state L1 estimate excludes
decode and branch refill; the actual simulation retains the original scenario.
The count of registers live across stages is a count of distinct physical names
from a representative functional iteration, not renamed values or allocation.
No executable software pipeline is synthesized. The simulated order is the best
of baseline and list order, and is also the order used for modulo placement.

Every candidate includes whole-trace cycles, actual selected-loop iteration count,
cycles per iteration (entry/exit and surrounding work included), pairing and limiting
constraints. Binary layout metadata is removed from both sides of the comparison;
its validated shape is removed too. No-layout inputs use the ordinary profile/shape
classification. No timing parameters, calibration or held-out rows are changed.

## 4. Commands and compiler handoff

Run from the skill directory (choose reusable output directories):

```sh
python scripts/knc_twin.py schedule fixtures/reduce_2acc.json --method beam --seed 17 --max-states 4096 --out /tmp/twin-schedule --force
python scripts/knc_twin.py batch /tmp/twin-schedule/batch.json --out /tmp/twin-rank --force
python scripts/knc_twin.py schedule fixtures/reduce_2acc.json --method modulo --max-states 4096 --out /tmp/twin-modulo --force
python scripts/knc_twin.py schedule fixtures/saxpy_loop.json --method list --lookahead 8 --out /tmp/twin-list --force
```

In this repository, run model tests and experiments through `tools/run.py` per
AGENTS.md. No command above builds GCC or runs the card.

`candidate.s` comes from `asm.emit_gas`; `candidate.json` and `baseline.json`
are normal kernel inputs. `batch.json` freezes the loaded profile and overlays
using the existing batch protocol. Relative input-file paths become absolute in
exported kernels. Automatic queue creation is disabled in that manifest; native
requests may be staged explicitly with `prepare-native` for the lead to run.
The ordinary batch command ranks both candidates and refuses a profile mismatch.
Its existing uncertainty rules still apply. A ranking does not establish a
measured winner. S14-02/S14-03 still own code generation, legality, allocation,
spills and native acceptance.

## 5. Verification

The approved red commit recorded six expected failures for the missing scheduling
module. The seven acceptance tests now cover a 60-instruction block, deterministic
budget, a known small optimum, physical/flag/memory dependencies, characterization
fixtures, modulo cyclic resources and latency constraints, S12-31 compare/jump
adjacency with x87 order preserved, and CLI export ranked through a frozen-profile
batch (including refusal when the profile differs). These are model tests, not
hardware validation. The required bundled selftest and `tests/regress/test_knc_twin.py`
are short sequential model checks authorized by the ticket; long corpus sweeps and
card jobs remain outside this session.
