# S12-24: ICE on a sign-alternating induction with a vector epilogue

Status 2026-11-14: reduced, root cause read in the source and the vect dump, fixed in the GCC
branch `s12/S12-24` (`e3c5b822619`). The test passes with both main loops vector (`vmulpd` and
`vmulps` on zmm). Not run on the card, and x86 identity not run.

## Reproducer

WRF `share/dfi.F`, REMEZ, `DO 130` (`K=-K` with `DDEN=DDEN+K*AD(J)/WT(L)`). Smallest form, at
`-O3 -march=knc` with no other option:

```c
void f (double *restrict a, double *restrict y, int n)
{ int k = 1; for (int j = 0; j < n; j++) { y[j] = k * a[j]; k = -k; } }
```

Test: `tests/t1/knc-vec-neg-induction.c`, run with
`python tools/check t1 --compiler gcc16 --neg-induction`.

## Root cause

- Statement: the PHI of the induction `k` (`vect_step_op_neg`).
- Vector type: `vector(16) int` (V16SI) for `int`. Also V8DI for `long`, and V16QI or V16HI for an
  `unsigned char` or `unsigned short` induction (seen with float and int elements).
- Transform: `vectorizable_nonlinear_induction` on the masked epilogue loop. The main loop (V8DF)
  transforms correctly.

`tree-vect-loop.cc` (16.2.0 lines 9312-9334) checks `directly_supported_p (NEGATE_EXPR, vectype)`
and `can_vec_perm_const_p` for the interleave only when the induction's start value is not a
constant. The epilogue is analysed before the main loop is transformed, when `k` still starts at the
constant 1, so the check is skipped. At transform time the epilogue's start value is the main
loop's result (an SSA name), the check runs, `NEGATE_EXPR` is not supported, the function returns
false and `vect_transform_stmt` asserts (`tree-vect-stmts.cc:13381`).

KNC fails the check because `neg<mode>2` in `sse.md` is `VI_AVX2` under `TARGET_SSE2` and `imci.md`
has no integer vector negate. `ix86_knc_vectorize_vec_perm_const` accepts the interleave.

Upstream `master` at `fceddda853f` (2026-11-14) has the same code. It is a latent
target-independent bug: x86 never reaches it because every SSE2 integer vector mode has a negate.

## Fix

In `vectorizable_nonlinear_induction`, the negate and interleave check now also runs when the
start value may not be the analysed constant at transform time: `LOOP_VINFO_EPILOGUE_P`, and a
peeled alignment prologue (`LOOP_VINFO_PEELING_FOR_ALIGNMENT` nonzero without
`vect_use_loop_mask_for_alignment_p`). Analysis then rejects what the transform cannot build.

The check is slightly wider than the ICE: an epilogue whose main loop has no skip guard (known
iteration count) keeps a constant start and compiled before, and is now also rejected when the
target lacks the negate or the interleave. Whether the guard exists is decided in
`vect_do_peeling`, after the epilogue is analysed. A target with both operations in every integer
vector mode it vectorizes with sees no change, since the check passes wherever it now runs.

A KNC-only `negv16si2`/`negv8di2` is not a general fix: V16QI and V16HI inductions would still
ICE.

## Finding for a separate ticket

KNC has no integer vector negate, so `x[i] = -y[i]` on integers is not vectorized, and after the
planned fix these loops get a scalar epilogue instead of a masked one.
