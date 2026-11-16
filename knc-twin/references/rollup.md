# Program roll-up: from region predictions to a program figure

`knc_twin.py rollup manifest.json` turns per-region twin predictions into the predicted change of
a program-level figure such as WRF seconds per step or an M4 program's run time. It ranks compiler
or loop changes before card time; the program's final speed is a card measurement.

## Manifest (`knc-twin.rollup/1`)

```json
{"schema": "knc-twin.rollup/1", "name": "WRF advection, candidate scheduler",
 "profile": "card-7120-measured", "frozen_profile_hash": "<64 hex, optional>",
 "program": {"unit": "seconds per step", "measured_per_unit": 2.84, "source": "run profile 2026-11-14, 60 threads"},
 "card": {"bytes_per_unit": 1.9e9, "traffic": "read_modify_write"},
 "unvalidated_band_pct": 30,
 "regions": [
   {"name": "advect_scalar", "share": 0.31, "share_source": "gprof exclusive time, same run",
    "baseline": "advect_scalar.before.json", "candidate": "advect_scalar.after.json"},
   {"name": "mp_mynn", "share": 0.12, "share_source": "same", "baseline": "mp_mynn.json"}
 ]}
```

- `share`: the region's fraction of the measured run time, from the run's own profile (a profiler,
  per-routine timers, or the project's region clocks). Shares may sum to less than 1; the rest of
  the run is assumed unchanged. They may not sum to more than 1.
- `baseline` / `candidate`: kernel files (adapter output with the run's inputs and expected
  results). A region with only a baseline is unchanged (ratio 1).
- `program.measured_per_unit`: the baseline's measured figure, used to express the prediction in
  the program's unit.
- `card`: optional bytes each unit must move through memory and the traffic type; the roll-up adds
  the memory floor `bytes / sustained bandwidth` from the profile and caps the prediction at it.
  This is a formula on a measured bandwidth entry, not a ring or memory-controller simulation.

## What the number means

For each region, ratio = candidate cycles per unit / baseline cycles per unit from `simulate` with
the same profile, scenario and inputs. The program's predicted time ratio is
`unmodeled share + sum(share x ratio)`. The band around it uses each region's validated error band
when its `provenance.shape` is a validated shape, else `unvalidated_band_pct` (default 30); the
result class is `calibrated_forecast` only when every modeled region is validated and nothing was
skipped, otherwise `unvalidated_scenario_estimate`. Regions the twin cannot run (unsupported
instruction, missing parameter, functional mismatch) are listed with the reason and their share is
left out of the modeled share: a roll-up over 40% of the run time says so.

## Rules

- One core, one thread per region: the roll-up does not model how 60 cores share the memory
  system beyond the bandwidth floor. A region that is memory-bound at full card load but
  core-bound alone is predicted optimistically; say so when `card` is given and the floor binds.
- Shares and the baseline figure come from a measured run; never from the twin.
- Rank, do not forecast: use the roll-up to order candidates and to decide which to send to the
  card, and quote the band with every number.

## Loop sampling

```
python scripts/knc_twin.py sample-loop kernel.json --loop L --warmup 64 --window 32 --tolerance 0.01 --max-iterations 4096 --out sample
```

The same options work with `simulate --sample-loop`. Sampling currently supports exactly one
functional context and a reachable label with a back-edge. Static traces and static trip-count
overrides are rejected. The selected loop must do **one unit of work per iteration**;
`unit_of_work.count` supplies the number of iterations to extrapolate. Nested loops execute
normally within each selected iteration. Entry code initializes both models, but extrapolated
time excludes entry/exit overhead. Select a different region or use plain `simulate` when that
overhead matters.

The interpreter and timing engine advance together, keeping registers, branches, cache/TLB,
prefetch and outstanding-access state. The interpreter stops too; sampling does not establish
whole-function correctness. If the entire function finishes, its expected outputs are checked
normally. The result reports functional Python seconds separately from timing Python seconds
and predicted KNC cycles, so users can assess the cost of tracing on their input. Up to two
instructions of functional lookahead preserve timing pairing and decode across boundaries.
The tracing-versus-timing cost comparison was not measured for this ticket; both are sampled
without claiming that either dominates host execution time.

`--warmup N` discards exactly N iterations. With the option omitted, warmup ends when an iteration
touches no new lines, capped at 64 iterations (and below the iteration budget). This is observed
first-touch coverage, not knowledge of the unexecuted input's working set. A streaming loop may
reach the cap while still discovering lines.

Each window initially has W iterations (default 32). Three full windows must agree: both lag-one
and lag-two cycle differences must be at most T times their mean (default T = 0.01). The sampler
also compares within-iteration address differences, per static memory instruction, to detect
irregular input. Two observed repetitions are required before an input period is accepted, and
the window must cover it. An uncovered period or lag-two agreement with lag-one disagreement
doubles W (or raises it to the observed period, whichever is larger). Ordinary drift keeps
the current window size and continues observing. This prevents an alternating pair of cheap/expensive
windows from being called steady solely because lag two agrees. Random indirect rows generally
need a complete input repetition or exhaust the budget. Regular translated streams can converge
without visiting their entire address space.

`prediction.sampling` contains the window series, widenings, observed period, discarded warmup,
iterations sampled, and `stop_reason`: `converged`, `max_iterations`, or `loop_finished`. A short
final window is reported but cannot prove convergence. The estimate uses the iteration-weighted
mean of the last three available windows; their minimum/maximum is
`cycles_per_iteration_band`. The per-unit band adds the existing shape's worst absolute error
(or the 30% unvalidated default) to that spread. Both the estimate and band are multiplied by
`unit_of_work.count` for the extrapolated total. Memory/instruction statistics describe only the
timed prefix, and `sampled_completion_cycles` records that prefix's completion time.

These are deterministic model estimates, not confidence intervals or measurements. A finite
prefix cannot exclude a later phase or a longer unseen reuse period. Supply representative
inputs and check the reported series. The usual instruction/cycle/wall-time budgets still
return `budget_exhausted`, with no valid prediction. The iteration budget is an intentional
sampling stop, with an explicitly unconverged estimate. Sampling neither changes profile
parameters nor uses held-out measurements to choose its window or band. `--jobs` integration
belongs to brief 02; this implementation is serial and has no random sampling state.

## Phases and representative regions

Use `phases` instead of the top-level `regions` list:

```json
{"schema": "knc-twin.rollup/1",
 "program": {"unit": "seconds per step", "measured_per_unit": 10},
 "phases": [
   {"name": "advection", "share": 0.4, "share_source": "measured run profile",
    "regions": [
      {"name": "representative interior loop", "share": 0.75,
       "share_source": "measured fraction represented by this loop",
       "baseline": "before.json", "candidate": "after.json",
       "sampling": {
         "baseline": {"loop": "L", "warmup": 64, "window": 32, "max_iterations": 4096},
         "candidate": {"loop": "L", "warmup": 64, "window": 32, "max_iterations": 4096}
       }}
    ]}
 ]}
```

This is a format illustration, not a measured WRF profile. Phase shares are fractions of program
time; region shares are fractions **within that phase**, including any explicitly represented
fraction. Supply multiple regions when the phase has different hot shapes. Names must be unique
within their list; shares must be positive, finite, and sum to at most one at each level. A
region side without `sampling` is fully simulated. Baseline/candidate must agree on scenario,
numerical policy and unit of work. Sampling options are the same as the command options, with
underscores in JSON (`max_iterations`).

For region r in phase p, the program weight is `phase.share * region.share`. Ratios and band
endpoints are weighted with these fractions; missing/skipped regions and unprofiled phases
retain their baseline time. This is algebraically identical to a flat manifest with those
program weights. Sampling spread propagates through the candidate/baseline ratio (candidate
low / baseline high, candidate high / baseline low), then adds the existing shape ratio error.
The resulting endpoints propagate through the phase and program sums. A sampled ratio of one
still retains its sampling uncertainty.

The report includes program time and its band in the supplied unit, program coverage, and a
per-phase table of share, covered fraction, ratio, band and result class. Region rows retain
their phase name, local share, effective program share and sampling series. A sampled region,
an unvalidated region (even at ratio one), or a skipped region prevents `calibrated_forecast`.
The existing HPCG pilot fixture exercises this arithmetic with its measured region shares;
splitting that fixture into phases is an algebraic check, not new phase-profile evidence. WRF
timestep validation requires the run's measured phase shares and dumped inputs from PhiWeather.
The WRF timestep case waits for a PhiWeather profile; no phase shares or dumped arrays were
supplied for this ticket.
