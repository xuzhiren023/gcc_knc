# Acceptance fixtures (reviewer-owned)

Claude owns this directory. GPT runs these fixtures but does not edit them. If
a fixture looks wrong, raise it in the sprint log with a reduced reason; do not
work around it. Story-level tests live in `tests/regress/` and belong to GPT.

An acceptance fixture passes only when every listed check passes. Each check
must be able to fail: if an expectation cannot go red, the fixture is wrong.

## `m1_affine/` — mixed scalar and vector program (Milestone M1)

Build `loops.c` (and `affine_fortran.f90` from Sprint 3) with the compiler under
test, in a separate translation unit from `driver.c`.

| Tier | Check | Expected |
|---|---|---|
| T1 | `loops.c` at `-O2 -ftree-vectorize -ffp-contract=off` | Assembles with `--march=k1om`, passes `tools/knc_lint` |
| T1 | `affine_f32`, `affine_f64` | Main loop uses `zmm` packed multiply and add, reported by `-fopt-info-vec` |
| T1 | `recurrence_f32` | No packed FP arithmetic on `zmm`; the loop stays scalar |
| T1 | same, with `-ffp-contract=fast` | Affine loops use `vfmadd*ps` / `vfmadd*pd` |
| T2 | Link `driver.c` + `loops.c` | ELF machine 181 (`EM_K1OM`), loader `/lib64/ld-linux-k1om.so.2`, no symbol version newer than the card provides |
| T3 | Run on the card | Exit 0, prints `ACCEPT-PASS scalar=3.00 failures=0` |
| T3 | Rerun with `driver.c` built by the donor GCC 5.1.1 and `loops.c` by the new compiler | Same result. This is the ABI cross-check |

Baseline measured 2026-11-01: donor GCC 5.1.1 at `-O3` produces only x87
arithmetic ("no vectype"), so this fixture is red until Sprint 3. The expected
Sprint 0 result is a recorded red for the right reason.

The fixture is only a demonstration of M1. It is not evidence of general
vectorization, and it says nothing about performance.

## `s3_tls_card/`: `__thread` shared between GCC 16 and the donor (S3-14)

`build.py OUTDIR` builds five programs. Run each one on the card with its library staged beside it:
`tools/card_run --file OUTDIR/libclaude-tlsV.so OUTDIR/claude-tlsV.mic`.

| Variant | Built how | Expected on the card |
|---|---|---|
| A | main and `tls_new` by GCC 16 at `-O2`; `tls_donor` and the `.so` by the donor | `S3-TLS PASS checks=59 failures=0` |
| B | as A, GCC 16 parts at `-O0` | same |
| C | main by the donor; `tls_new` and the `.so` by GCC 16 at `-O2` (global- and local-dynamic) | same |
| D | as C, GCC 16 parts at `-O0` | same |
| X | A with `-DCONTROL_SHARED`: plain globals instead of `__thread` | `S3-TLS FAIL`, exit 1 |

Each of 4 threads writes its own values through one compiler's code and reads them back through
the other's after a barrier; the main thread writes nothing and must still see the initial
values. The build refuses any GCC 16 object or library that references `__emutls`.

## `s4_masks/`: compares, masks, blends, conditional stores and tails (Sprint 4)

Build `loops.c` with the compiler under test at `-O2 -ftree-vectorize -fwrapv` and again at
`-O3 -fwrapv` (no `-ffast-math`). Build `driver.c` at `-O0 -fwrapv`, so the references are never
vectorized, and link the two with `-lm`. `-fwrapv` makes the integer wraparound rows defined.

The driver checks every kernel at lengths 0-65 and element offsets 0-15 (every fifth offset above
length 20), with each array flush against a `PROT_NONE` page on one side or the other.
- **Exact by bits:** compares, selects, conditional stores, `fabs`, the `a < b ? a : b` idioms and
  integer operations.
- **Arithmetic:** uses dyadic inputs whose results are exact, so x87 extended precision cannot
  change a reference.
- **`fmin`/`fmax`:** any NaN is accepted for a NaN result, and either zero sign for a ±0 pair,
  because C leaves both open.
- **Stray writes:** sentinels 256 bytes each side of every output catch a store outside the array.

| Tier | Check | Expected |
|---|---|---|
| T3 | Run on the card, each `loops.c` build | Exit 0; last line `S4-MASKS PASS failures=0` (an `INFO checks=` line precedes it) |
| T3 | `loops.c` with `-DNEGATIVE_CONTROL` (`cmp_lt_f32` uses `<=`) | Exit 1, `S4-MASKS FAIL` |
| T3 | `loops.c` with `-DGUARD_CONTROL` (`add_f32` reads one past the end) | Prints `S4-MASKS FAULT ... kernel=add_f32`, exit 3 |
| T3 | `loops.c` with `-DGUARD_AL_CONTROL` (`add_al_f32` reads one line past `b`) | Prints `S4-MASKS FAULT ... kernel=add_al_f32 ... where=2`, exit 3 |
| T3 | `loops.c` at `-O2 -ftree-vectorize -fvect-cost-model=unlimited` (S4-05) | As the first row; this forces the misaligned masked paths that the cost model normally avoids |

A fault in any build prints `S4-MASKS FAULT sig= kernel= n= o= where= addr=` and exits 3;
`addr=(nil)` is the misaligned-access fault of S3-03, a real address is a guard page.

The `*_al_*` kernels (S4-05) promise 64-byte alignment. The driver places each of their arrays so
the line after the last element is the guard page (`where=2`); a masked tail that names one line too
many faults there.

Which kernels must vectorize, and how, is each ticket's T1 (S4-02 compares, S4-03 selects and
idioms, S3-09 and S4-04 integers, S4-05 tails). This fixture checks only that whatever code the
compiler emits is exact and stays inside the arrays.

Before Sprint 4's code (lead, 2026-11-04): host Cygwin gcc at `-O2 -ftree-vectorize` (SSE2)
passes 1,576,200 checks; the negative control fails, and the guard control dies with SIGSEGV. With S4-05's aligned kernels: 1,589,070 checks, and the aligned guard control faults (lead, host).
GCC 16 at `knc` `0d3c0152fe3` faults on the card in `add_f32` (n=16, o=1, `addr=(nil)`): LRA
folds a misaligned load into `vaddps`. That is S4-09, and this fixture is red until it merges.
