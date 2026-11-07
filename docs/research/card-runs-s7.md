# Card runs, Sprint 7

## S7-06: shared libgcc on the card (20:10-20:11Z on 2026-11-07)

S7-05's payloads (`.work/_shared/S7-06`, staged flat with a launcher that rebuilds `donor/` and
`candidate/` and runs S7-05's `run.sh` unchanged; explicit loader `--library-path`, `LD_*` unset, no
system library touched). Card glibc 2.21, kernel 2.6.38.

- Donor `libgcc_s.so.1`: `old-compat`, `new-compat`, `old-unwind` match their expected output.
- Candidate (S7-04's `libgcc_s.so.1`): `old-compat`, `new-compat`, `old-unwind`, `new-helpers` match.
  `old-unwind` covers cross-DSO throw/catch both ways, backtrace across a DSO, signal unwind through
  the trampoline, pthread cancellation with two cleanups, and three dlopen/dlclose frame-registration
  cycles. `new-helpers` needs exports the donor lacks, so its pass shows the candidate directory is
  the one loaded; the other programs use the same explicit search path but do not print which copy
  they loaded.
- No loader failure and no unsupported-instruction fault.
