# Held-out native validation cases

Kernels that were predicted with `simulate` first and measured on the card afterwards, and
whose measurements were never used to set a profile parameter. They are the only evidence for
"the engine predicts this card": `calibration.held_out_validation_cases` in the card profile
counts them.

Currently empty: no end-to-end prediction has been compared with a native measurement.

To add one: keep the prediction `result.json`, the `request.json`, the `measurement.json` and
the `import-native` result together in a subdirectory named after the kernel; record the error
per thread count in this README; do not derive overlays from these measurements.
