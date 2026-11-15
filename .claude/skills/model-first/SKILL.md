---
name: model-first
description: >-
  Use before changing code or compiler heuristics to make a program or loop
  faster, and when reviewing such a change. Model operations, bytes and
  dependencies in the hot region; derive a run-time lower bound and prediction
  from the project's machine file, compare with measurement, and choose the
  transformation by the dominant term. Not for correctness, ABI or build tickets.
---

# Model first

Make the expected mechanism and its limit explicit before optimizing. Use the
Hager-Wellein model/measure/diagnose cycle, resource Rooflines and an explicit
Execution-Cache-Memory (ECM) overlap model. A prediction is not a lower bound.

This project's machine input is
[knc-machine.yaml](../../../docs/research/knc-machine.yaml). Read the relevant
keys and their notes, not an entire source corpus. Each value retains its unit,
resource scope, model/profile applicability, hardware status and evidence:
V = verified source evidence, R = reported project measurement, E = estimate or
inference. V does not mean reproduced on this machine. A null is unknown, not
zero. Follow the source locator if its qualification changes the decision.

The method is generic; obtain all architecture constants from the machine file.
Keep actual hardware identity separate from a runner's capacity profile. A
restricted core count does not emulate another model's clock or memory system.

## Choose the tier from ticket depth

| `depth` | Required artifact | Modeling limit |
| --- | --- | --- |
| light | One ticket-note line: dominant term, its value, measured time and bound/measured ratio | Reuse existing evidence; no new measurements |
| standard | Model table, lower bound, prediction, measurement, per-term utilization and predicted change | About 10% of the ticket's session budget |
| deep | Standard artifact, a microbenchmark for any uncertain input that changes the decision, and validation on a second program or profile | Measure only decision-changing uncertainty; reuse qualifying existing results |

Ticket scope and measurement authorization still apply. For a deep optimization
ticket, put the model and prediction through the ticket's lead review before
implementation. If required evidence or review is unavailable, record the gap
through the ticket; this skill creates no new approval command or card window.
Do not expand a correctness, ABI or build task into performance work.

## Nine steps

1. **Scope.** Name one hot region, the fixed useful work and its measured share
   `p` of whole-program time. Reuse an existing profile. Skip regions below about
   5% unless the ticket explicitly includes them. Before detailed modeling,
   estimate a plausible regional speedup `s` and its Amdahl cap
   `1 / (1 - p + p/s)`; the unlimited regional-speedup cap is `1/(1-p)`.
   If `p` is unknown, say so and do not invent a whole-program gain.

2. **Characterize.** Record trip counts, active lanes, working set and traffic
   at each memory level, data layout/alignment, page backing, active cores,
   workers per core, affinity, hardware model and requested/effective profile.
   Separate workload facts from compiler defaults. Choose a common accounting
   unit, such as completion of one iteration on every active worker, and a time
   unit. Keep TSC ticks, core cycles and seconds distinct.

3. **Model.** Count executed operations from the relevant assembly path: issue
   bundles (only eligible pairs share one), resource-specific operations,
   loads/stores, complete gather/scatter retry loops, prefetches, address work,
   branches, spills, helper calls and ABI transfers. Count bytes per level,
   independent chains and their loop-carried latencies, plus parallel work/span.
   Integer/control code uses instruction roofs; leave irrelevant FLOP terms N/A.
   Source every input as counted file/line or address, machine key, or measured
   ticket/run ID. Use [term-formulas.md](references/term-formulas.md) for units,
   resource aggregation, concurrency and overlap.

4. **Bound and predict.** For each applicable hardware/profile, compute
   `T_lb = max(T_i)` from terms that are individually lower bounds for the same
   work. A measured sustainable rate is an empirical roof for its configuration,
   not a proven maximum: label bounds using it conditional and show sensitivity.
   Exclude unknown terms explicitly; never substitute zero. Separately compute
   `T_pred` under stated overlap, latency and scheduling assumptions. On an
   in-order target, account for a stalled requesting thread and any overlap with
   other threads; an ECM-style serial sum is a prediction, not a bound.

5. **Compare.** Reuse matching measurements first. Any authorized new measurement
   follows the project's ADR-0010/ADR-0015 rules and ticket test budget; engineers
   stage card work for the lead. Match work, code, profile, placement and timing
   scope. Record `T_lb/T_meas`, `T_pred/T_meas` and `T_i/T_meas` for each time term.
   These are modeled utilization ratios, not measured hardware-counter activity.
   Report ranges, drift and infrastructure failures as such; an unrun test is not
   a native pass.

6. **Diagnose.** Set a tolerance before judging a result (normally about 15%,
   enlarged only for stated uncertainty). If `T_meas <= 1.15*T_lb` and the bound
   is applicable and credible, stop tuning this algorithm/layout: substantial
   improvement requires reducing the dominant work, bytes or mandatory span.
   A conditional empirical roof alone cannot prove a hardware limit. If measured
   time is much above prediction, name and check the missing pattern (address
   dependency, bank/set conflict, TLB, ring, scalar-domain bridge, imbalance).
   If prediction is much above the bound, investigate overlap, chains, worker
   density and prefetch distance. If measurement is below the bound, audit units,
   traffic, scope and roof applicability before claiming success.

7. **Choose.** Select the smallest legal change that reduces the dominant term
   or the diagnosed gap. Consult [levers.md](references/levers.md). Include added
   instructions, traffic and register pressure in the proposed model. Strict FP,
   ordering, masks, ABI and memory safety remain independent legality gates;
   a throughput opportunity never authorizes reassociation or fast math.

8. **Predict.** Before measuring the candidate, write its new `T_lb`, `T_pred`,
   expected regional speedup and Amdahl-limited whole-program gain, with ranges
   for decision-sensitive inputs. State a falsifiable mechanism and the result
   that would reject it. Do not book a predicted gain as a result.

9. **Measure and update.** Compare authorized existing/new results with that
   prediction, retain negative results in the ticket, and revise the model or
   decision. A new parameter proposal includes ticket/run ID, date, card/model,
   compiler commit, scope, spread, evidence and source. The machine file is
   lead-owned: request its update through the ticket unless that edit is in
   scope. Do not modify project wiring or start another experiment by implication.

## Fixed Model artifact

Use a `Model` section in the ticket note or its research note. Reuse it by link
on follow-up tickets; update changed inputs rather than rebuilding the analysis.

```text
Model
Region / fixed work / profile share p / plausible s / Amdahl cap:
Hardware / effective profile / cores / threads per core / compiler commit:
Accounting unit / time unit / evidence date / uncertainty band:

| Term | Formula | Inputs | Source | Value per profile |
| --- | --- | --- | --- | --- |
| ... | ... | quantities and units | counted file:line; machine.key [V/R/E]; run ID | one named value/range per applicable profile, or unknown/N/A with reason |

T_lb: ... (rigorous within stated resource assumptions, or conditional; omissions)
T_pred: ... (overlap and scheduling assumptions; range)
T_meas: ... (run ID, timing scope, spread; or not measured)

| Term | Profile | T_i / T_meas | Interpretation / uncertainty |
| --- | --- | --- | --- |
| ... | ... | ... | modeled resource utilization, not a PMU reading |

Bound utilization T_lb/T_meas: ...
Prediction ratio T_pred/T_meas: ...
Diagnosis / dominant term / decision (including stop): ...
Candidate T_lb / T_pred / regional speedup / whole-program gain: ...
Predicted versus measured / negative result / model update: ...
```

Use N/A for inapplicable resources and unknown for missing evidence. Show other
profiles as unmeasured when appropriate; never fill them by pretending a runner
profile is a physical card. A light ticket compresses this to its required line.

## Stop before over-modeling

Reuse the machine file and prior models. Bound only relevant terms; no whole-ISA
inventory, broad parameter sweep or new measurement that cannot change the
decision. Stop at the tier's budget or the near-bound criterion; document the
remaining uncertainty. A large residual gap calls for one focused diagnosis,
not speculative transformations. Acceptance and regression budgets remain those
of the ticket; a deep tier does not override an explicit no-card-run scope.

For a completed example using existing data, read
[example-c7-reduction.md](references/example-c7-reduction.md). Method basis and
the cited KNC ECM extension are in [term-formulas.md](references/term-formulas.md).
