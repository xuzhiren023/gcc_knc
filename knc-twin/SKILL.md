---
name: knc-twin
description: Run supported KNC/IMCI simulations, check kernels, compare schedules and calculate bounds. Use for gcc-knc, PhiChat and PhiWeather optimization.
---

# knc-twin

A standard-library Python twin of one Intel Xeon Phi Knights Corner (K1OM, IMCI) core, plus
analytical pair/card scenario models. It runs on the host or in a code-execution sandbox and
needs no card. Entry point: `scripts/knc_twin.py` (Python 3.8+). Everything bundled resolves
relative to that file; the current directory does not matter.

## Workflow (follow in order)

1. **Inspect capabilities before choosing a model.** Run
   `python scripts/knc_twin.py capabilities --out <dir>` and read `capabilities.json`: scales,
   supported mnemonics (functional vs timing-only), memory and branch scenarios, profiles,
   result classes. If the kernel uses anything not listed, stop and report it as unsupported
   instead of approximating.
2. **Prepare the input faithfully.** From compiler output use the adapter:
   `python scripts/from_gcc_s.py file.s --function NAME --out k.json` (whole function) or
   `--loop NAME:LABEL` (one loop), then supply `--init init.json` with initial registers,
   memory and expected outputs derived independently of the twin (host reference, hand
   calculation, integer-valued data). `--audit` over several `.s` files reports complete-region
   coverage by parser/isa/functional/timing before any run. Hand-written records follow
   `schemas/kernel.schema.json`. Keep every dependency and side effect the real code has
   (spills, masks, x87 stack, scatter completion, address updates, flags, stores); never
   simplify a region to make it pass. Say what one unit of work is, and declare
   `provenance.shape` when a validated shape applies (`references/validation.md`).
3. **Execute, never estimate by hand.** Each command writes `result.json` + `summary.md` in its
   own output directory (`--out`, one per experiment). Report only numbers from a run with
   status `ok`. If Python is not available where you are, say so: do not invent a result.
   - `validate <kernel>` well-formedness and which parameters the profile lacks
   - `functional <kernel>` exact results of supported operations vs expected outputs
   - `simulate <kernel> --profile <id>` core-cycle prediction (1-4 contexts)
   - `bounds <kernel>` lower bounds; `--loop` ResMII/RecMII/critical path; `--search` exhaustive reorder
   - `bounds --scale card|pair --params <json>` labeled analytical scenario estimates
   - `compare <baseline result.json> <candidate result.json>` same model, same scenario, deltas
   - `batch <manifest.json>` rank a candidate set with a frozen profile hash; uncertain cases get
     native requests under `queue/`
   - `prepare-native <kernel>` reproducible request for the shared hardware queue (no card access)
   - `import-native <measurement.json>` validate and turn a native measurement into a profile overlay
   - `selftest` the bundled unit tests (synthetic model tests, not hardware validation)
4. **Identify assumptions and unsupported features.** Copy the `assumptions`, `unsupported`,
   `limiting_constraints`, `calibration_status` and `result_class` fields of `result.json` into
   your report. A `missing_parameter`, `unsupported`, `needs_parameters`, `invalid_input` or
   `budget_exhausted` status is the answer; a `partial` block is never a result.
5. **Classify every number.** Each result carries a `result_class`: `conditional_bound`
   (bounds; valid under the listed model assumptions), `unvalidated_scenario_estimate`
   (simulate without a validated shape; every pair/card total), or `calibrated_forecast`
   (simulate on a kernel whose declared shape has a held-out validation entry in the profile,
   with its error band). A formula is not a bound; a simulation is not a measurement. Keep
   functional results, timing predictions, bounds, scaling estimates and imported native
   measurements apart, and keep Python wall time apart from predicted KNC cycles.
6. **Compare with the model unchanged.** `compare` and `batch` refuse when engine version,
   profile hash, scenario, unit of work or numerical policy differ. Run baseline and candidate
   with the same `--profile`/`--overlay` and scenario; vary only the kernel. Send anything the
   model cannot rank (unsupported, missing parameter, unvalidated memory behaviour, within the
   `too_close_fraction` of the baseline) to the native queue with the generated request.

## Scales

`instruction`, `region` and `core` (1-4 in-order contexts: U/V pairing, same-context issue
spacing, round-robin picker, x87 stack dependencies, AGI, demand-miss stalls, nonblocking
prefetch, outstanding-miss limit, L1/L2 LRU line tracking with optional DTLB, streaming L2
prefetcher and memory-service sub-models, gather/scatter/x87/L2-prefetch occupancy) are
simulated. `pair` and `card` are analytical scenario models that need explicit parameters and
return `needs_parameters` otherwise; they never multiply one-core throughput by the core count.

## Profiles

`card-7120-measured` (the gcc_knc project's card; parameters imported from its native
characterization and checked against 119 measured rows, `references/validation.md`),
`card-5110p-literature`, `card-3120-documented` (card constants only; latencies stay unknown),
`knc-common` (rules and documented values only), `synthetic-demo` (labeled synthetic).
Unknown parameters stop a run with `missing_parameter`; nothing gets a default cost.
Sensitivity: `--overlay profiles/overlay-vector-load-12.json`.

## References

- `references/architecture-model.md` what the core model does and does not do, with sources
- `references/input-format.md` records, GAS subset, the compiler-output adapter, scenarios
- `references/parameters.md` every parameter with value, status, source, uncertainty
- `references/validation.md` held-out validation, ranking reliability, validated shapes, open misses
- `references/bounds.md` bound terms, MII vocabulary, search-space claims
- `references/analytic-scales.md` pair and card scenario formulas and assumptions
- `references/calibration.md` prepare-native / import-native procedure, held-out rules
- `references/sources.md` which claims each source supports
- `references/gcc-pipeline-mapping.md` relation to GCC's `knc.md` pipeline description
