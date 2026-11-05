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
