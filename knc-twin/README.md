# knc-twin

A portable functional and timing twin of one Intel Xeon Phi Knights Corner (K1OM / IMCI) core,
with analytical pair and card scenario models, packaged as a Claude skill. Python 3.8+,
standard library only.

- `SKILL.md` — the skill entry point and workflow Claude follows
- `scripts/knc_twin.py` — CLI: capabilities, selftest, validate, functional, simulate, bounds, compare, prepare-native, import-native
- `scripts/knc_model/` — engine (profiles, ISA table, exact FP, interpreter, cache scenarios, core timing, bounds, analytic scales, native export)
- `profiles/` — hardware parameters with provenance (common rules; 7120 measured; 5110P literature; 3120 documented; synthetic demo; a sensitivity overlay)
- `schemas/` — kernel, profile, result, native-measurement, analytic-params JSON schemas
- `fixtures/` — runnable example kernels (`make_fixtures.py` regenerates them with independent expected values)
- `tests/` — synthetic model tests (`selftest`), plus empty `calibration/` and `heldout_native/` case directories
- `references/` — architecture model, input format, parameters, bounds, analytic scales, calibration procedure, sources, GCC pipeline mapping
- `INSTALL.md`, `CAPABILITY_REPORT.md`, `TEST_RESULTS.md`, `examples/`

Quick start:

```bash
python scripts/knc_twin.py capabilities --out out/caps
python scripts/knc_twin.py simulate fixtures/saxpy_4ctx.json --out out/saxpy4
python scripts/knc_twin.py bounds fixtures/reduce_1acc.json --loop --out out/mii
python scripts/knc_twin.py bounds --scale card --params fixtures/card_params_stream.json --out out/card
```

Every run writes `result.json` and `summary.md` into its own output directory with engine
version, profile hash, input hash, scale, calibration status, functional-check status,
assumptions, unsupported features, limiting constraints and the exact invocation.

Status: engine 0.1.0. `card-7120-measured` is built from the gcc_knc project's native
microbenchmarks; no end-to-end prediction has been validated against the card yet
(`references/calibration.md`). Simulated cycles are model results, never measurements.
