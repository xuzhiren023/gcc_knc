# s5_ops: Sprint 5 acceptance fixture (lead-owned)

Conversions, permutes, reductions, gather and scatter, and division and square root. The kernels
are in `loops.c`, built by the compiler under test with vectorization on. The references and checks
are in `driver.c`, built at `-O0 -fwrapv`, never vectorized, and linked with `-lm`.

Every kernel is checked:
- at every length 0-65 and element offset 0-15 (every fifth offset above length 20);
- with each array flush against a `PROT_NONE` page, on the low side and on the high side;
- with 256-byte sentinels around each output array.

What each kernel must do:

- **Conversions:** bit-exact against single-rounding scalar references.
  - Float-to-int inputs stay inside the defined range.
  - `cvt_i64_f64` has no IMCI form and is expected to stay scalar.
- **Permutes:** bit copies. `cmul_f32` uses dyadic inputs, so every product and sum is exact.
- **Reductions:** equal to the in-order reference.
  - FP inputs are dyadic, so the sum is exact in any order. That checks the reduction tree, the
    lane handling and the tails, not the ordering.
  - That FP sums are not reassociated without `-fassociative-math` is a T1 scan, not a native
    check. Today GCC 16 emits an in-order fold (vector multiply, then sequential x87 adds) for
    `dot_f32` at `-O2`.
- **Gathers:** read a table of 1-64 elements flush against a guard page, with indices covering both
  ends and duplicates.
- **Masked gathers and masked scatters** (`mgat_*`, `msca_f32`): the indices of inactive lanes
  point into a guard page. A vector form that touches an inactive lane faults (`S5-OPS FAULT`).
- **Scatters:** run once with a permutation and once with duplicate indices. With duplicates, the
  last write in source order must win.
- **Division and square root:** must be correctly rounded (ADR-0003 point 4).
  - FP32 is checked against division and square root in double, which is innocuous double
    rounding (53 >= 2·24+2). Inputs include subnormals and specials.
  - FP64 is decided exactly in 128-bit integers from the mantissas: the residual against half the
    gap to the neighbour. Operands are normal, with exponents within ±200. A separate set covers
    special operands.
  - Scalar x87 code on the card runs at 64-bit precision, so its FP64 quotients and roots are
    rounded twice and are not always correctly rounded (S5-03). An FP64 element equal to that
    double-rounded x87 value is therefore accepted, because it came from a scalar peel or
    remainder.
  - Under `-ffast-math` (the `fast` row), the division, square-root and FP32/FP64 conversion
    checks are skipped, and the driver prints an `INFO` line instead. `crtfastmath` sets DAZ and
    FTZ, and reciprocal approximation is allowed there.

## Builds

Driver: `xgcc -march=knc -O0 -fwrapv -c driver.c`, then link with each `loops.c` build and `-lm`.

| Name | `loops.c` flags | Expected |
|---|---|---|
| `o2v` | `-O2 -ftree-vectorize -fwrapv` | `S5-OPS PASS failures=0` |
| `o3` | `-O3 -fwrapv` | PASS |
| `fast` | `-O3 -ffast-math -fwrapv` | PASS, with fewer checks (FP reductions may reassociate; inputs are exact) |
| `neg` | `-O2 -ftree-vectorize -fwrapv -DNEGATIVE_CONTROL` | FAIL in `div_f32`, `sqrt_f32`, `div_f64`, `sqrt_f64` and both special sets |

Host check (Cygwin GCC 14, x86_64, 2026-11-05):
- `o2v` passes 767,184 checks;
- `fast` passes 589,584 checks;
- `neg` fails all six division and square-root checks.

## Baseline at GCC `knc` `c759f17f1b9` (Sprint 4 head)

At `-O2 -ftree-vectorize`:
- The integer reductions already vectorize: `sum_i32`, `sum_i64`, `min_i32`, `max_i32`,
  `max_u32`, `and_i32`, `or_i32` and `xor_i32`.
- `dot_f32` vectorizes its multiply with an in-order x87 fold.
- Every other kernel is scalar.

At `-O3 -ffast-math`, `sum_f32`, `sum_f64` and `dot_f32` also vectorize.
