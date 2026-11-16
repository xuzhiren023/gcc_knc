# Test results, knc-twin 0.3.0

Status on 2026-11-16 (host: Windows 10, Python 3.8.5). Model tests plus checks against independent
oracles; they are not validation against hardware (that is `references/validation.md`).

## What ran after the last engine change

`python -m unittest test_fp test_asm test_functional test_bounds test_timing test_extended test_v03`
in `tests/`: 123 tests, 0 failures, 0 errors. `tests/trial/knc_trial.py` cases: 16 of 16 convert
and check as recorded.

## What did not rerun

The full `knc_twin.py selftest` (which adds `test_cli`, 14 tests that drive every command through
the CLI, including the S12-30 batch) and `examples/run_examples.py` were stopped on 2026-11-16 at the
GCC-KNC lead's request (no CPU load on the laptop during the M4 card block). The last complete
`test_cli` run before the final two fixes had 2 errors from a result-serialization bug that the
fixes removed, and 12 passes. Both runs are the first thing to repeat when the window opens; until
then the figures above are the evidence.

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
