# Vector math qualification harness (parked for E7-02)

Requalifies the copied 16-lane `expf`, `logf` and `powf` cores (`contrib/knc-vecmath/`, ADR-0011
point 4) as built by GCC-KNC. Written 2026-11-06 and parked by the owner ("Park it, commit"): it is
E7 work (Milestone M4), not Sprint 6. Nothing has run on the card.

- `build.py` compiles the pointer-form cores (`phi_host_*_e16`) at `-O2` with GCC's default
  contraction, the Arm data tables, and `qualify.c` (no vectorization, no contraction), into
  `.work/_shared/vecmath-qualify/qualify.mic`, and lints it.
- `qualify.mic expf|logf|powf` checks results against the card's x87 `expl`, `logl` and `powl`, in
  float ULPs. `expf` and `logf` cover all 2^32 inputs, or every `--block-stride`-th block of 16.
  `powf` uses `--pow-count` random pairs plus a grid of special pairs. One block in 64 also runs
  with a random mask and merge values. It passes at max 1 ULP with no special-value, status or mask
  errors. Round-to-nearest only; errno and FP flags are not checked.
- Negative controls: `--negative` flips one result bit per block; `--negative-mask` corrupts an
  inactive lane. Both must fail.

Host dry run (Cygwin GCC 14, x86-64 build of the same sources, so it tests the harness, not
GCC-KNC's code): `expf` max 0.5016 ULP, `logf` 0.5080, `powf` 0.5036, all PASS; both negative
controls FAIL as required.

Card plan when E7-02 starts: negative controls, a calibration run at `--block-stride 4096`, then
each function sized from the calibration (a full 2^32 sweep is likely hours at 80 threads).
