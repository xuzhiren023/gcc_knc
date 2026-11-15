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
   supported mnemonics (functional vs timing-only), memory and branch scenarios, profiles.
   Pick the scale and profile that cover the question; if the kernel uses anything not listed,
   stop and report it as unsupported instead of approximating.
2. **Prepare the input faithfully.** Write the kernel as normalized records
   (`schemas/kernel.schema.json`, `references/input-format.md`) or the GAS AT&T subset. Keep
   every dependency and side effect the real code has: spills and reloads, masks, address
   updates, flags, stores. Give initial state and expected outputs derived independently of
   the twin (hand calculation, host reference, integer-valued data). Say what one unit of work is.
3. **Execute, never estimate by hand.** Each command writes `result.json` + `summary.md` in its
   own output directory (`--out`, one per experiment). Report only numbers that come from a
   run with status `ok`. If Python is not available where you are, say so: do not invent a result.
   - `validate <kernel>` well-formedness and which parameters the profile lacks
   - `functional <kernel>` exact results of supported operations vs expected outputs
   - `simulate <kernel> --profile <id>` core-cycle prediction (1-4 contexts)
   - `bounds <kernel>` lower bounds; `--loop` ResMII/RecMII/critical path; `--search` exhaustive reorder
   - `bounds --scale card|pair --params <json>` labeled analytical scenario estimates
   - `compare <baseline result.json> <candidate result.json>` same model, same scenario, deltas
   - `prepare-native <kernel>` reproducible request for the shared hardware queue (no card access)
   - `import-native <measurement.json>` validate and turn a native measurement into a profile overlay
   - `selftest` the bundled unit tests (synthetic model tests, not hardware validation)
4. **Identify assumptions and unsupported features.** Copy the `assumptions`, `unsupported`,
   `limiting_constraints` and `calibration_status` fields of `result.json` into your report.
   A `missing_parameter`, `unsupported`, `needs_parameters`, `invalid_input` or
   `budget_exhausted` status is the answer; a `partial` block is never a result.
5. **Distinguish result kinds** in every report: functional result (exact), timing prediction
   (model cycles, `card-7120-measured` is built from imported microbenchmarks but has no
   end-to-end validation yet), analytical lower bound, analytical scaling estimate (pair/card
   scenarios with their stated assumptions), imported native measurement (the only hardware
   numbers). Never present simulated cycles as measured ticks. Keep Python wall time apart
   from predicted KNC cycles.
6. **Compare with the model unchanged.** `compare` refuses when engine version, profile hash,
   scenario, unit of work or numerical policy differ. Run baseline and candidate with the same
   `--profile`/`--overlay` and the same scenario; vary only the kernel.

## Scales

`instruction` and `region` (records of one or more contexts), `core` (1-4 in-order contexts:
U/V pairing, same-context issue spacing, round-robin picker, scoreboard, AGI, demand-miss
stalls, nonblocking prefetch, outstanding-miss limit, L1/L2 LRU line tracking, gather/x87/L2
prefetch occupancy) are simulated. `pair` and `card` are analytical scenario models that need
explicit parameters and return `needs_parameters` otherwise; they never multiply one-core
throughput by the core count.

## Profiles

`card-7120-measured` (the gcc_knc project's card; latencies imported from its native
characterization runs, see `references/parameters.md`), `card-5110p-literature`,
`card-3120-documented` (card constants only; latencies stay unknown), `knc-common` (rules and
documented values only), `synthetic-demo` (labeled synthetic, for exercising the engine).
Unknown parameters stop a run with `missing_parameter`; nothing gets a default cost.
Sensitivity: `--overlay profiles/overlay-vector-load-3.json`.

## References

- `references/architecture-model.md` what the core model does and does not do, with sources
- `references/input-format.md` records, GAS subset, scenarios, numerical policy
- `references/parameters.md` every parameter with value, status, source, uncertainty
- `references/bounds.md` bound terms, MII vocabulary, search-space claims
- `references/analytic-scales.md` pair and card scenario formulas and assumptions
- `references/calibration.md` prepare-native / import-native procedure, held-out validation
- `references/sources.md` which claims each source supports
- `references/gcc-pipeline-mapping.md` relation to GCC's `knc.md` pipeline description
