# libknc_vmath

GCC-KNC's vector math library (ADR-0014 point 3, S10-02): the copied algorithms (ADR-0011) for
`expf`, `logf`, `powf` (16 lanes) and `exp`, `log`, `pow` (8 lanes), as pointer-form cores
`__knc_vmath_core_<name>_<lanes>` behind the by-value entry points `__knc_vmath_<name>_<lanes>`
(`knc_vmath.h`, S10-03). Loops compiled with `-mveclibabi=knc` (the `-march=knc` default) call the
entry points, and the KNC driver names the installed `libknc_vmath.a` in every link.

| Member | Copied source |
|---|---|
| `vmath_expf.c`, `vmath_logf.c` | `math_algorithms/e_width_experiment/e_expf.c`, `e_logf.c` |
| `vmath_exp.c`, `vmath_log.c` | `math_algorithms/e_width_experiment/e_exp.c`, `e_log.c` |
| `vmath_powf.c`, `vmath_pow.c` | `math_algorithms/powf_e16/powf_e16.c`, `pow_e8/pow_e8.c` |
| tables | Arm `exp_data.c`, `log_data.c`, `exp2f_data.c`, `pow_log_data.c`, `powf_log2_data.c` |

v1a (S10-07) adds the other copied algorithms, each with a masked entry point
`__knc_vmath_<name>_<lanes>_m(x, mask)` (ADR-0014 point 4): a clear mask bit returns that lane of
the first argument (`y` for atan2) unchanged.

| Member | Functions | Copied source |
|---|---|---|
| `vmath_sincos.c` | sinf, cosf (16); sin, cos (8) | `math_algorithms/cos_sin_e/cos_sin_e.c` |
| `vmath_tan.c` | tanf (16); tan (8) | `math_algorithms/tan_e/tan_e.c` |
| `vmath_reducer.c` | the argument reduction of the two above | `math_algorithms/cos_sin_e/reducer.c` (musl `__rem_pio2`) |
| `vmath_log10f.c`, `vmath_log10.c` | log10f (16); log10 (8) | `math_algorithms/log10_e/e_log10f.c`, `e_log10.c` |
| `vmath_atan.c` | atanf, atan2f (16); atan2 (8) | `math_algorithms/atan_e/atan_e_v2.c` |
| `vmath_hyperbolic.c` | sinhf, coshf, tanhf (16); sinh, cosh, tanh (8) | `math_algorithms/hyperbolic_e/hyperbolic_e.c` |

The copy has no 8-lane atan, so a double `atan` loop keeps its scalar call. `hyperbolic_e` has no
inverse functions. `bounded_f32.h` and `bounded_f64.h` declare only 4-lane exp and log on bounded
ranges, which v0's full-range exp and log cover. `hyperbolic_e.c` is edited: its double-double
helpers pass pointers, as GCC-KNC has no convention for a struct of two 64-byte vectors by value
(`hyperbolic_e/NOTICE`).

These are the plain cores, the ones the accepted float harness already used. The receipts' `exp`,
`log` and `pow` were the `register_i64` rewrites, which avoid gathers for PhiWeather's translation
route; GCC-KNC needs no such rewrite, and both implement the same Arm algorithm.

Build: `python tools/knc_vmath.py` (KNC into `.work/_shared/S10-02/knc`, host into `.../host`;
`--out T` for `.work/_shared/T`).
`-O2`, GCC's default contraction, no fast-math; the KNC members are `-fPIC` with hidden symbols,
as in `libgcc.a`, so the archive also links into shared libraries. `--install` copies the KNC
archive beside `libgcc.a` in this lane's build tree and installed prefix
(`tools/s7_09_checks.py install` does it after replacing the prefix). `pow_e8.c` passes 64-byte vectors between its
static helpers by value, so it needs S10-01's vector ABI in the compiler.

Qualification: `python tests/vmath/card_qualify.py` (card, lead only) or `--host`. `expf`, `logf`
and `powf` run the accepted harness (`tests/acceptance/vecmath_qualify/qualify.c`) linked to these
cores; `exp`, `log` and `pow` run `tests/vmath/qualify_d.c`, whose x87 screen dumps every lane above
0.5 ULP for an exact recheck on the host (Python decimal, 60 digits). The v1a functions run
`tests/vmath/qualify_v1.c` through the entry points: exact against MPFR on the host, and on the card
a long double screen whose dumped lanes the host program rechecks exactly; special cases come from
its C99 Annex F table.

## Expected limits

From the PhiWeather receipts (`../receipts`): targets, not evidence (ADR-0011 point 4). The pass
limit is 1 ULP, round to nearest, all lanes, IEEE special values (ADR-0014 point 4).

| Function | Receipt maximum (ULP) | Receipt field |
|---|---|---|
| expf | 0.5016 | `knc-g5-expf.json` finiteNonidenticalMaximumIntervalBoundUlpsApprox |
| logf | 0.7754 | `knc-g5-logf.json` maximumConservativeTrueErrorUlps (a bound, not an observed error) |
| powf | 0.5051 | `knc-g5-powf.json` maximumInheritedTrueErrorUlps |
| exp | 0.5054 | `knc-g5-exp-i64.json` maximumConservativeTrueErrorUlps |
| log | 0.5102 | `knc-g5-log-i64.json` maximumConservativeTrueErrorUlps |
| pow | 0.5068 | `knc-g5-pow-i64.json` maximumCertifiedTrueErrorUlps |

v1a, with the host result (x86-64 build, MPFR-exact, `card_qualify.py --host`, 2026-11-11: 2^16 sweep
blocks and 2^16 dense blocks per function, 2^16 pair blocks for atan2; no special-case or mask
error). The card has not run these.

| Function | Precision | Source | Receipt maximum (ULP) | Receipt field | Host maximum (ULP) |
|---|---|---|---|---|---|
| sinf | float, 16 | `cos_sin_e/cos_sin_e.c` | 0.5000 | `knc-g5-sinf.json` maximumInheritedTrueErrorUlps | 0.500000 |
| cosf | float, 16 | `cos_sin_e/cos_sin_e.c` | 0.5000 | `knc-g5-cosf.json` maximumInheritedTrueErrorUlps | 0.500000 |
| tanf | float, 16 | `tan_e/tan_e.c` | 0.5000 | `knc-g5-tan2-v5.json` worstErrorUlps | 0.500000 |
| log10f | float, 16 | `log10_e/e_log10f.c` | 0.8189 | `knc-g5-narrow14-v2.json` worstErrorUlps | 0.806986 |
| atanf | float, 16 | `atan_e/atan_e_v2.c` | 0.5000 | `knc-g5-atan3-finite-div-v7.json` worstErrorUlps | 0.500000 |
| atan2f | float, 16 | `atan_e/atan_e_v2.c` | 0.5000 | `knc-g5-atan3-finite-div-v7.json` worstErrorUlps | 0.500000 |
| sinhf | float, 16 | `hyperbolic_e/hyperbolic_e.c` | 0.5000 | `knc-g5-hyperbolic6-v6.json` worstErrorUlps | 0.500000 |
| coshf | float, 16 | `hyperbolic_e/hyperbolic_e.c` | 0.5000 | `knc-g5-hyperbolic6-v6.json` worstErrorUlps | 0.500000 |
| tanhf | float, 16 | `hyperbolic_e/hyperbolic_e.c` | 0.5000 | `knc-g5-hyperbolic6-v6.json` worstErrorUlps | 0.500000 |
| sin | double, 8 | `cos_sin_e/cos_sin_e.c` | 0.7712 | `knc-g5-sin-i64.json` maximumCertifiedTrueErrorUlps | 0.760933 |
| cos | double, 8 | `cos_sin_e/cos_sin_e.c` | 0.7589 | `knc-g5-cos-i64.json` maximumCertifiedTrueErrorUlps | 0.766517 |
| tan | double, 8 | `tan_e/tan_e.c` | 0.7574 | `knc-g5-tan2-v5.json` worstErrorUlps | 0.825883 |
| log10 | double, 8 | `log10_e/e_log10.c` | 0.5308 | `knc-g5-log10-i64.json` maximumCertifiedTrueErrorUlps | 0.609776 |
| atan2 | double, 8 | `atan_e/atan_e_v2.c` | 0.9181 | `knc-g5-atan3-finite-div-v7.json` worstErrorUlps | 0.876863 |
| sinh | double, 8 | `hyperbolic_e/hyperbolic_e.c` | 0.5310 | `knc-g5-hyperbolic6-v6.json` worstErrorUlps | 0.517798 |
| cosh | double, 8 | `hyperbolic_e/hyperbolic_e.c` | 0.5332 | `knc-g5-hyperbolic6-v6.json` worstErrorUlps | 0.524547 |
| tanh | double, 8 | `hyperbolic_e/hyperbolic_e.c` | 0.5000 | `knc-g5-hyperbolic6-v6.json` worstErrorUlps | 0.500000 |
| atan | double, 8 | none in the copy | | | not implemented |
| `bounded_f32.h`, `bounded_f64.h` | 4 lanes | expf, exp, log on bounded ranges | | | v0 covers them |

cos, tan and log10 pass the 1 ULP limit but exceed their receipt's maximum on this input set (by
0.008, 0.068 and 0.079 ULP).

The receipts' input sets differ from ours (about 1.3 million lanes each), so a card maximum a little
above a receipt's on a larger set is not by itself a regression; above 1 ULP is a failure.

Screen limits: the x87 screen's error is shown as `screen error` per job. Cygwin's `powl` is off by
up to 0.45 double ULP, so on the host the undumped pow lanes are bounded only by 0.95 ULP; glibc's
`powl` on the card is expected to do better. Within 2^-64 of a power of two the screen can halve an
error (it rounds the reference onto the power), which the exact recheck corrects for dumped lanes.
