# knc-twin

A portable functional and timing twin of one Intel Xeon Phi Knights Corner (K1OM / IMCI) core,
with analytical pair and card scenario models, packaged as a Claude skill. Python 3.8+,
standard library only.

- `SKILL.md` — the skill entry point and workflow Claude follows
- `scripts/knc_twin.py` — CLI: capabilities, selftest, validate, functional, simulate, bounds, compare, batch, rollup, calibration-plan, prepare-native, import-native
- `scripts/from_binary.py` — binary adapter: K1OM object or executable plus its `objdump -dr` listing to a kernel with code layout, calls and returns (preferred)
- `scripts/from_gcc_s.py` — compiler-output adapter: GCC-KNC / GCC 5.1.1 assembly to kernel records, with a coverage audit
- `scripts/validate_heldout.py` — held-out validation against the gcc_knc characterization catalog
- `scripts/knc_model/` — engine (profiles, ISA table, exact FP, interpreter, cache scenarios, core timing, bounds, analytic scales, native export)
- `profiles/` — hardware parameters with provenance (common rules; the measured x100 core layer; 7120 measured; 5110P and 3120 with transferred core timing; synthetic demo; sensitivity overlays)
- `schemas/` — kernel, profile, result, native-measurement, analytic-params JSON schemas
- `fixtures/` — runnable example kernels (`make_fixtures.py`), real compiled functions (`fixtures/gcc/`, `fixtures/binary/`), the S12-30 gate candidate batch (`fixtures/batch/`) and a roll-up example (`fixtures/rollup/`)
- `tests/` — model tests and oracle checks (`selftest`); `tests/heldout_native/` holds the measured characterization tables, the compiled-code cases built from the binaries that ran on the card, and the comparison run
- `references/` — architecture model, input format and adapter, parameters, validation, bounds, analytic scales, calibration procedure, sources, GCC pipeline mapping
- `INSTALL.md`, `CAPABILITY_REPORT.md` (implemented vs not, coverage of real output, native time displaced), `AUDIT.md`, `TEST_RESULTS.md`, `examples/`

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

Status: engine 0.3.0. `card-7120-measured` is built from the gcc_knc project's native
microbenchmarks; its predictions are compared with 119 measured characterization rows and with
compiled code from the binaries that ran on the card (S12-31 row loops and HPCG kernels, S12-30
sparse products). `references/validation.md` gives the held-out error, the ranking reliability
and the decision bar (median error at most 10%, right winner in at least 90% of pairs more than
5% apart, at least 50 compiled loops) with its current verdict. Every result carries a class:
conditional bound, unvalidated scenario estimate, or calibrated forecast for a validated shape.
Simulated cycles are model results, never measurements; the twin ranks changes, the card decides.
