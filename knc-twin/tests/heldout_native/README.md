# Held-out native validation cases

Kernels predicted first and compared with native measurements that never set a profile
parameter. One harness owns them: `scripts/validate_heldout.py` (the characterization catalog
with `--kernels-s/--kernels-h/--measured`, plus every case directory here with `--cases`).
Results: `characterization-run/validation.md` and `references/validation.md`.

- `measured-characterization.json`, `characterization-run/`: the 119 measured rows of the
  gcc_knc characterization catalog; rows listed in `CALIBRATION_ROWS` set a parameter and are
  excluded from the held-out statistics.
- One directory per compiled-code or card case (S13-06): `case.json` (source assembly or
  adapter kernel, input, expected output, scenario), `measurement.json` (citing its native log;
  no job id; `used_to_set_parameters: false`) and `prediction.json` (written by
  `validate_heldout.py --cases tests/heldout_native --record`, deterministic;
  `tests/regress/test_knc_twin.py` in gcc_knc checks it is unchanged for the same engine and
  profile).

| case | scale | unit | in the core model |
|---|---|---|---|
| s12-31-microbench | core, 7 variants of one x87 row loop (`mb.s`) | core cycles per 27-product row | yes (single core, L1, every form supported; `movslq` costed as a scalar ALU op, unsourced) |
| s12-30-small-csr | core, 4 compiled `csr_raw` variants (`fixtures/batch` kernels) | core cycles per call | yes (single core, L1/L2-resident; input columns differ from the card's random ones) |
| stream-rmw/write-ngo/read-card, gemv-fp32-card | card (analytical, stand-in core loop) | GB/s | no: card scale is outside the core model; reported apart |

The profile's `calibration.held_out_validation_cases` (62) counts the characterization rows
only; it is left unchanged so that the profile hash, and with it every recorded prediction and
the frozen batch manifest, stay valid.

To add a case: write `case.json` and `measurement.json`, run the harness with `--record`
before comparing, and never derive a parameter or overlay from the measurement.
