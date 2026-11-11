# libknc_vmath v0

GCC-KNC's vector math library (ADR-0014 point 3, S10-02): the copied algorithms (ADR-0011) for
`expf`, `logf`, `powf` (16 lanes) and `exp`, `log`, `pow` (8 lanes), as pointer-form cores
`__knc_vmath_core_<name>_<lanes>` (`knc_vmath.h`). The by-value entry points
`__knc_vmath_<name>_<lanes>` come with S10-03.

| Member | Copied source |
|---|---|
| `vmath_expf.c`, `vmath_logf.c` | `math_algorithms/e_width_experiment/e_expf.c`, `e_logf.c` |
| `vmath_exp.c`, `vmath_log.c` | `math_algorithms/e_width_experiment/e_exp.c`, `e_log.c` |
| `vmath_powf.c`, `vmath_pow.c` | `math_algorithms/powf_e16/powf_e16.c`, `pow_e8/pow_e8.c` |
| tables | Arm `exp_data.c`, `log_data.c`, `exp2f_data.c`, `pow_log_data.c`, `powf_log2_data.c` |

These are the plain cores, the ones the accepted float harness already used. The receipts' `exp`,
`log` and `pow` were the `register_i64` rewrites, which avoid gathers for PhiWeather's translation
route; GCC-KNC needs no such rewrite, and both implement the same Arm algorithm.

Build: `python tools/knc_vmath.py` (KNC into `.work/_shared/S10-02/knc`, host into `.../host`).
`-O2`, GCC's default contraction, no fast-math. `pow_e8.c` passes 64-byte vectors between its
static helpers by value, so it needs S10-01's vector ABI in the compiler.

Qualification: `python tests/vmath/card_qualify.py` (card, lead only) or `--host`. `expf`, `logf`
and `powf` run the accepted harness (`tests/acceptance/vecmath_qualify/qualify.c`) linked to these
cores; `exp`, `log` and `pow` run `tests/vmath/qualify_d.c`, whose x87 screen dumps every lane above
0.5 ULP for an exact recheck on the host (Python decimal, 60 digits).

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

The receipts' input sets differ from ours (about 1.3 million lanes each), so a card maximum a little
above a receipt's on a larger set is not by itself a regression; above 1 ULP is a failure.

Screen limits: the x87 screen's error is shown as `screen error` per job. Cygwin's `powl` is off by
up to 0.45 double ULP, so on the host the undumped pow lanes are bounded only by 0.95 ULP; glibc's
`powl` on the card is expected to do better. Within 2^-64 of a power of two the screen can halve an
error (it rounds the reference onto the power), which the exact recheck corrects for dumped lanes.
