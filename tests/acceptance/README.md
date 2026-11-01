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
