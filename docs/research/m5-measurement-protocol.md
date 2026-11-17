# M5 per-region measurement protocol (S14-04)

This section implements M1-M4 of the GPT Pro triage and the early donor-margin
check absorbed from S12-41. It extends the existing
[model-first method](../../.claude/skills/model-first/SKILL.md), rather than
introducing another optimization method. The ticket's earlier
`analytic-model-skill.md` destination is absent; the landed model-first skill
and its term formulas supply that method. Apply installed `knc-optimize` when
choosing transformations, and knc-twin for supported one-core loops.

[ADR-0016, including amendments 1-2](../adr/0016-m5-definition.md) controls the
corpus, held-out split, style coverage, score and pass criteria.
[ADR-0015](../adr/0015-m4-scoring-and-measurement.md) controls timing, validity,
paired launches, noise, retries and donor exceptions except as ADR-0016 amends
it. This diagnostic protocol changes none of those rules. Diagnostic regions,
density panels and outcome categories do not become additional corpus votes.

## Start with donor margins on development units

Before detailed tuning, reuse qualifying strict serial donor comparisons, or
stage an early matched development-only check for the lead. Report each unit's
style H/S/N/C/G/B as frozen by ADR-0016 amendment 2, input, compiler/runtime
heads, flags, correctness, pair data, speedup, confidence limits and source run.
Keep the SQLite donor exception labelled. Define margin as
`donor elapsed time / GCC-KNC elapsed time - 1`; work on the smallest known
margins first, including negative and zero margins. Unknown margins remain
visible and require feasibility evidence; they are not parity or passes.
Do not select new inputs by speedup. Keep failed/blocked checks and existing
negative evidence. Never open held-out units to select a tuning theme.

The extension accepts `donor_margins` records with `program`, `speedup` (or null)
and `source`; it preserves extra fields such as confidence limits and panel
labels. The sorted queue is advisory and cannot decide ADR-0016's pass rule.
The existing S12-19 allowlist remains deliberately unchanged: new M5 corpus
collection and its development/held-out wiring belong to the corpus lane.

## Model each hot region before optimizing

Reuse profiles and S12-19's exclusive source attribution and executable mapping
gate. List unassigned samples/functions separately; never assign an entire hot
function to an unproven loop. Rank by observed time with its limitations, not
by static vectorization failures. Record a region's fixed useful work, share
of whole-application elapsed time and Amdahl cap before selecting it. Sampled
CPU shares are estimates with their original denominator, not wall timers.

For every region, record these seven properties, each with a value, locator
and evidence status (verified, reported, inference, unknown, not applicable):

| Property | Required observation and decision it informs |
| --- | --- |
| Control uncertainty | Branch/indirect target distributions, trip-count variability, masks and tails; separate a static control-flow refusal from measured unpredictability |
| Dependency depth | Loop-carried chains, addresses, recursions, ordered reductions and critical path; latency and span in the same work unit |
| Available independence | Independent chains/outputs/iterations/tasks, active lanes, legal parallelism and limits on exposing it |
| Memory behaviour | Bytes at each level, useful versus transferred traffic, locality, layout, strides, alignment, gathers/retries, working set, backing, ownership traffic and placement |
| Compiler visibility | Aliasing, stride/shape knowledge, inlining, calls/dispatch, LTO and versioning; distinguish actual diagnostics from source inference |
| Numerical contract | Required order, precision, rounding, exceptions, errno, integer overflow and result tolerance; identify every permission to relax it |
| Runtime overhead | Setup, allocation, dispatch, synchronization, scheduling, worker persistence, I/O and host/card transfers, with completed timing boundaries |

Unknown is a required record when evidence is missing, never a claim of zero
cost or absence of a dependency. Properties drive the mechanism; style labels
drive coverage. A vectorized loop can remain latency or bandwidth limited.

Use the standard-depth Model table from model-first: term, formula, inputs,
source, value per profile; then bound, prediction, matching measurement,
per-term utilization, diagnosis, proposed change and falsifiable prediction.
Record hardware identity, effective profile, cores, contexts/core, affinity,
page backing, code revision, work and units. Model numerical legality separately.

## Lower bound and gap per region and level

Normalize every term to **seconds for identical fixed work**, then compute

`T_lb = max(T_dependency_path, bytes / sustainable_bandwidth,
            max_r(work_r / capacity_r))`.

Count executed assembly, including addresses, masks, retry loops, prefetches,
spills, calls and bridges. Include all relevant resource constraints (issue,
execution units, transfer services, concurrency and parallel span); do not
apply an FMA roof to integer/control code. Aggregate shared resource work over
workers, take the maximum critical worker/core dependency, and keep card-wide
traffic at card scope. Never divide every term by worker count. A dependency
path for a full completion differs from a steady-state recurrence per update.
State which is modeled, including startup/tail/completion effects.

Inputs come from [knc-machine.yaml](knc-machine.yaml), with exact key/subkey,
units, V/R/E status, source run, applicability, hardware status and notes.
Use measured sustainable rates only for matching traffic, density, working
set, placement, backing and completion scope. These are empirical roofs:
their bound is **conditional**, with sensitivity, not a proven physical limit.
Missing terms are listed explicitly; a maximum over known terms is partial.
Do not substitute peak specifications for absent measured bandwidth.

For example, `stream_triad_baseline_bandwidth` reports 163.70 decimal GB/s
useful traffic for its production project card configuration (R, S11-06 case 3).
For a counted useful traffic quantity B bytes under those same conditions, the
conditional memory term is `B / (163.70 * 10^9)` seconds. Its backing, density,
stores and completion notes are part of the input. This rate cannot supply a
zlib, one-context, or restricted-profile roof. The machine file's
`restricted_profile_sustainable_bandwidth` is null: report unknown there.
No new hardware fact or native measurement is asserted by this example.

Report `gap = T_meas - T_lb`, `T_lb/T_meas`, and each `T_i/T_meas`. Negative gaps
trigger a units/work/roof/scope audit. Ratios are modeled utilization, not PMU
readings. Keep `T_pred` separate, with explicit overlap/scheduling assumptions,
range and `T_pred/T_meas`. For one-core loops run knc-twin's capability checks
and report its status, assumptions and unsupported forms verbatim as results;
partial/unsuccessful output supplies no prediction. Its trace cold-start
dependency estimate is not a floor (until twin T1-03). No twin execution is
needed to extend old profile records without a loop trace or candidate.

Before timed candidate work, publish the Model table and tolerance (normally
15%, with justified input uncertainty). Follow model-first's near-bound stop
rule only for an applicable credible bound; conditional roofs cannot establish
hardware optimality. Predict regional and Amdahl-limited application gain.
Uncertain small differences are resolved on the card, not by twin rankings.

## Four separate outcomes

Every measured A/B result has exactly one of these labels; retain the complete
configuration and negative results. A combined intervention goes in the category
that includes its strongest permissions, and lists every constituent change.
Use separate controlled comparisons if attributing component gains.

| Label (JSON key) | Comparison permitted |
| --- | --- |
| Unmodified-source compiler gain (`unmodified_source_compiler_gain`) | Same source/input/algorithm/layout/numerical contract, matched resources; compiler-generated specialization stays here; explicit flag tracks remain labelled |
| Runtime-assisted gain (`runtime_assisted_gain`) | Worker density/persistence, scheduling, affinity or runtime dispatch changes with the same algorithm/layout and numerical contract; charge setup and completion |
| Algorithm or layout redesign (`algorithm_or_layout_redesign`) | Source algorithm, traversal, data layout or library/kernel replacement changes under the preserved result contract; also covers combinations with runtime assistance |
| Relaxed numerics (`relaxed_numerics`) | Any result using changed precision, order, tolerance, errno/FP semantics or other numerical permission, including combined runtime/redesign changes |

Absent outcome measurements are explicitly empty, never zero gain. Relaxed
numerics, runtime and redesign rows cannot replace the frozen strict compiler
primary. Report numerical checks, overhead and reference path for every outcome.

## Four measurement levels

| Level (JSON key) | Required scope |
| --- | --- |
| One context (`one_context`) | One pinned hardware context, other work/placement declared; fixed region work and completed elapsed time |
| One core (`one_core`) | One physical core, explicit 1/2/4-context panels and per-worker work; aggregate throughput distinguished from individual latency |
| Whole card (`whole_card`) | Named physical card and effective resource profile, cores/density, verified affinity, completion and imbalance; parallel panels follow ADR-0015 machine-state rules |
| Whole application (`whole_application`) | Frozen launch-to-exit work, setup/I/O/teardown included as ADR-0015 specifies, plus separate host/transfer/native/synchronization times where applicable |

Keep matching level-specific bounds, predictions and measurements. Never scale
one context into a claimed card measurement. The serial primary remains serial
against serial; whole-card parallel diagnostics are side tracks, not parallel
copies counted as application acceleration. Report full/3100/5100 profiles
without calling restrictions native smaller-card measurements. Only 7120 full
decides under ADR-0016. Engineers stage binaries; the lead runs card work.

## Triage extension and host check

`tools/vec_triage.py m5` reads an existing development `triage.json` and optional
annotation JSON, and writes a new file without collection, compilation or
source access. Attribution, samples and old fields are preserved. Every region
gets seven property records, four level records and four separate outcome
lists. Without evidence, bounds, gaps and ratios are null. Existing sampled
`cpu_seconds` is never implicitly used as `T_meas`.

Annotation schema (all omitted properties/levels/outcomes remain unknown/empty):

```json
{
  "style": "B",
  "donor_margins": [{"program": "zlib", "speedup": null, "source": "not measured"}],
  "regions": {
    "exact captured region id": {
      "properties": {
        "compiler_visibility": {"status": "reported", "value": "specific observed diagnostic", "source": "capture:line"}
      },
      "levels": {
        "one_context": {
          "work": "fixed useful batch including tails",
          "configuration": "card/profile/revision/density/backing/affinity",
          "assumptions": "scope, overlap, applicability and sensitivity",
          "terms": {
            "dependency_path": null,
            "memory": null,
            "resources": {}
          }
        }
      },
      "outcomes": {}
    }
  }
}
```

Each known term supplies `seconds`, `formula`, `source`, and `qualification`
(`conditional` or `rigorous`). Derive its seconds in the reviewed Model table
from counted work and machine inputs; this tool takes the maximum rather than
guessing operation classes or evaluating arbitrary formula strings. A level's
optional `measurement` and `prediction` each supply `seconds` and `source` for
the declared work/configuration. The reviewer must verify applicability;
syntactically valid evidence strings do not certify a model. Each outcome list
item supplies `level`, `baseline_seconds`, `candidate_seconds`, `work`,
`configuration`, `source`; include pair samples/spread and validity as extra
fields. The tool computes speedup and preserves those fields. Invalid labels,
nonfinite/negative times, unknown region IDs and sealed program names fail.

Host acceptance uses the existing **serial-zlib** capture, all 164 source
regions. Its leading region has 24 samples, estimated 0.24595 CPU seconds and a
control-flow vectorization refusal. Those facts do not reveal branch entropy,
dependency depth, memory traffic or completed region wall time. The host check
therefore preserves attribution and explicitly missing model evidence instead
of inventing a bound/gain; arithmetic fixtures exercise max/gap calculations,
outcome isolation, donor ordering and rejection. No performance tuning occurs.

```text
python tools/run.py --name s14-04-m5-host --inputs tools/m5_triage.py tools/vec_triage.py tests/tools/test_m5_triage.py -- python -m unittest discover -s tests/tools -p test_m5_triage.py
python tools/vec_triage.py m5 --triage ../_shared/S12-19/debug/serial-zlib/triage.json --output ../_shared/S14-04/zlib-m5.json
```

The host test writes `.work/_shared/S14-04/zlib-m5.json`; it is disposable analysis
output, excluded from git. No new native pass, timing gain or M5 gate result is
claimed. Missing evidence blocks performance conclusions, not host schema use.
