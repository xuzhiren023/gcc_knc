# Calibration and native validation

## Status

`card-7120-measured` imports single-core microbenchmark results measured natively on the
gcc_knc project's card (S6-03 2026-11-06; S8-01/S8-10/S8-12/S8-17 2026-11-07..09; identifiers
in the profile's `native_measurement_ids`). The engine's predictions were then compared with
the 119 measured rows of that characterization (`validation.md`): rows that set a parameter are
labeled calibration, the rest are held out. No prediction of a *compiler-generated* region has
yet been compared with a native run of that region; `tests/heldout_native/` holds the
characterization comparison only. The other card profiles are uncalibrated (literature or
documented values). `synthetic-demo` is synthetic.

Passing `selftest` means the model behaves as specified; it is not hardware validation.

## Three kinds of evidence, three result classes

- `conditional_bound`: `bounds` output; valid for the model's assumptions, never a hardware
  guarantee.
- `unvalidated_scenario_estimate`: every `simulate` result whose kernel shape has no held-out
  validation, every pair/card total, every result using an assumed sub-model parameter.
- `calibrated_forecast`: `simulate` on a kernel whose `provenance.shape` is listed in the
  profile's `calibration.validated_shapes` with its measured error band. The list is written by
  the lead from `validation.md`; a user cannot promote a shape by editing the kernel.

## Rules

1. Predict first. A kernel compared with a native run is predicted with the frozen profile
   before the measurement is looked at; the result file keeps the profile hash.
2. Never tune on a held-out case. A parameter may be changed only from a measurement that
   isolates it (a calibration row); the row then moves to the calibration list in
   `scripts/validate_heldout.py` and out of the held-out statistics. Changes made in the first
   validation round (store-to-load path, plain vector load latency, no-read store stalls,
   store-miss stalls, nop/jmp pairing, gather completion mask, unpack merge rule, HWP depth) are
   recorded that way in `validation.md`.
3. A model-structure change (a new rule) is recorded with the row that exposed it; the row is
   then no longer held out for that aspect.
4. A disagreement is a finding, not a reason to widen tolerances: it goes into `validation.md`
   under open misses with the suspected mechanism and a native request when one would settle it.

## Procedure: predict, request, measure, import, compare

1. `simulate <kernel> --profile card-7120-measured --out P` (prediction, note `result.json`).
2. `prepare-native <kernel> --prediction P/result.json --out R` writes `request.json`,
   `kernel.S`, `driver.c`, `README.md`. No card is contacted. The kernel's expected outputs are
   checked first (`--no-check` to skip). `batch` writes the same request for every candidate it
   cannot rank under `queue/`.
3. The queue operator reviews `kernel.S`/`driver.c`, builds them with the k1om toolchain
   (`k1om-mpss-linux-gcc -O2 -pthread -o knc_twin_native driver.c kernel.S`) and runs them in an
   exclusive window with pinned siblings (`--cpus 1`, `--cpus 1,2`, `--cpus 1,2,3,4`), following
   the project's measurement protocol (ADR-0010 in gcc_knc: five groups, median of medians,
   spread under 2%). The driver checks correctness once (exit 6 on mismatch) and prints JSON lines.
4. Fill `measurement.json` (`schemas/native-measurement.schema.json`): `request_hash_sha256`
   from `request.json`, job id, date, card profile, environment (MPSS, clock policy, toolchain),
   one `results` row per thread count with `ticks_per_unit_per_thread`, spread and check status.
   Add `parameters` only when the kernel isolates a parameter (name, value, unit, note).
5. `import-native measurement.json --request R/request.json --prediction P/result.json --out I`
   validates the file (schema, hash match), writes `I/overlay-profile.json` when parameters were
   given (status `measured`, source = job id and date), and reports prediction error per row.
6. Use the overlay with `--overlay I/overlay-profile.json`; results then carry a different profile
   hash, so baseline and candidate must both use it. To make it permanent, merge the overlay's
   parameters into the card profile, bump its `version`, append the job id to
   `native_measurement_ids`, add the case under `tests/heldout_native/` (held out) or
   `tests/calibration/` (parameter isolating), and rerun `scripts/validate_heldout.py` so
   `validation.md` stays current.

## Native requests worth sending now

Listed with the parameter or rule each would settle (`validation.md`, open misses):

- a dependent plain vector-load chain (`vmovaps` load, `vaddps` use) at one thread:
  `latency.vector_load_l1` 5 derived vs 3 documented;
- independent store/reload pairs with and without aliasing: the store-to-load path for
  non-dependent pairs (spill_reload.rt 5 measured vs 9 modeled);
- `dec/jnz` and `sub/jnz` loops against `cmp/jne`: flag-producer pairing beyond cmp/test;
- scatter completion cost by lines touched: `occupancy.scatter_cycles_per_line`;
- `lock add` in a dependent chain: `latency.fence`; `fsqrt`, `idiv`, `fldcw/fnstsw` latencies;
- a scattered 16-line gather chain: per-line occupancy (7 modeled vs about 11 measured);
- a four-thread sequential stream: HWP depth and memory service (85 modeled vs 78 measured per
  thread), and the branch-dense four-thread case (prefetch-buffer refill, 17 vs 12).

## Comparing like with like

Measured ticks are TSC ticks per thread (TSC and core clock agree within 0.5% on the 7120
card). The prediction is core cycles per unit for the simulated context count. Compare the
one-thread prediction with the one-thread measurement, and so on. Report the error, the
scenario and the assumptions; a disagreement is a finding about a parameter or a missing
mechanism, to be recorded in `parameters.md`, `architecture-model.md` or `validation.md`.
