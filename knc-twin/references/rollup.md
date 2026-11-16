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
