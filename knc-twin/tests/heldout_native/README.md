# Held-out native validation cases

Kernels that were predicted with `simulate` first and measured on the card afterwards, and
whose measurements were never used to set a profile parameter. They are the only evidence for
"the engine predicts this card": `calibration.held_out_validation_cases` in the card profile
counts them.

S13-06 (2026-11-15) added cases from measurements that already existed. Each directory holds
`case.json` (source assembly and loop, or card parameters), the assembly or stand-in loop,
`measurement.json` (citing its source log; no job id) and `prediction.json` (recorded before the
comparison by `tests/trial/knc_trial.py --record-heldout`; `tests/regress/test_knc_twin.py`
checks it is unchanged for the same engine and profile). Results: docs/research/knc-twin-trial.md.

| Case | Prediction | Measured | Pred/meas |
|---|---|---|---:|
| s12-31-microbench (x87 row loop) | unsupported (x87 memory forms) | 393-395 ns per row | - |
| s12-30-small-csr (x87 SpMV) | unsupported (x87 memory forms) | 16.47 ns per nonzero | - |
| stream-rmw-card | 156.5 GB/s | 179.11 GB/s | 0.874 |
| stream-write-ngo-card | 226.1 GB/s | 169.23 GB/s | 1.336 |
| stream-read-card, gemv-fp32-card | needs_parameters (read bandwidth unknown) | 147.24, 125.30 GB/s | - |

No core-scale case is inside the model yet, so `calibration.held_out_validation_cases` stays 0.
To add one: keep the prediction, the request, the measurement and the `import-native` result
together in a subdirectory named after the kernel; do not derive overlays from these measurements.
