# Card runs, Sprint 5

Every job here was run by the lead through `tools/card_run` (cores 40-59). Each ran only when the
shared ledger showed no open timed job of the PhiWeather tuning session, and after it had
announced the end of its block. No timing figures are recorded.

## 2026-11-05: S5-04's runner, `s5_ops` baseline, S5-01 and S5-02 probes

`card_run` after S5-04: `hello` prints `hello from KNC` (`claude-44abcc97…`), and our ledger rows
now carry `"project": "gcc-knc"`.

**`s5_ops` at the Sprint 4 head** (GCC `knc` `c759f17f1b9`, `cc1` `2818504de6f7…`), with the
driver revised for S5-03's findings:

| Build | Result | Job |
|---|---|---|
| `o2v` | PASS, 767,184 checks | `claude-62255246…` |
| `o3` | PASS, 767,184 | `claude-d7d190c3…` |
| `fast` | PASS, 589,584 (div/sqrt and FP32/FP64 conversions skipped) | `claude-682d8c88…` |
| `neg` | FAIL as designed in `div_f32`, `sqrt_f32`, `div_f64`, `sqrt_f64` and both special sets | `claude-d674477c…` |

Most kernels are scalar at this head, so this proves the fixture, its guard pages and its
references on hardware, not new compiler work.

**S5-01 gather probe** (`tests/regress/knc-gather-probe.c`, `claude-a88a8b70…`): 184 checks
`ok`, none `FAIL`. Settled:

- **Masked-off lanes neither fault nor write.** All four gathers and all four scatters were run
  with masked-off lanes pointing into `PROT_NONE` pages, at lane 0, a middle lane and the last
  lane, and with an empty mask. Ordinary masked moves do fault (S3-03); gathers and scatters do
  not.
- **A gather or scatter resumed after a page fault completes correctly.** The handler opened the
  page and returned. Before the fault, lanes were done in lane order: an abandoned scatter that
  faulted on lane k had stored exactly lanes 0 to k-1.
- **With duplicate scatter indices, the highest active lane wins.** That holds within one line,
  across 2 and 4 lines (separate re-executions), under mask `0x5555`, and around a fault.
- **Indices are scaled at address width**, as GCC's `gather_load` assumes: index `0x20000000`
  with scale 4 is not wrapped to 32 bits. Negative indices are sign-extended.
- **`vgmaxps`/`vgminps`/`vgmaxpd`/`vgminpd`/`vgmaxabsps`** match the manual's pseudocode in all
  64 cases, NaN operand order included.

**S5-02 convert probe** (`tests/regress/knc-convert-probe.c`):
- The first run (`claude-63aef1fd…`) died with SIGILL at `vcvtfxpntps2dq` imm 4. Immediate bit 2
  is reserved, not "use MXCSR". The lead limited the probe to imm 0-3.
- The rerun completed (`S5-02 done`). Settled:
  - **Float to int with imm 3 (rz) truncates and raises IE** for NaN (result 0), ±inf, and every
    finite out-of-range input (saturated to `0x7fffffff`/`0x80000000`, or `0xffffffff`/0 for the
    unsigned forms). It raises PE for inexact inputs, and nothing for exact ones (`-2^31`
    included). Vector `(int) f` is therefore IEEE-correct under the default `-ftrapping-math`,
    and C leaves the value of the undefined cases open.
  - **Immediate bits 1:0 select rn/rd/ru/rz whatever MXCSR.RC is.** Int to float and
    `vcvtpd2ps` round by MXCSR.RC.
  - **`vcvtpd2ps` flags:** overflow gives inf with OE|PE; a tiny inexact result gives UE|PE; an
    exact float subnormal raises nothing; sNaN raises IE and is quieted, and a qNaN keeps its
    payload truncated. `vcvtps2pd` of a float subnormal raises DE only.
  - The 8-lane forms read lanes 0-7. Under mask `0x000f`, `vcvtfxpntpd2dq` and `vcvtpd2ps` keep
    lanes 4-7 and zero lanes 8-15.
  - **Up-converting loads and down-converting stores** of 16 or 32 bytes touch only those bytes.
    They are safe at the very end of a page, and fault on a misaligned address (`si_code=128`).
    A mask does not stop a fault on an unmapped page.
  - **Down-converting integer stores saturate** (`model=saturate`), so C's modular `(uint8_t)`
    needs the AND first, as ADR-0008 point 7 says.
  - **The unaligned `vloadunpackl/hd` and `vpackstorel/hd` `{uint8}` pairs fault at a page end**
    even for a 16-byte stream: the h half touches the next line (`phase=1`). Any compiler use must
    guard the h half, as S4-14 does.

## 2026-11-05: S5-06 merged, S5-09 estimate probe

GCC `knc` `5554500ffb7` (the S5-06 merge), `cc1` `147c34fe5b78…`. All 16 shuffle recipes and the
reversed and stride-2 kernels are vectorized. `s5_ops` passes:
- `o2v`: 779,984 checks (`claude-e82e58aa…`);
- `o3`: 779,984 checks (`claude-21bfeac6…`);
- `fast`: 602,384 checks (`claude-13b9c1b8…`).

That includes every lane of every shuffle recipe against its selector. `s4_masks` still passes
1,589,070 checks at `-O2 -ftree-vectorize` (`claude-91bbb9cd…`) and `-O3` (`claude-375c5e45…`).

**S5-09 estimate probe** (`tests/regress/knc-estimate-probe.c`, `claude-6b23d83b…`), all items `ok`:
- `vrcp23ps`: the maximum error over all 2^23 significands is 0.8991 ulp, under the manual's 0.912.
- `vrsqrt23ps`: the maximum over all 2^24 values in [1/2,2) is 0.7123 ulp, under 0.775. So the
  FP32 division and square-root proofs (S5-03) hold for this hardware.
- `vgetmantps`/`vgetmantpd` normalize subnormal inputs with DAZ=0, as the manual's prose says,
  not as its pseudocode reads (1,024 and 1,952 cases).
- A masked-off lane raises no flag: no #Z for `rcp(0)`, and no #I for `rsqrt(-1)` or an sNaN.
- `vrcp23ps(0x3FFFFFFF)` returns `0x3F000001`, round to nearest. So S5-03's step 15 is not needed
  on this part; the sequence keeps it anyway, because the proof must not rely on that.

## 2026-11-05: S5-07 merged (reductions, the first Codex ticket)

GCC `knc` `bb2dffd3b06`. The integer reductions and the fast-math FP sums now end in a
`vpermf32x4` and swizzle tree (18 `vpermf32x4` in `s5_ops` at `-O3`). `s5_ops` passes:
- `o2v`: 779,984 checks (`claude-32c1f857…`);
- `o3`: 779,984 checks (`claude-5d276890…`);
- `fast`: 602,384 checks (`claude-d4d47532…`).

The reductions are exact, including integer wrap-around, and the fast-math FP sums use
reassociated trees over exact inputs. `s4_masks` still passes 1,589,070 checks at
`-O2 -ftree-vectorize` (`claude-02ff21ef…`) and `-O3` (`claude-0c3ea928…`).

## 2026-11-05: S5-08 merged (same-width conversions)

GCC `knc` with S5-08: `cvt_i32_f32`, `cvt_u32_f32` and `cvt_f32_i32` now use `vcvtfxpnt*` (3 at
`-O2 -ftree-vectorize`). `s5_ops` passes:
- `o2v`: 779,984 checks (`claude-32528ac0…`);
- `o3`: 779,984 checks (`claude-657ae463…`);
- `fast`: 602,384 checks (`claude-7c997da8…`).

That includes the round-to-nearest int-to-float checks and float-to-int truncation with negative
fractions. `s4_masks` still passes 1,589,070 checks at `-O2 -ftree-vectorize` (`claude-34a18310…`)
and `-O3` (`claude-37ed4a56…`).

## 2026-11-05: S5-10 under review (FP32 vector sqrt)

`s5_ops` built from S5-10's compiler with `-fno-math-errno`, so `sqrtf` loops vectorize:

- `-O2 -ftree-vectorize`: 779,984 checks, 0 failures.
- `-O3`: 779,984 checks, 0 failures.

The first 80-thread exhaustive run exited with code 2 in under a second: `pthread_create` failed
under card_run's default 128 MiB limit (80 default stacks need more). Use a config with
`memoryMB: 2048` for threaded jobs. card_run also allows only one of our jobs at a time (own lock),
so our jobs run one after another even when cores are free.

Exhaustive FP32 sqrt check (`sqrt-exhaustive-mt.c`, 80 threads on cores 59-40, MXCSR RN with
FZ=DAZ=0, `claude-d72bce9f…`): `inputs=4294967296 regular=2139095039 special=2155872257
bad_regular=0 bad_special=0`. Every positive finite input gives the correctly rounded result,
and every zero, negative, infinity and NaN gives the expected special value.

## 2026-11-05: S5-17 mid batch check, at GCC `knc` `9690ac8906a` (after S5-06 to S5-10)

- Full `gcc.c-torture/execute` suite: 1,681 of 1,681 pass (`harness/card/run_suite.py`, now with
  `--threads 80`; build and receipts in `.work/_shared/tmp/claude-suite-s5-17`).
- `s4_masks`: 1,589,070 checks, 0 failures at `-O2 -ftree-vectorize` (`claude-96b1e88d…`) and
  `-O3` (`claude-174af769…`).
- `s5_ops` `fast` (`-O3 -ffast-math`): 602,384 checks, 0 failures (`claude-5125e9d6…`). Two
  earlier tries failed with "SSH upload deadline" while the laptop was busy building the suite;
  the third passed with `--transport-timeout 60 --stage-timeout 300`.
- `s5_ops` `o2v` and `o3` passed at the same compiler code under S5-10 (above).
- x86 (lead, `portability-claude`): `-O2` and `-O2 -mavx512f` identical=1962 different=0
  both-failed=41.

## 2026-11-05: S5-11 under review (FP32 vector division)

Built from S5-11's compiler (GCC `fabdf2d706e`), core 59:

- `s5_ops` `o2v`: 779,984 checks, 0 failures (`claude-9c208fd6…`); `o3`: same (`claude-97a295e8…`).
- `tests/regress/knc-div-sets.c` (S5-03 sets, exact integer residuals, flags per batch;
  `claude-d51007f0…`, about 10 card minutes):

| Set | Pairs | Bad | Flag mismatches | Flags seen |
|---|---|---|---|---|
| (a) modular near-midpoints, RN | 46,513,140 | 0 | 0 | PE |
| (b) near-one class, RN | 134,217,704 | 0 | 0 | PE |
| (c) all exponent pairs and subnormals, RN | 4,161,664 | 0 | 0 | PE UE OE |
| (d) subnormal midpoints, RN | 102,010 | 0 | 0 | PE UE |
| (e) specials, one pair per call, all modes | 784 | 0 | 0 | IE DZ OE UE PE |
| (f) 2^30 random, RN | 1,073,741,824 | 0 | 0 | IE DZ OE UE PE |
| (g) (a), (b), (d) under RD, RU, RZ | 542,498,562 | 0 | 0 | PE UE |

## 2026-11-06: S5-12 under review (float/double-width conversions)

`s5_ops` built from S5-12's compiler (GCC `84679230849`; `cvt_f32_f64`, `cvt_f64_f32`,
`cvt_i32_f64`, `cvt_f64_i32` and `mix_f32_f64` now vectorize), core 59:
`o2v` 779,984 checks (`claude-7e435c2f…`), `o3` 779,984 (`claude-c620df3d…`), `fast` 602,384
(`claude-b274292a…`), all 0 failures.

## 2026-11-06: S5-13 under review (16-lane gather and scatter)

`s5_ops` built from S5-13's compiler (GCC `917beb990eb`; `gat_f32`, `gat_i32` and `sca_f32` now
use `vgatherdps`/`vpgatherdd`/`vscatterdps` in a `jknzd` retry loop; `mgat_f32` and `msca_f32`
stay scalar by the amended acceptance), core 59: `o2v` 779,984 checks (`claude-19552b23…`),
`o3` 779,984 (`claude-ac2a8527…`), `fast` 602,384 (`claude-2f13affb…`), all 0 failures.

## 2026-11-06: S5-14 under review (8-lane gather and scatter)

`s5_ops` built from S5-14's compiler (GCC `ab967b42a6e`; `gat_f64`, `gat_i64` and `sca_f64` now
use two `vgatherdpd`/`vpgatherdq`/`vscatterdpd` per 16 int indices, the high half moved down by
`vpermf32x4 $0xee`), core 59: `o2v`
779,984 checks (`claude-050135f9…`), `o3` 779,984 (`claude-73528700…`), `fast` 602,384
(`claude-24590e76…`), all 0 failures.

## 2026-11-06: S5-15 under review (FP min/max)

Built from S5-15's compiler (GCC `41a1abe5bbb`; `vgmin`/`vgmax` for MIN_EXPR/MAX_EXPR, `fmin`/`fmax`
and their reductions), core 59: `s4_masks` `o2v` and `o3` 1,589,070 checks each (`claude-b021089b…`,
`claude-83fc00b3…`), including `fmin_*`/`fmax_*` now vectorized; `s5_ops` `o2v` 779,984
(`claude-f9c973ff…`), `o3` 779,984 (`claude-09bac8f0…`), `fast` 602,384 (`claude-375bab83…`);
all 0 failures.
