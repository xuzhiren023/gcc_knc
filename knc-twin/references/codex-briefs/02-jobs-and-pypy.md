# Codex ticket brief: knc-twin, `--jobs N` and PyPy

For the GCC-KNC lead to dispatch on a Codex lane (backend codex, depth standard; model per
`harness/policy.json`). Branch `twin/0.3` of gcc_knc, folder `knc-twin/`. Owner request 2026-11-16,
relayed by the GCC-KNC lead: these two need few source changes.

## 1. `--jobs N`

Add a `--jobs N` flag (default 1) to every command that runs several independent simulations:
`knc_twin.py batch`, `knc_twin.py rollup`, `scripts/validate_heldout.py` (the characterization rows,
and the compiled cases' variants), `examples/run_examples.py`, `tests/heldout_native/wrf_coverage.py`.
Rules:

- Standard library only: `multiprocessing` with the `spawn` start method (Windows is the reference
  host). Each worker runs one whole simulation; no threading inside a simulation; one simulation is
  one process.
- Results byte-identical for any N: the output order and every file written (`result.json`,
  `batch.md`, `validation.json`, `prediction.json`, `RESULTS.md`) must not depend on N or on
  worker timing. Timestamps and `python_execution_seconds` are the only fields allowed to differ;
  make the comparison ignore exactly those and nothing else.
- Errors from a worker are reported as the same status the single-process path reports; a crashed
  worker is a `error` row, never a silently missing one.
- One test in `tests/test_cli.py`: the S12-30 batch (`fixtures/batch/manifest.json`) with `--jobs 1`
  and `--jobs 4`, comparing `result.json` and `batch.md` after removing the two timing fields; and
  one test for `validate_heldout.py --cases tests/heldout_native --only-cases s12-30-small` at
  1 and 4 jobs comparing the recorded predictions.

## 2. PyPy

- Install PyPy (owner approved the download) beside CPython; CPython 3.8 stays the reference
  interpreter. Record the PyPy version and where it was installed in `INSTALL.md`.
- Run `knc_twin.py selftest` and `examples/run_examples.py` under PyPy. Fix only genuine
  incompatibilities in the twin's own code; list each in `TEST_RESULTS.md` with the file and line.
  Do not change semantics to suit PyPy: results must be byte-identical between the two interpreters
  (compare `result.json` without the timing fields for every example).
- Speed: time `simulate` on `fixtures/saxpy_4ctx.json`,
  `tests/heldout_native/s12-31-hpcg-toy/kernels/knc_spmv.json`,
  `tests/heldout_native/s12-30-small/kernels/csr27-knc-switch-off.json` and one `validate_heldout.py
  --only-cases s12-31-microbench` run, under both interpreters; report `python_execution_seconds`
  and the simulated instructions per second in `TEST_RESULTS.md` as a table. Timing runs load the
  host: do them only after the lead says M4 is done.
- `INSTALL.md`: how to run under PyPy (`pypy3 scripts/knc_twin.py ...`), with the caveat that the
  reference numbers in `references/validation.md` are CPython's (and that they are identical under
  PyPy, once shown).

## Done when

- `--jobs` exists on the listed commands with the two identity tests green; the default behaviour is
  unchanged.
- PyPy results are byte-identical and the speed table is in `TEST_RESULTS.md`, or the
  incompatibilities are listed with their fix or their reason.
- Host rule until the lead says M4 is done: code and small tests only, two single-threaded processes
  at most; speed and validation comparisons afterwards.
