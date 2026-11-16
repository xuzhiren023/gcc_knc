---
name: knc-twin
description: Run supported KNC/IMCI simulations, check kernels, compare schedules and calculate bounds. Use for gcc-knc, PhiChat and PhiWeather optimization.
---

# knc-twin

A standard-library Python twin of one Intel Xeon Phi Knights Corner (K1OM, IMCI) core, plus
analytical pair/card scenario models. It runs on the host or in a code-execution sandbox and
needs no card. Entry point: `scripts/knc_twin.py` (Python 3.8+). Everything bundled resolves
relative to that file; the current directory does not matter.

## What it is for, and what it is not

- **For**: ranking compiled variants of a hot function or loop before card time; finding what
  binds (issue slots, a dependency, x87 serialization, misses, decode); bounds; checking that a
  candidate computes the same result; turning measured time shares into a predicted change of a
  program-level figure (`rollup`).
- **Not for**: replacing a card run. It is not a system emulator: no operating system, system
  calls, files, MPI or shared-memory processes, and no whole-program execution. At about 20,000
  simulated instructions per second it covers functions and loops (millions of instructions),
  not a forecast run. Accuracy questions about a whole application (for example a WRF physics
  option) are outside it. Final speed numbers come from the card.
- **How far to trust it**: read `references/validation.md` first. It states the held-out error
  on compiled code, the decision bar (median error at most 10%, right winner in at least 90% of
  pairs measured more than 5% apart, at least 50 compiled loops) and whether the bar is met.

## Workflow (follow in order)

1. **Inspect capabilities before choosing a model.** Run
   `python scripts/knc_twin.py capabilities --out <dir>` and read `capabilities.json`: scales,
   supported mnemonics (functional vs timing-only), memory and branch scenarios, profiles,
   result classes. If the code uses anything not listed, stop and report it as unsupported
   instead of approximating.
2. **Prepare the input faithfully: the whole function, as built.**
   - From an object file or the linked executable (preferred; no `.s` needed):
     `python scripts/from_binary.py FILE --function NAME --disassembly DIS.txt --out k.json`,
     where `DIS.txt` is `objdump -dr FILE` from the K1OM binutils (or pass `--objdump TOOL`).
     This keeps entry code, alignment padding with its real NOP bytes, instruction lengths and
     prefixes, calls and returns. `--with-callee NAME` takes a callee into the region;
     every other callee needs a costed stub in `--calls` (cycles from a profile or measurement;
     a stub never gets a default cost). `--list` shows the functions.
   - From compiler assembly: `python scripts/from_gcc_s.py file.s --function NAME` or
     `--loop NAME:LABEL`; `--audit` reports complete-region coverage. This path has no code
     layout, so prefix decode and padding are not modeled and the result says so.
   - **Use the inputs of the measured run.** Give arrays as `init.memory` file blocks
     (`{"addr": ..., "file": "cols.bin"}`, raw dumps or text lists; the result records each
     file's SHA-256). For sparse, indexed or branchy code a different index stream is a
     different experiment. If the run's data cannot be dumped, say so and report the spread
     over several generated inputs.
   - Expected outputs come from outside the twin (host reference, exact arithmetic, the card).
     Keep every dependency and side effect the real code has; never simplify a region to make
     it pass. Say what one unit of work is, and declare `provenance.shape` when a validated
     shape applies (`references/validation.md`).
3. **Execute, never estimate by hand.** Each command writes `result.json` + `summary.md` in its
   own output directory (`--out`, one per experiment). Report only numbers from a run with
   status `ok`. If Python is not available where you are, say so: do not invent a result.
   - `validate <kernel>` well-formedness and which parameters the profile lacks
   - `functional <kernel>` exact results of supported operations vs expected outputs
   - `simulate <kernel> --profile <id>` core-cycle prediction (1-4 contexts), with front-end and
     memory statistics, stub calls and input-file hashes
   - `sample-loop <kernel> --loop LABEL --warmup N --window W --tolerance T --max-iterations M`
     sample a single-context loop, preserving functional and timing state between windows;
     equivalent to `simulate --sample-loop --loop LABEL`. One iteration must be one unit of
     work. Reports the window series, stopping rule, spread and extrapolated cycles. Both
     trace and timing are sampled; final expected outputs are checked only if execution ends.
     Every sampled prediction is an `unvalidated_scenario_estimate`, even for a validated shape.
     See `references/rollup.md` for the stopping rule and its limits.
   - `bounds <kernel>` lower bounds; `--loop` ResMII/RecMII/critical path; `--search` exhaustive reorder
   - `bounds --scale card|pair --params <json>` labeled analytical scenario estimates
   - `compare <baseline result.json> <candidate result.json>` same model, same scenario, deltas
   - `batch <manifest.json>` rank a candidate set with a frozen profile hash; uncertain cases get
     native requests under `queue/`
   - `rollup <manifest.json>` weight region predictions by measured time shares: predicted
     change of seconds per step (or any program figure), with a band and the unmodeled share
     (`phases` groups regions by measured phase share; region shares are within each phase).
     Each side of a region can supply `sampling` options. Sampling spread is propagated into
     the program band; a sampled or unvalidated region prevents a calibrated program forecast.
   - `calibration-plan` what to measure in the next card window (staged microbenchmarks, open
     misses, held-out cases to add)
   - `prepare-native <kernel>` reproducible request for the shared hardware queue (no card access)
   - `import-native <measurement.json>` validate and turn a native measurement into a profile overlay
   - `selftest` the bundled unit tests (model tests, not hardware validation)
4. **Identify assumptions and unsupported features.** Copy the `assumptions`, `unsupported`,
   `limiting_constraints`, `calibration_status` and `result_class` fields of `result.json` into
   your report, and the `parameters_used` entries whose status is `assumed` or `derived`.
   A `missing_parameter`, `unsupported`, `needs_parameters`, `invalid_input` or
   `budget_exhausted` status is the answer; a `partial` block is never a result.
5. **Classify every number.** Each result carries a `result_class`: `conditional_bound`
   (bounds; valid under the listed model assumptions), `unvalidated_scenario_estimate`
   (simulate without a validated shape; anything with stub calls; every pair/card total), or
   `calibrated_forecast` (simulate on a kernel whose declared shape has a held-out validation
   entry in the profile, with its error band). A formula is not a bound; a simulation is not a
   measurement. Keep functional results, timing predictions, bounds, scaling estimates and
   imported native measurements apart, and keep Python wall time apart from predicted KNC cycles.
6. **Compare with the model unchanged.** `compare`, `batch` and `rollup` refuse when engine
   version, profile hash, scenario, unit of work or numerical policy differ. Run baseline and
   candidate with the same `--profile`/`--overlay` and scenario; vary only the kernel. Do not
   choose between variants predicted closer together than the validated error for that shape:
   send those, and anything unsupported or unvalidated, to the native queue with the generated
   request.
7. **Keep it calibrated.** After a card window: run the open items of `calibration-plan`,
   import them, add the window's compiled runs as held-out cases (prediction recorded before
   the comparison), rerun `scripts/validate_heldout.py`. A measurement that changes a rule
   becomes a calibration row and stops counting as held out (`references/calibration.md`).

## Scales

`instruction`, `region` and `core` are simulated: 1-4 in-order contexts; U/V pairing with the
measured rules (x87 and NOP issue alone, compare-and-jump pairs, dependent instructions do not);
same-context issue spacing; prefix decode delays, encoding pairing limits and padding from the
code layout; optional instruction-cache misses; taken-branch refill; x87 stack dependencies and
memory-operand serialization; AGI; store-to-load interlock and forwarding; demand-miss stalls;
nonblocking prefetch; outstanding-miss limit; L1/L2 LRU line tracking with DTLB, streaming L2
hardware prefetcher and memory-service sub-models on by default; gather/scatter one cache line
per execution; calls, returns and costed stubs. `pair` and `card` are analytical scenario
models (formulas on measured bandwidths, no ring or memory-controller simulation) that need
explicit parameters and return `needs_parameters` otherwise; they never multiply one-core
throughput by the core count.

## Profiles

`card-7120-measured` (the gcc_knc project's card) extends `core-x100-measured` (core timing in
cycles measured or derived on that card) which extends `knc-common` (documented rules).
`card-3120-documented` and `card-5110p-literature` inherit the same core layer (same core
design; transferred, not re-measured) with their own clock, cores and memory figures: every
result on them is an unvalidated estimate. `synthetic-demo` is labeled synthetic. Parameters
without a measurement or a sourced prior stop a run with `missing_parameter` (today: the lock
prefix/fence cost and scatter occupancy); nothing gets a silent default. Sensitivity overlays:
`profiles/overlay-*.json`.

## References

- `references/validation.md` held-out validation on compiled code, the decision bar, validated shapes, open misses
- `references/architecture-model.md` what the core model does and does not do, with sources
- `references/input-format.md` records, GAS subset, both adapters, calls and stubs, input files, scenarios
- `references/parameters.md` every parameter with value, status, source, uncertainty
- `references/calibration.md` the calibration habit: plan, prepare-native, import-native, held-out rules
- `references/rollup.md` program roll-up manifest and what its number means
- `references/bounds.md` bound terms, MII vocabulary, search-space claims
- `references/analytic-scales.md` pair and card scenario formulas and assumptions
- `references/sources.md` which claims each source supports
- `references/gcc-pipeline-mapping.md` relation to GCC's `knc.md` pipeline description
- `references/handoff-prompt.md` a prompt that tells another agent what the twin does and its one good use
