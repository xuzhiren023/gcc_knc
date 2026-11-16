# Test results, knc-twin 0.3.1

Status on 2026-11-16 (host: Windows 10, Python 3.8.5). Model tests plus checks against independent
oracles; they are not validation against hardware (that is `references/validation.md`).

## Runs on the final engine (2026-11-16)

- `python scripts/knc_twin.py selftest` (0.3.1): 154 tests, 0 failures, 0 errors (test_fp 14, test_functional 13,
  test_asm 4, test_bounds 9, test_timing 24, test_extended 19, test_cli 14, test_v03 42, test_wrf_forms 15).
  test_wrf_forms checks the IMCI forms PhiWeather's WRF loops use against the R27 operation descriptions:
  exponent and mantissa extraction (intervals, sign control, denormals, specials), scaling with rounding
  overrides and range, vgmax/vgmin NaN and signed-zero rules, named integer predicates and blend, MXCSR
  contents and flag accumulation with {sae} suppression, x87 memory compares, the approximate reciprocals'
  special values and marking, the fix-up token table.
- `examples/run_examples.py` (`examples/RESULTS.md`): 41 commands, 34 ok and 7 with the intended non-ok
  status and exit code (functional_mismatch 6, needs_parameters 7, unsupported 3, missing_parameter 4 twice,
  budget_exhausted 5, incompatible 8). New examples: HPCG ComputeSPMV_ref from the linked S12-31 binary,
  the S12-31 row loop behind a 13-byte prefixed NOP and with the compare next to its jump, the roll-up,
  the calibration plan, the 3120 profile.
- `tests/trial/knc_trial.py` cases: 16 of 16 convert and check as recorded.
- `scripts/validate_heldout.py --cases --record`: see `references/validation.md`.

Two defects found by these runs and fixed before the commit: `bounds` with a functional trace wrote an
unreadable result.json (an internal object leaked into the result), and `prepare-native` built one contiguous
memory image from the lowest to the highest address a kernel touched, which for the S12-30 batch kernels
(data sections 500 MB away from the arrays) consumed 24 GB; the image is now capped at 32 MiB with a
clear error and the batch kernels place their arrays next to the data sections (the batch runs in 9 s).

## New in 0.3 (`tests/test_v03.py`, 40 tests)

- parser forms: symbolic immediates, `%fs:` thread-local access, segment rejection, disassembler
  spellings, indirect jumps rejected, the lock family;
- semantics: locked read-modify-write exact, `fxam` classes and `sahf`, `vpmadd231d`, one cache
  line per gather execution and the `all` policy;
- calls and stubs: in-region call and return, missing sentinel, undeclared callee, stub without a
  cost stops the timing, stub cost charged and marked inexact, noreturn reached, memcpy exact and
  sqrt correctly rounded;
- input binding: file blocks (raw and text), file-based expected values, missing file;
- front end and pairing: x87 issues alone (gas vs adj order, two cycles per iteration), an
  instruction before the compare takes it as partner, slow-prefix decode delays (one hidden, two per
  further prefix), NOPs never pair, forward taken branch core bubble only with several threads and
  none for loop back-edges, cold instruction cache;
- store and gather rules: load four cycles after a store and paired with the next store, the
  store-to-load data path unchanged, eleven cycles per line for a scattered gather, memory
  sub-models on by default;
- layout and binary adapter: encoding facts (prefixes, displacement, immediate), the HPCG SpMV
  object converts complete with padding, prefixes, a noreturn stub, string symbols and constants;
- roll-up arithmetic, the bandwidth floor, share validation, the decision bar, transferred
  profiles run and say so.

Earlier suites (test_fp 14, test_functional 13, test_asm 4, test_bounds 9, test_timing 24,
test_extended 19) are unchanged except where the model changed: gather fixtures now use the
completion loop, memory-latency assertions read the profile, `fsqrt` has a labelled prior instead
of stopping, x87 memory-operand chains pay the operand read plus the operation.
