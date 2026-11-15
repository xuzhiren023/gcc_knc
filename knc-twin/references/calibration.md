# Calibration and native validation

## Status

`card-7120-measured` imports single-core microbenchmark results measured natively on the
gcc_knc project's card (S6-03 2026-11-06; S8-01/S8-10/S8-12/S8-17 2026-11-07..09; identifiers
in the profile's `native_measurement_ids`). These fix parameters (latencies, occupancies,
bandwidths, barrier times). No end-to-end prediction of this engine has been compared with a
native measurement: `calibration.held_out_validation_cases` is 0 and every timing result says so
in `calibration_status`. The other card profiles are uncalibrated (literature or documented
values only). `synthetic-demo` is synthetic.

Passing `selftest` means the model behaves as specified; it is not hardware validation.

## Three kinds of test cases

- `tests/test_*.py`: synthetic model tests (run by `selftest`).
- `tests/calibration/`: kernels whose native result isolates one parameter (microbenchmarks).
  Their measurements become profile overlays. Currently documented only; the imported
  parameters came from the project's own characterization binaries, not from kernels in this
  directory.
- `tests/heldout_native/`: kernels predicted first and measured afterwards, never used to set a
  parameter. Empty until the first native request returns. Keep them held out.

## Procedure: predict, request, measure, import, compare

1. `simulate <kernel> --profile card-7120-measured --out P` (prediction, note `result.json`).
2. `prepare-native <kernel> --prediction P/result.json --out R` writes `request.json`,
   `kernel.S`, `driver.c`, `README.md`. No card is contacted. The kernel's expected outputs are
   checked first (`--no-check` to skip).
3. The queue operator reviews `kernel.S`/`driver.c`, builds them with the k1om toolchain
   (`k1om-mpss-linux-gcc -O2 -pthread -o knc_twin_native driver.c kernel.S`) and runs them in an
   exclusive window with pinned siblings (`--cpus 1`, `--cpus 1,2`, `--cpus 1,2,3,4`), following
   the project's measurement protocol (ADR-0010 in gcc_knc: five groups, median of medians,
   spread under 2%). The driver checks correctness once (exit 6 on mismatch) and prints JSON lines.
4. Fill `measurement.json` (`schemas/native-measurement.schema.json`): `request_hash_sha256`
   from `request.json`, job id, date, card profile, environment (MPSS, clock policy, toolchain),
   one `results` row per thread count with `ticks_per_unit_per_thread`, spread and check status.
   Add `parameters` only when the kernel is a calibration microbenchmark whose result isolates
   a parameter (name, value, unit, note).
5. `import-native measurement.json --request R/request.json --prediction P/result.json --out I`
   validates the file (schema, hash match), writes `I/overlay-profile.json` when parameters were
   given (status `measured`, source = job id and date), and reports prediction error per row.
6. Use the overlay with `--overlay I/overlay-profile.json`; results then carry a different profile
   hash, so baseline and candidate must both use it. To make it permanent, merge the overlay's
   parameters into the card profile, bump its `version`, append the job id to
   `native_measurement_ids`, and add the kernel to `tests/calibration/` or `tests/heldout_native/`
   with the measurement file next to it. Never edit a measured value without a new identifier.

## Comparing like with like

Measured ticks are TSC ticks per thread (TSC and core clock agree within 0.5% on the 7120
card). The prediction is core cycles per unit for the simulated context count. Compare the
one-thread prediction with the one-thread measurement, and so on. Report the error, the
scenario and the assumptions; a disagreement is a finding about a parameter or a missing
mechanism, to be recorded in `parameters.md` or `architecture-model.md`.
