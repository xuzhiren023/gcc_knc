# Codex ticket brief: knc-twin, iteration sampling and phase sampling

For the GCC-KNC lead to dispatch on a Codex lane (backend codex, depth deep, model per
`harness/policy.json`; never Fable). Branch `twin/0.3` of gcc_knc, folder `knc-twin/`. Owner roadmap
item 2 (2026-11-16), after `--jobs`/PyPy (brief 02) and before the multi-core model (brief 03).
Standard-library Python only; held-out rules of `references/calibration.md` apply: results are
estimates until a held-out card run covers them.

## Why

The one-core engine runs about 20,000 simulated instructions per second. A loop of millions of
iterations, or a whole timestep of WRF, cannot be simulated to the end; today users cut regions by
hand (`validate_heldout.py` uses a two-point slope over round counts). Sampling makes the
prediction reach program scale with a stated error.

## A. Iteration sampling (loops)

New command `knc_twin.py sample-loop <kernel> --loop LABEL [--warmup N] [--window W] [--tolerance T]
[--max-iterations M]` (and the same as an option of `simulate`):

- Run the functional interpreter as today (it is cheap relative to the timing engine? measure: if
  not, sample the trace too and say so) and feed the timing engine iteration by iteration.
- Warm-up: discard the first N iterations (default: until every line the loop touches has been
  touched once, bounded by N).
- Stopping rule: after each window of W iterations compute cycles per iteration; stop when the last K
  windows agree within T (default 1%) or at M iterations. Report the per-window series, the rule that
  fired, the estimated cycles per iteration with its spread (min/max of the last K windows), and the
  extrapolated total for the kernel's `unit_of_work.count` iterations.
- Steady state must be real: a loop whose working set does not fit a cache level and whose misses
  come in phases (for example sweeping a matrix larger than L2 with a periodic reuse pattern) must
  not stop early. Detect periodicity longer than W (compare windows at distance 1 and 2) and widen W.
- The result carries `result_class` `unvalidated_scenario_estimate` with the sampling error band
  added to the shape's band, and `sampled: true` with the series in `result.json`.
- Determinism: the same inputs give the same sample for any `--jobs`.

Validation on data we have: the S12-31 HPCG 104-cubed case (`tests/heldout_native/s12-31-hpcg-104`)
has a full 8000-row run recorded; the sampled prediction must land within its own stated band of
the full run's slope and the measured 699.6 cycles per 27 nonzeros. Add it as a test. For the S12-30
small cases (random columns) show that the stopping rule does not stop before the input's period.

## B. Phase sampling (whole-program figures)

Extend `rollup` (`scripts/knc_model/rollup.py`, `references/rollup.md`) with a `phases` manifest:

- A measured profile gives phases (for example WRF: advection, microphysics, boundary-layer, small
  steps) with their time shares and, per phase, the hot regions (kernels converted from the binary
  with the run's inputs) and each region's share within the phase.
- For each region, `sample-loop` or a plain `simulate` gives cycles per unit; the phase figure is the
  share-weighted sum; the program figure is the phase-weighted sum, with the unmodeled share left
  unchanged (as `rollup` does today) and the sampling bands propagated.
- Representative intervals: when a phase's profile has several hot regions with different shapes,
  the manifest names which regions stand for which fraction; the report shows the covered fraction of
  each phase and refuses a `calibrated_forecast` when any region is sampled or unvalidated.
- Output in the program's unit (seconds per step), with the band, the covered fraction and the
  per-phase table in `summary.md`.

Validation on data we have: the S11-28 HPCG serial pilot (shares in `docs/research/s12-31-hpcg.md`,
measured rating change 1.088 for the S12-31 rule) through the existing `fixtures/rollup` example,
now with phases; and one WRF timestep when PhiWeather supplies a run profile with phase shares and
dumped arrays (ask them; `tests/heldout_native/wrf_coverage.py` lists the routines).

## Done when

- `sample-loop` exists with the stopping rule, the series and the band in `result.json`; tests show it
  reproducing the full-run slope on the HPCG 104-cubed case and not stopping early on a periodic
  input (red first).
- `rollup` accepts phases, propagates bands, reports covered fractions; `references/rollup.md` and
  `SKILL.md` describe both; every sampled result is labelled an estimate.
- Host rule until the lead says M4 is done: two single-threaded processes at most, no builds, no card.
