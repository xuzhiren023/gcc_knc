# Card runs, Sprint 3

All jobs were run by the lead through `tools/card_run`, under the shared card rules. They used
cores 30-59 (logical CPUs 121-240), and boot ID `e9bfb0ab-e90a-4a5e-9df4-2899a9fd93a4` was
unchanged. No timing figures are given: the ledger shows another agent's jobs overlapping.

## 2026-11-03 evening (UTC 00:15-00:30 on 11-04)

The compiler was the shared GCC 16 build. The vector copy checks used S3-06's branch build (it
contains S3-04 and S3-05); the FP checks used the merged `knc` at `0da1f525ed2` (S3-06's merge).
The sources are in `tests/acceptance/s3_vec_card/`.

| Program | Flags | Result on the card |
|---|---|---|
| `vec_card.c`: S3-04/S3-05 packed copies, 4 types (aligned, zero, pool constant; unaligned pairs at every element offset of source and destination, with sentinels; pairs flush against unmapped guard pages; vectors live across calls at four stack alignments) | `-O0` | `S3-VEC PASS cases=780 failures=0` |
| same | `-O2` | `S3-VEC PASS cases=780 failures=0` |
| same, `-DBROKEN_ALIGN` (negative control: aligned moves on unaligned addresses) | `-O2` | Segmentation fault, as it must |
| `fp_card.c`: S3-06 V16SF/V8DF add, sub, mul and broadcast-multiply, exact values | `-O0` | `S3-FP PASS cases=8 failures=0` |
| same, plus FMA where fused and unfused differ (`vfmadd` present) | `-O2` | `S3-FP PASS cases=10 failures=0` |
| S2-08's 256 `gcc.c-torture/execute` programs, rebuilt with S3-06's branch build at `-O2 -march=knc` | `-O2`, `-j 30` | 256 of 256 PASS |

Card minutes: about 0.18 in total.

Runner issue: two attempts at the torture job were refused with `unknown process identity in
snapshot: b'PROC\t242373\t\tkworker/u:7\t\t'` while a `gpt61` job ran. The third attempt passed.
S3-17 fixes the cause.

## m1_affine, early (2026-11-04 01:50 UTC)

Built with S3-07's branch build (`dd28677d065`, before S3-07 merged): `loops.c` at `-O2
-ftree-vectorize -march=knc`, and `driver.c` by GCC 16 or by the donor. `-fopt-info-vec` reports
both affine loops vectorized with 64-byte vectors. With `-ffp-contract=off` they use `vmulp*` and
`vaddp*`; with `fast`, `vfmadd*`. All four builds lint clean.

| `loops.c` contraction | `driver.c` built by | Card |
|---|---|---|
| off | GCC 16 | `ACCEPT-PASS scalar=3.00 failures=0` |
| off | donor (ABI cross-check) | `ACCEPT-PASS scalar=3.00 failures=0` (first attempt refused by the runner, S3-19) |
| fast | GCC 16 | `ACCEPT-PASS scalar=3.00 failures=0` |
| fast | donor | `ACCEPT-PASS scalar=3.00 failures=0` |

S3-07 merged as `daedd869681`, with no compiler change after `dd28677d065`, so these are the
merged code's results. After the merge, S2-08's 256 torture programs, rebuilt with vectorization on
by default, pass 256 of 256. Only 10 of them contain packed zmm code, so that is a regression check,
not a vector test; the full execute suite follows. Two attempts were refused by the S3-19 race
before one ran.

## Full `gcc.c-torture/execute` suite after S3-07 (2026-11-04 02:30 UTC)

The merged `knc` (`daedd869681`) at `-O2 -march=knc`, vectorization on by default, each file's own
`dg-options` applied. Built on the laptop; six card jobs of up to 300 programs each, `-j 30`.

- Of 1,692 sources: 1,661 linked; 94 of them contain packed zmm code. There were 30 compile errors:
  21 for other targets or features, and 5 the expected "unsupported KNC register ABI mode". There
  was 1 ICE, `pr85169.c` (S3-20).
- **On the card: 1,659 of 1,661 PASS.**
  - `930529-1.c` is a harness failure. My script missed its brace-form `dg-options { "-fwrapv" }`,
    and built with `-fwrapv` it passes.
  - **`pr65369.c` is wrong code from vectorization.** It segfaults; built with
    `-fno-tree-vectorize`, `-O0` or the donor, it passes. SLP put a V16SI `vloadunpackld/hd` pair on
    a byte-aligned address, and the pairs need element alignment (Intel 327364 p.361). S3-21 fixes
    it, and ADR-0005 point 4 is amended.
- No runner refusals in six chunks (S3-18 and S3-19 had merged by then).

## Full execute suite after S3-21 (2026-11-04 03:50 UTC)

S3-21's build (`29781633082`), which has the same compiler sources as the merged `knc`
(`10ce7e12b64`). The suite was rebuilt at `-O2 -march=knc`, with brace-form `dg-options` now
parsed (so `930529-1` gets `-fwrapv`). 1,661 linked, 93 with packed zmm code (`pr65369` no longer
vectorizes), and 1 ICE (`pr85169`, S3-20).

**On the card: 1,661 of 1,661 PASS**, in six chunks with no runner refusals.

## S3-21 before merge (2026-11-04 03:20 UTC)

S3-21's branch build (`29781633082`):

- The engineer's guard program at `-O2` and `-O3` prints `PASS S3-21 all four modes,
  source/destination offsets 0-63, sentinels and guards`.
- `pr65369` rebuilt at `-O2` now exits 0 on the card; before the fix it segfaulted.

## m1_affine with the Fortran twin, after S3-08 (2026-11-04 02:45 UTC)

`driver.c -DKNC_WITH_FORTRAN`, `loops.c` and `affine_fortran.f90` (GCC 16 `gfortran`, vectorized),
at contraction `off` and `fast`: both print `ACCEPT-PASS scalar=3.00 failures=0`.

## FP state and special values (2026-11-04 01:30 UTC)

`tests/acceptance/s3_vec_card/fp_special.c`, built with S3-07's branch build (`dd28677d065`,
which contains S3-06), at `-O0` and `-O2`, `-lm`. Both print `S3-FPSPECIAL PASS cases=96
failures=0`.

- **Startup state without fast-math:** MXCSR `0x00200000` (bit 21 only: no FTZ, no DAZ, so
  gradual underflow) and x87 control word `0x037f`.
- **CPUID leaf 1:** `eax=0x00000b12 edx=0x1101137f`, so **SSE and SSE2 are reported absent**. A
  runtime that gates MXCSR writes on CPUID SSE, like libgfortran's `config/fpu-387.h`, skips them:
  it does not fault, but it also leaves the vector unit's exceptions and rounding unmanaged.
- **Lanes:** V16SF and V8DF add, sub and mul on ±0, ±∞, NaN, the smallest normal, ±subnormals, the
  largest finite value and half-normals all match an x87 long double reference rounded to the
  element type. That covers the sign of zero, and subnormal results are kept rather than flushed.
- **Flags** seen by `fetestexcept`: the same for vector and x87 ops. `inexact` on 1+1e-30,
  `invalid` on ∞-∞, `overflow inexact` on MAX×4, and nothing on an exact subnormal product, as
  IEEE says.

One first `-O0` attempt ended `infrastructure-failure` (exit 126). Its reason was not kept, and 5
`hello` reruns passed; S3-18 keeps receipts so the next one can be diagnosed.

After S3-17 merged (runner fix): `hello` matched, and the same 256 torture programs passed 256 of 256 while a `gpt61` job overlapped.

## Native TLS after S3-14 (2026-11-04 04:30 UTC)

Built with S3-14's branch build (`cc1` from `0235ff44771`, HAVE_AS_TLS defined). S3-14 merged as
`edf7c69d617`; the merge differs only in the reverted picflag lines, which do not reach `cc1`, so
these are the merged compiler's results. Sources and build: `tests/acceptance/s3_tls_card/`. Every
GCC 16 object and library was checked for `__emutls` before linking (none), and all lint clean.

Each of 4 threads writes its own value to `__thread` variables defined by the donor, by GCC 16 and
in a shared library, then reads them back through the other compiler's code after a barrier; the
main thread must still see the initial values.

| Variant | Built how | Card job | Result |
|---|---|---|---|
| A | main and `tls_new` by GCC 16 `-O2`; `tls_donor` and the `.so` by the donor | `claude-985a0cc8…` | `S3-TLS PASS checks=59 failures=0` |
| B | as A, GCC 16 at `-O0` | `claude-e8a82b81…` | same |
| C | main by the donor; `tls_new` and the `.so` (global- and local-dynamic) by GCC 16 `-O2` | `claude-41ac1b6a…` | same |
| D | as C, GCC 16 at `-O0` | `claude-80f64600…` | same |
| X | control: plain globals instead of `__thread` | `claude-ebd13244…` | `S3-TLS FAIL checks=59 failures=46`, exit 1, as it must |

This ticks S3-14's native line: donor-defined used from GCC 16, the reverse, and a donor `.so`,
each from 4 threads. S3-10 need not rebuild it.

## Full `gcc.c-torture/execute` suite after S3-14 (2026-11-04 04:45-04:58 UTC)

The merged `knc` (`edf7c69d617`, native TLS) at `-O2 -march=knc`, built with
`harness/card/build_suite.py` before S3-15's rebuild started (`cc1` unchanged from start to end of
the build). 1,692 sources, 1,661 linked, 93 with packed zmm code, 30 compile errors as before, and
1 ICE (`pr85169`, S3-20). **On the card: 1,661 of 1,661 PASS**, in six jobs, with no retries. That
is the same as the baseline at `10ce7e12b64`, so native TLS caused no regression.

## S3-15: complex values and rounding mode across calls (2026-11-04 05:35 UTC)

The cross-links S3-15's T2 left in `.work/_shared/scalar-abi/`, built at 00:29 local by S3-15's
branch build (`cc1` of 00:24, from `eb2efcdcf04`). S3-15 merged as `eb8fb3e902a` with no compiler
change after that, and `cc1` was not rebuilt, so these are the merged compiler's results. All lint
clean. Suffix `-0` is a GCC 16 caller and donor callee, `-1` the reverse.

| Program | Card | Result |
|---|---|---|
| `abi-gaps-O0-0`, `-O0-1`, `-O2-0`, `-O2-1` | `claude-a49bd551…`, `claude-c0c8a9b0…`, `claude-36f63a5c…`, `claude-12a37489…` | `complex ABI PASS` with `_Complex float`, `double` and `long double` exact (long double keeps its 2^-60 tail); `rounding PASS` in all 4 modes |
| `scalar-abi-O2-0`, `-O2-1` (S2-02's suite, now built with `-frounding-math`) | `claude-c6ef8fff…`, `claude-78afe6b4…` | `S2-02 scalar ABI PASS` |

The rounding case adds 2^-53 to ±1, a halfway value, so each mode stores a different double; it
also checks that the x87 control word and MXCSR rounding bits are the same before and after the
call. `fesetround` on the card sets both. A mode lost across the call would print a wrong value,
so the expectations are their own control.

Full execute suite after S3-15 (`eb8fb3e902a`): the build gives the same result for every one of
the 1,692 sources as after S3-14 (the new guard rejects nothing that compiled before), and on the
card **1,661 of 1,661 PASS**, six jobs, no retries.
